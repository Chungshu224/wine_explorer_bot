"""
《風土探勘者》Telegram 互動小說式葡萄酒學習遊戲 — Supabase 持久化版本

架構重點(跟前一版的差異):
- 玩家進度不再存在本機 user_state.json,改成讀寫 Supabase 的兩張表:
    - wine_bot_users:   telegram_user_id (PK), active_campaign
    - wine_bot_progress: (telegram_user_id, campaign_id) 複合 PK,
                         current_chapter / current_node / badges / flags / fog_zones / attempts
  這樣不管 Railway 怎麼重新部署,進度都不會消失。
- 跟 Supabase 溝通走 REST API(PostgREST),用 httpx 非同步呼叫,
  不需要額外安裝 supabase-py。
- 其餘的劇情樹讀取(story_data.json)、Telegram 互動邏輯,跟前一版相同。

環境變數:
- TELEGRAM_BOT_TOKEN:跟 BotFather 申請的 token
- SUPABASE_URL:例如 https://xxxx.supabase.co
- SUPABASE_ANON_KEY:Supabase 專案設定 -> API -> anon / publishable key

執行方式:
1. pip install -r requirements.txt
2. 設定上述三個環境變數
3. python bot.py
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
STORY_FILE = BASE_DIR / "story_data.json"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")


# ---------------------------------------------------------------------------
# 劇情資料載入(跟以前一樣,從本機 JSON 讀,這部分不需要持久化)
# ---------------------------------------------------------------------------

def load_story() -> dict[str, Any]:
    with open(STORY_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_campaign_order(story: dict[str, Any]) -> list[str]:
    return list(story["campaigns"].keys())


def group_campaigns_by_region(story: dict[str, Any]) -> list[tuple[str, list[tuple[int, str]]]]:
    """把故事線依照 campaign["region"] 分組,方便 /campaigns 跟 /start 選單
    用「夜丘」「伯恩丘」這種產區小標分區顯示,而不是一長串扁平列表。
    回傳的每個 campaign_id 都附帶它在 get_campaign_order() 裡的原始索引,
    因為按鈕的 callback_data 是用這個索引定位故事線,分組顯示不能打亂它。
    """
    order = get_campaign_order(story)
    groups: dict[str, list[tuple[int, str]]] = {}
    group_order: list[str] = []
    for idx, cid in enumerate(order):
        region = story["campaigns"][cid].get("region", "其他")
        if region not in groups:
            groups[region] = []
            group_order.append(region)
        groups[region].append((idx, cid))
    return [(region, groups[region]) for region in group_order]


def get_chapter_order(story: dict[str, Any], campaign_id: str) -> list[str]:
    campaign = story["campaigns"][campaign_id]
    return campaign.get("chapter_order", list(campaign["chapters"].keys()))


def chapter_is_unlocked(
    story: dict[str, Any], campaign_id: str, chapter_id: str, badges: list[str]
) -> bool:
    meta = story["campaigns"][campaign_id]["chapters"][chapter_id].get("meta", {})
    required = meta.get("requires_badges", [])
    return all(b in badges for b in required)


def get_node(
    story: dict[str, Any], campaign_id: str, chapter_id: str, node_id: str
) -> dict[str, Any]:
    return story["campaigns"][campaign_id]["chapters"][chapter_id]["nodes"][node_id]


# ---------------------------------------------------------------------------
# Supabase 存取層(取代原本的本機 user_state.json)
# ---------------------------------------------------------------------------

def _supabase_headers() -> dict[str, str]:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _default_campaign_row(user_id: int, campaign_id: str) -> dict[str, Any]:
    return {
        "telegram_user_id": user_id,
        "campaign_id": campaign_id,
        "current_chapter": None,
        "current_node": None,
        "badges": [],
        "flags": [],
        "fog_zones": [],
        "attempts": {},
    }


async def get_active_campaign(user_id: int) -> str | None:
    """回傳玩家目前選的故事線 id;沒有紀錄就回傳 None(代表要先選故事線)。"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/wine_bot_users",
            headers=_supabase_headers(),
            params={"telegram_user_id": f"eq.{user_id}", "select": "active_campaign"},
        )
        resp.raise_for_status()
        rows = resp.json()
    return rows[0]["active_campaign"] if rows else None


async def set_active_campaign(user_id: int, campaign_id: str) -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/wine_bot_users",
            headers={**_supabase_headers(), "Prefer": "resolution=merge-duplicates,return=representation"},
            json={"telegram_user_id": user_id, "active_campaign": campaign_id},
        )
        resp.raise_for_status()
    # 確保這條故事線在 wine_bot_progress 也有一列初始資料
    await _ensure_campaign_row(user_id, campaign_id)


async def _ensure_campaign_row(user_id: int, campaign_id: str) -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/wine_bot_progress",
            headers=_supabase_headers(),
            params={
                "telegram_user_id": f"eq.{user_id}",
                "campaign_id": f"eq.{campaign_id}",
                "select": "telegram_user_id",
            },
        )
        resp.raise_for_status()
        exists = bool(resp.json())
        if not exists:
            insert_resp = await client.post(
                f"{SUPABASE_URL}/rest/v1/wine_bot_progress",
                headers=_supabase_headers(),
                json=_default_campaign_row(user_id, campaign_id),
            )
            insert_resp.raise_for_status()


async def get_campaign_state(user_id: int, campaign_id: str) -> dict[str, Any]:
    await _ensure_campaign_row(user_id, campaign_id)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/wine_bot_progress",
            headers=_supabase_headers(),
            params={
                "telegram_user_id": f"eq.{user_id}",
                "campaign_id": f"eq.{campaign_id}",
                "select": "*",
            },
        )
        resp.raise_for_status()
        rows = resp.json()
    return rows[0] if rows else _default_campaign_row(user_id, campaign_id)


async def update_campaign_state(user_id: int, campaign_id: str, **kwargs) -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{SUPABASE_URL}/rest/v1/wine_bot_progress",
            headers=_supabase_headers(),
            params={
                "telegram_user_id": f"eq.{user_id}",
                "campaign_id": f"eq.{campaign_id}",
            },
            json=kwargs,
        )
        resp.raise_for_status()


async def append_unique(user_id: int, campaign_id: str, field: str, value: str) -> None:
    state = await get_campaign_state(user_id, campaign_id)
    lst = state.get(field) or []
    if value not in lst:
        lst.append(value)
        await update_campaign_state(user_id, campaign_id, **{field: lst})


async def record_attempt(user_id: int, campaign_id: str, node_id: str) -> int:
    state = await get_campaign_state(user_id, campaign_id)
    attempts = state.get("attempts") or {}
    attempts[node_id] = attempts.get(node_id, 0) + 1
    await update_campaign_state(user_id, campaign_id, attempts=attempts)
    return attempts[node_id]


async def get_all_campaign_states(user_id: int) -> dict[str, dict[str, Any]]:
    """給 /campaigns 用:一次取回這位玩家在所有故事線的進度。"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/wine_bot_progress",
            headers=_supabase_headers(),
            params={"telegram_user_id": f"eq.{user_id}", "select": "*"},
        )
        resp.raise_for_status()
        rows = resp.json()
    return {row["campaign_id"]: row for row in rows}


# ---------------------------------------------------------------------------
# 劇情節點渲染
# ---------------------------------------------------------------------------

def build_keyboard(
    node: dict[str, Any], campaign_id: str
) -> InlineKeyboardMarkup | None:
    choices = node.get("choices", [])
    if not choices:
        return None
    buttons = []
    for idx, choice in enumerate(choices):
        # callback_data 故意保持極簡:Telegram 對 callback_data 有 64 bytes
        # 的硬性長度上限,塞進完整的章節/節點 id 很容易超過(尤其中文章節
        # 名對應的 id 加起來很長),超過就會導致 Telegram 直接拒收整則訊息
        # (400 Bad Request),表現起來就是「按鈕完全沒反應、bot 像當機」。
        # 所以這裡只帶「故事線 id + 選項索引」,其餘資訊(玩家目前在哪個
        # 章節/節點)一律從資料庫現查,資料庫本身就是唯一的真相來源。
        callback_data = f"goto:{campaign_id}:{idx}"
        buttons.append([InlineKeyboardButton(choice["label"], callback_data=callback_data)])
    return InlineKeyboardMarkup(buttons)


async def send_node(
    update_or_query,
    context: ContextTypes.DEFAULT_TYPE,
    campaign_id: str,
    chapter_id: str,
    node_id: str,
    user_id: int,
) -> None:
    story = load_story()
    node = get_node(story, campaign_id, chapter_id, node_id)
    text = node["text"]
    keyboard = build_keyboard(node, campaign_id)

    if node.get("grants_badge"):
        await append_unique(user_id, campaign_id, "badges", node["grants_badge"])
        text += f"\n\n🏅 獲得知識印記:{node['grants_badge']}"

    await update_campaign_state(user_id, campaign_id, current_chapter=chapter_id, current_node=node_id)

    if hasattr(update_or_query, "message") and update_or_query.message:
        await update_or_query.edit_message_text(text, reply_markup=keyboard)
    else:
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=keyboard)


# ---------------------------------------------------------------------------
# 故事線選單(兩層樹狀導覽:先選產區,再選故事線)
# ---------------------------------------------------------------------------

def build_region_menu(
    story: dict[str, Any],
    mode: str,
    active_campaign: str | None = None,
    all_states: dict[str, Any] | None = None,
) -> tuple[str, InlineKeyboardMarkup]:
    """第一層選單:只列出產區(夜丘/伯恩丘/...),不展開個別故事線。
    mode 是 "p"(picker,/start 用,第一次選故事線)或 "c"(/campaigns 總覽用),
    差別只在標題文字跟要不要顯示已獲得印記數。
    """
    groups = group_campaigns_by_region(story)
    header = "🍇 選擇一個產區:" if mode == "p" else "🗺️ 所有故事線 · 選擇一個產區:"
    lines = [header, ""]
    buttons = []
    for region_idx, (region, entries) in enumerate(groups):
        n_campaigns = len(entries)
        if mode == "c" and all_states is not None:
            total_badges = sum(len(all_states.get(cid, {}).get("badges") or []) for _, cid in entries)
            lines.append(f"🗺️ {region}({n_campaigns} 條故事線,已獲得 {total_badges} 個印記)")
        else:
            lines.append(f"🗺️ {region}({n_campaigns} 條故事線)")
        buttons.append([InlineKeyboardButton(f"📂 {region}", callback_data=f"selectregion:{mode}:{region_idx}")])
    return "\n".join(lines), InlineKeyboardMarkup(buttons)


def build_region_detail(
    story: dict[str, Any],
    region_idx: int,
    mode: str,
    active_campaign: str | None = None,
    all_states: dict[str, Any] | None = None,
) -> tuple[str, InlineKeyboardMarkup]:
    """第二層選單:展開某個產區底下的故事線列表,附一顆返回按鈕。"""
    groups = group_campaigns_by_region(story)
    region, entries = groups[region_idx]

    lines = [f"🗺️ {region}\n"]
    buttons = []
    for idx, cid in entries:
        campaign = story["campaigns"][cid]
        if mode == "c" and all_states is not None:
            badge_count = len(all_states.get(cid, {}).get("badges") or [])
            active_mark = "🟢 " if cid == active_campaign else ""
            lines.append(f"{active_mark}📖 {campaign['title']}(已獲得 {badge_count} 個印記)\n   {campaign['knowledge_focus']}\n")
        else:
            lines.append(f"📖 {campaign['title']}\n   {campaign['tagline']}\n   知識主線:{campaign['knowledge_focus']}\n")
        # 用索引而非完整 campaign_id 組 callback_data:Telegram 對
        # callback_data 有 64 bytes 硬性上限,用索引可以確保不管故事線
        # id 未來取得多長,按鈕資料都維持極短、不會有超過上限的風險。
        buttons.append([InlineKeyboardButton(f"▶️ {campaign['title']}", callback_data=f"startcampaign:{idx}")])
    buttons.append([InlineKeyboardButton("⬅️ 返回產區選單", callback_data=f"regionmenu:{mode}")])
    return "\n".join(lines), InlineKeyboardMarkup(buttons)


# ---------------------------------------------------------------------------
# 指令處理
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    story = load_story()
    active_campaign = await get_active_campaign(user_id)

    if active_campaign is None:
        text, keyboard = build_region_menu(story, mode="p")
        await update.message.reply_text(text, reply_markup=keyboard)
        return

    campaign_state = await get_campaign_state(user_id, active_campaign)

    if campaign_state["current_node"] is None:
        chapter_id = get_chapter_order(story, active_campaign)[0]
        node_id = story["campaigns"][active_campaign]["chapters"][chapter_id]["start_node"]
    else:
        chapter_id = campaign_state["current_chapter"]
        node_id = campaign_state["current_node"]

    node = get_node(story, active_campaign, chapter_id, node_id)
    keyboard = build_keyboard(node, active_campaign)
    await update.message.reply_text(node["text"], reply_markup=keyboard)
    await update_campaign_state(user_id, active_campaign, current_chapter=chapter_id, current_node=node_id)


async def campaigns_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    story = load_story()
    active_campaign = await get_active_campaign(user_id)
    all_states = await get_all_campaign_states(user_id)

    text, keyboard = build_region_menu(story, mode="c", active_campaign=active_campaign, all_states=all_states)
    await update.message.reply_text(text, reply_markup=keyboard)


async def handle_select_region(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """使用者點了「產區」按鈕,展開該產區底下的故事線列表。"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    _, mode, region_idx_str = query.data.split(":")
    region_idx = int(region_idx_str)

    story = load_story()
    active_campaign = await get_active_campaign(user_id) if mode == "c" else None
    all_states = await get_all_campaign_states(user_id) if mode == "c" else None

    text, keyboard = build_region_detail(story, region_idx, mode, active_campaign, all_states)
    await query.edit_message_text(text, reply_markup=keyboard)


async def handle_region_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """「返回產區選單」按鈕,回到第一層(只列產區)。"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    mode = query.data.split(":", 1)[1]

    story = load_story()
    active_campaign = await get_active_campaign(user_id) if mode == "c" else None
    all_states = await get_all_campaign_states(user_id) if mode == "c" else None

    text, keyboard = build_region_menu(story, mode, active_campaign, all_states)
    await query.edit_message_text(text, reply_markup=keyboard)


async def chapters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    story = load_story()
    active_campaign = await get_active_campaign(user_id)

    if active_campaign is None:
        await update.message.reply_text("你還沒選擇故事線喔,先輸入 /start 選一條吧。")
        return

    campaign_state = await get_campaign_state(user_id, active_campaign)
    badges = campaign_state.get("badges") or []
    campaign = story["campaigns"][active_campaign]

    lines = [f"🗺️ {campaign['title']} · 章節地圖\n"]
    buttons = []
    campaign_idx = get_campaign_order(story).index(active_campaign)

    for chapter_idx, chapter_id in enumerate(get_chapter_order(story, active_campaign)):
        chapter = campaign["chapters"][chapter_id]
        meta = chapter.get("meta", {})
        unlocked = chapter_is_unlocked(story, active_campaign, chapter_id, badges)
        tier_label = meta.get("tier_label", "")
        village = meta.get("village", "")

        if unlocked:
            lines.append(f"🔓 {chapter['title']}({tier_label} · {village})")
            buttons.append([InlineKeyboardButton(
                f"▶️ {chapter['title']}",
                callback_data=f"startchapter:{campaign_idx}:{chapter_idx}",
            )])
        else:
            required = meta.get("requires_badges", [])
            missing = [b for b in required if b not in badges]
            lines.append(f"🔒 {chapter['title']}({tier_label} · {village})\n   需要印記:{', '.join(missing)}")

    keyboard = InlineKeyboardMarkup(buttons) if buttons else None
    await update.message.reply_text("\n\n".join(lines), reply_markup=keyboard)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    active_campaign = await get_active_campaign(user_id)

    if active_campaign is None:
        await update.message.reply_text("你還沒選擇故事線喔,先輸入 /start 選一條吧。")
        return

    campaign_state = await get_campaign_state(user_id, active_campaign)
    badges = campaign_state.get("badges") or ["(尚未獲得任何印記)"]
    fog = campaign_state.get("fog_zones") or ["(沒有需要複習的知識點)"]

    text = (
        f"目前故事線:{active_campaign}\n\n"
        "🏅 已獲得的印記:\n"
        + "\n".join(f"  · {b}" for b in badges)
        + "\n\n🌫️ 迷霧區域(下次會以新題目重新出現):\n"
        + "\n".join(f"  · {f}" for f in fog)
    )
    await update.message.reply_text(text)


# ---------------------------------------------------------------------------
# 按鈕 callback 處理
# ---------------------------------------------------------------------------

async def handle_start_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    campaign_idx = int(query.data.split(":", 1)[1])
    story = load_story()
    campaign_id = get_campaign_order(story)[campaign_idx]

    await set_active_campaign(user_id, campaign_id)
    campaign_state = await get_campaign_state(user_id, campaign_id)

    if campaign_state["current_node"] is None:
        chapter_id = get_chapter_order(story, campaign_id)[0]
        node_id = story["campaigns"][campaign_id]["chapters"][chapter_id]["start_node"]
    else:
        chapter_id = campaign_state["current_chapter"]
        node_id = campaign_state["current_node"]

    await send_node(query, context, campaign_id, chapter_id, node_id, user_id)


async def handle_start_chapter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    _, campaign_idx_str, chapter_idx_str = query.data.split(":")
    campaign_idx, chapter_idx = int(campaign_idx_str), int(chapter_idx_str)

    story = load_story()
    campaign_id = get_campaign_order(story)[campaign_idx]
    chapter_id = get_chapter_order(story, campaign_id)[chapter_idx]

    campaign_state = await get_campaign_state(user_id, campaign_id)
    badges = campaign_state.get("badges") or []

    if not chapter_is_unlocked(story, campaign_id, chapter_id, badges):
        await query.edit_message_text("這個章節還沒解鎖喔,先去收集需要的印記吧。")
        return

    start_node = story["campaigns"][campaign_id]["chapters"][chapter_id]["start_node"]
    await send_node(query, context, campaign_id, chapter_id, start_node, user_id)


async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    _, campaign_id, choice_idx_str = query.data.split(":")
    choice_idx = int(choice_idx_str)

    story = load_story()
    campaign_state = await get_campaign_state(user_id, campaign_id)
    source_chapter = campaign_state.get("current_chapter")
    source_node = campaign_state.get("current_node")

    if source_chapter is None or source_node is None:
        await query.edit_message_text(
            "找不到目前的進度,輸入 /start 重新開始這條故事線。"
        )
        return

    current_node = get_node(story, campaign_id, source_chapter, source_node)

    try:
        choice = current_node["choices"][choice_idx]
    except IndexError:
        # 玩家點到「過期」的按鈕(通常是重複開啟的舊訊息,選項索引已經
        # 對不上目前節點的選項清單),不讓它整個當機,給友善提示即可。
        await query.edit_message_text(
            "這個按鈕已經過期了(可能是重複開啟的舊訊息)。"
            "輸入 /start 或 /chapters 回到目前的進度繼續遊玩。"
        )
        return

    target_chapter = choice.get("chapter", source_chapter)
    next_node_id = choice["next"]

    if current_node.get("type") == "quiz":
        attempt_count = await record_attempt(user_id, campaign_id, source_node)
        if not choice.get("correct", True):
            await append_unique(user_id, campaign_id, "fog_zones", source_node)
            logger.info(
                "user %s (campaign=%s) answered %s incorrectly (attempt #%d)",
                user_id, campaign_id, source_node, attempt_count,
            )
        if current_node.get("knowledge_card"):
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📖 知識卡片:\n{current_node['knowledge_card']}",
            )

    if choice.get("sets_flag"):
        await append_unique(user_id, campaign_id, "flags", choice["sets_flag"])
    if choice.get("sets_fog"):
        await append_unique(user_id, campaign_id, "fog_zones", choice["sets_fog"])

    await send_node(query, context, campaign_id, target_chapter, next_node_id, user_id)


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("請先設定環境變數 TELEGRAM_BOT_TOKEN(跟 BotFather 申請後取得)")
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise SystemExit("請先設定環境變數 SUPABASE_URL 與 SUPABASE_ANON_KEY")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("chapters", chapters))
    app.add_handler(CommandHandler("campaigns", campaigns_command))
    app.add_handler(CallbackQueryHandler(handle_start_campaign, pattern=r"^startcampaign:"))
    app.add_handler(CallbackQueryHandler(handle_start_chapter, pattern=r"^startchapter:"))
    app.add_handler(CallbackQueryHandler(handle_select_region, pattern=r"^selectregion:"))
    app.add_handler(CallbackQueryHandler(handle_region_menu, pattern=r"^regionmenu:"))
    app.add_handler(CallbackQueryHandler(handle_choice, pattern=r"^goto:"))

    logger.info("風土探勘者 bot(Supabase 持久化版)啟動中...")
    app.run_polling()


if __name__ == "__main__":
    main()
