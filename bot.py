"""
《風土探勘者》Telegram 互動小說式葡萄酒學習遊戲 — 程式雛形

延續 telegram_review_bot.py 的骨架概念:
- 用 JSON 儲存劇情樹(story_data.json),方便未來用資料庫文章批次生成新章節
- 每位玩家的進度(目前節點、已獲得印記、答錯次數/迷霧區域)存在 user_state.json
- 用 python-telegram-bot 的 InlineKeyboardButton 處理分支選擇
- 品飲判斷題(quiz 節點)答對/答錯會分別導向不同劇情後果,並記錄到 attempts

執行方式:
1. pip install python-telegram-bot --upgrade
2. 設定環境變數 TELEGRAM_BOT_TOKEN(跟 BotFather 申請)
3. python bot.py
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

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
STATE_FILE = BASE_DIR / "user_state.json"

DEFAULT_CHAPTER = "gevrey_chambertin_01"


# ---------------------------------------------------------------------------
# 資料載入與玩家狀態儲存
# ---------------------------------------------------------------------------

def load_story() -> dict[str, Any]:
    with open(STORY_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_all_states() -> dict[str, Any]:
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_all_states(states: dict[str, Any]) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(states, f, ensure_ascii=False, indent=2)


def get_user_state(user_id: int) -> dict[str, Any]:
    states = load_all_states()
    key = str(user_id)
    if key not in states:
        states[key] = {
            "current_chapter": DEFAULT_CHAPTER,
            "current_node": None,
            "badges": [],       # 已獲得的產區印記
            "flags": [],        # 劇情旗標,例如 found_letters
            "fog_zones": [],    # Leitner 迷霧區域:答錯或跳過的知識點
            "attempts": {},     # 每個 quiz 節點的作答次數
        }
        save_all_states(states)
    return states[key]


def update_user_state(user_id: int, **kwargs) -> None:
    states = load_all_states()
    key = str(user_id)
    if key not in states:
        get_user_state(user_id)
        states = load_all_states()
    states[key].update(kwargs)
    save_all_states(states)


def append_unique(user_id: int, field: str, value: str) -> None:
    states = load_all_states()
    key = str(user_id)
    lst = states[key].setdefault(field, [])
    if value not in lst:
        lst.append(value)
    save_all_states(states)


def record_attempt(user_id: int, node_id: str) -> int:
    states = load_all_states()
    key = str(user_id)
    attempts = states[key].setdefault("attempts", {})
    attempts[node_id] = attempts.get(node_id, 0) + 1
    save_all_states(states)
    return attempts[node_id]


# ---------------------------------------------------------------------------
# 劇情節點渲染
# ---------------------------------------------------------------------------

def get_node(chapter_id: str, node_id: str) -> dict[str, Any]:
    story = load_story()
    return story["chapters"][chapter_id]["nodes"][node_id]


def build_keyboard(node: dict[str, Any], chapter_id: str) -> InlineKeyboardMarkup | None:
    choices = node.get("choices", [])
    if not choices:
        return None
    buttons = []
    for idx, choice in enumerate(choices):
        # callback_data 格式: "goto:章節:目標節點:選項索引"
        # 索引用來讓 handler 知道這個選項是否為 quiz 的正確答案
        callback_data = f"goto:{chapter_id}:{choice['next']}:{idx}"
        buttons.append([InlineKeyboardButton(choice["label"], callback_data=callback_data)])
    return InlineKeyboardMarkup(buttons)


async def send_node(update_or_query, context: ContextTypes.DEFAULT_TYPE,
                     chapter_id: str, node_id: str, user_id: int) -> None:
    node = get_node(chapter_id, node_id)
    text = node["text"]
    keyboard = build_keyboard(node, chapter_id)

    # 節點副作用:發放印記 / 設定旗標 / 加入迷霧區域
    if node.get("grants_badge"):
        append_unique(user_id, "badges", node["grants_badge"])
        text += f"\n\n🏅 獲得產區印記:{node['grants_badge']}"

    update_user_state(user_id, current_chapter=chapter_id, current_node=node_id)

    if hasattr(update_or_query, "message") and update_or_query.message:
        # CallbackQuery: 編輯原本的訊息,維持對話簡潔
        await update_or_query.edit_message_text(text, reply_markup=keyboard)
    else:
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=keyboard)


# ---------------------------------------------------------------------------
# 指令與按鈕處理
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    chapter_id = state["current_chapter"]
    story = load_story()
    start_node = story["chapters"][chapter_id]["start_node"]

    if state["current_node"] is None:
        node_id = start_node
    else:
        node_id = state["current_node"]  # 玩家中斷後可以從上次的節點繼續

    node = get_node(chapter_id, node_id)
    keyboard = build_keyboard(node, chapter_id)
    await update.message.reply_text(node["text"], reply_markup=keyboard)
    update_user_state(user_id, current_node=node_id)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/status 讓玩家查看目前收集的印記與迷霧區域(複習清單)"""
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    badges = state.get("badges", []) or ["(尚未獲得任何印記)"]
    fog = state.get("fog_zones", []) or ["(沒有需要複習的知識點)"]

    text = (
        "🏅 已獲得的產區印記:\n"
        + "\n".join(f"  · {b}" for b in badges)
        + "\n\n🌫️ 迷霧區域(下次會以新題目重新出現):\n"
        + "\n".join(f"  · {f}" for f in fog)
    )
    await update.message.reply_text(text)


async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    _, chapter_id, next_node_id, choice_idx_str = query.data.split(":")
    choice_idx = int(choice_idx_str)

    state = get_user_state(user_id)
    current_node = get_node(chapter_id, state["current_node"])
    choice = current_node["choices"][choice_idx]

    # 若目前節點是品飲判斷題,記錄作答並依對錯決定要不要標記迷霧區域
    if current_node.get("type") == "quiz":
        attempt_count = record_attempt(user_id, state["current_node"])
        if not choice.get("correct", True):
            append_unique(user_id, "fog_zones", state["current_node"])
            logger.info(
                "user %s answered %s incorrectly (attempt #%d)",
                user_id, state["current_node"], attempt_count,
            )
        # 顯示知識卡片(無論對錯,答錯的敘事後果節點裡也可以再插入引導)
        if current_node.get("knowledge_card"):
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📖 知識卡片:\n{current_node['knowledge_card']}",
            )

    # 節點自帶的旗標設定(例如找到信件)
    if choice.get("sets_flag"):
        append_unique(user_id, "flags", choice["sets_flag"])
    if choice.get("sets_fog"):
        append_unique(user_id, "fog_zones", choice["sets_fog"])

    await send_node(query, context, chapter_id, next_node_id, user_id)


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "請先設定環境變數 TELEGRAM_BOT_TOKEN(跟 BotFather 申請後取得)"
        )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(handle_choice, pattern=r"^goto:"))

    logger.info("風土探勘者 bot 啟動中...")
    app.run_polling()


if __name__ == "__main__":
    main()
