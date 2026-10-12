"""
/learn — 葡萄酒闖關學習模式（多國題庫）

資料：data/learn/index.json（國家清單）、data/learn/<deck>.json（關卡、題目、干擾選項），
      由 g2-italian-wine-cards 專案的 tools/build_levels.py 產生，隨程式一起部署（不需要資料庫存題庫）。
進度：Supabase wc_user_levels（通關紀錄）、wc_user_cards（Leitner 間隔複習）、
      wc_sessions（進行中的關卡；無伺服器環境每次請求都是新的，不能放記憶體）。
流程：/learn → 選國家 → 選產區（軌道）→ 關卡 → 逐題作答 → 結算（≥80% 通關並解鎖下一關）。
"""

import json
import os
import random
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

DATA_DIR = Path(__file__).parent / "data" / "learn"
INTERVALS = [0, 1, 3, 7, 16]  # Leitner 箱 0–4 的複習間隔（天），與眼鏡版相同
LETTERS = "ABCD"
RECALL_TYPES = {"recall_list", "flip_cloze"}
REVERSE_TYPES = {"blind_clue"}  # 給描述，猜名稱

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
_KEY = os.environ.get("SUPABASE_ANON_KEY", "")


def _headers() -> dict[str, str]:
    return {"apikey": _KEY, "Authorization": f"Bearer {_KEY}", "Content-Type": "application/json"}


# ---------------------------------------------------------------- 題庫（本機 JSON）
@lru_cache(maxsize=None)
def _index() -> list[dict[str, Any]]:
    return json.loads((DATA_DIR / "index.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _deck(deck: str) -> dict[str, Any]:
    d = json.loads((DATA_DIR / f"{deck}.json").read_text(encoding="utf-8"))
    d["by_id"] = {lv["id"]: lv for lv in d["levels"]}
    return d


# ---------------------------------------------------------------- Supabase
async def _get(table: str, params: dict[str, str]) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=_headers(), params=params)
        r.raise_for_status()
        return r.json()


async def _upsert(table: str, row: dict[str, Any]) -> None:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers={**_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"},
            json=row,
        )
        r.raise_for_status()


async def _insert(table: str, row: dict[str, Any]) -> None:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{SUPABASE_URL}/rest/v1/{table}", headers={**_headers(), "Prefer": "return=minimal"}, json=row)
        r.raise_for_status()


async def _load(user_id: int) -> dict[str, Any] | None:
    rows = await _get("wc_sessions", {"telegram_user_id": f"eq.{user_id}", "select": "state"})
    st = rows[0]["state"] if rows and rows[0]["state"] else None
    return st if st and "deck" in st else None  # 舊版（單一勃艮第）格式的暫存視為已中斷


async def _save(user_id: int, state: dict[str, Any]) -> None:
    await _upsert("wc_sessions", {"telegram_user_id": user_id, "state": state,
                                  "updated_at": datetime.now(timezone.utc).isoformat()})


async def _drop(user_id: int) -> None:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.delete(f"{SUPABASE_URL}/rest/v1/wc_sessions", headers=_headers(),
                           params={"telegram_user_id": f"eq.{user_id}"})
        r.raise_for_status()


# ---------------------------------------------------------------- 選單：國家 → 產區 → 關卡
async def _progress(user_id: int, deck: str) -> dict[str, dict[str, Any]]:
    rows = await _get("wc_user_levels", {"telegram_user_id": f"eq.{user_id}", "level_id": f"like.{deck}:*",
                                         "select": "level_id,best_pct,cleared"})
    return {r["level_id"].split(":", 1)[1]: r for r in rows}


def _status(d: dict[str, Any], prog: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    cleared = {k for k, v in prog.items() if v["cleared"]}
    return {lv["id"]: dict(unlocked=all(r in cleared for r in lv["requires"]), cleared=lv["id"] in cleared,
                           best=prog.get(lv["id"], {}).get("best_pct", 0)) for lv in d["levels"]}


def _deck_list_view():
    lines = ["🍷 葡萄酒闖關學習", "選一個國家：\n"]
    kb = []
    row: list[InlineKeyboardButton] = []
    for it in _index():
        lines.append(f"{it['name']}：{it['cards']} 張卡・{it['levels']} 關")
        row.append(InlineKeyboardButton(it["name"], callback_data=f"wd:{it['id']}"))
        if len(row) == 3:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    return "\n".join(lines), InlineKeyboardMarkup(kb)


async def learn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text, kb = _deck_list_view()
    await update.message.reply_text(text, reply_markup=kb)


async def handle_decks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    text, kb = _deck_list_view()
    await q.edit_message_text(text, reply_markup=kb)


async def handle_deck(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """某個國家：列出產區（軌道）與各自進度。"""
    q = update.callback_query
    await q.answer()
    deck = q.data.split(":")[1]
    d = _deck(deck)
    st = _status(d, await _progress(q.from_user.id, deck))
    lines = [f"🌍 {d['name']}", ""]
    kb = []
    for t in d["tracks"]:
        lvs = [lv for lv in d["levels"] if lv["track"] == t["id"]]
        done = sum(1 for lv in lvs if st[lv["id"]]["cleared"])
        locked = not any(st[lv["id"]]["unlocked"] for lv in lvs)
        icon = "🔒" if locked else ("✅" if done == len(lvs) else "▶️")
        lines.append(f"{icon} {t['name']}（{done}/{len(lvs)} 關）")
        if not locked:
            kb.append([InlineKeyboardButton(f"{icon} {t['name']}", callback_data=f"wt:{deck}:{t['id']}")])
    kb.append([InlineKeyboardButton("⬅️ 選別的國家", callback_data="wds")])
    await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))


async def handle_track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    _, deck, track = q.data.split(":", 2)
    d = _deck(deck)
    st = _status(d, await _progress(q.from_user.id, deck))
    tname = next(t["name"] for t in d["tracks"] if t["id"] == track)
    lvs = [lv for lv in d["levels"] if lv["track"] == track]
    lines = [f"🗺️ {d['name']}・{tname}", "每關達 80% 即通關並解鎖下一關\n"]
    kb: list[list[InlineKeyboardButton]] = []
    nxt = None
    for n, lv in enumerate(lvs, 1):
        s = st[lv["id"]]
        icon = "✅" if s["cleared"] else ("▶️" if s["unlocked"] else "🔒")
        boss = "👑 " if lv["type"] == "boss" else ""
        score = f"（最佳 {s['best']}%）" if s["best"] else ""
        lines.append(f"{icon} {n}. {boss}{lv['title']}{score}")
        if s["unlocked"] and not s["cleared"] and nxt is None:
            nxt = (n, lv)
    if nxt:
        kb.append([InlineKeyboardButton(f"▶️ 繼續：第 {nxt[0]} 關", callback_data=f"lvs:{deck}:{nxt[1]['id']}")])
    redo = [(n, lv) for n, lv in enumerate(lvs, 1) if st[lv["id"]]["cleared"]][-4:]
    row: list[InlineKeyboardButton] = []
    for n, lv in redo:
        row.append(InlineKeyboardButton(f"🔁 第 {n} 關", callback_data=f"lvs:{deck}:{lv['id']}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    if not nxt and redo and all(st[lv["id"]]["cleared"] for lv in lvs):
        lines.append("\n🏆 這個產區全部通關！")
    kb.append([InlineKeyboardButton("⬅️ 返回", callback_data=f"wd:{deck}")])
    await q.edit_message_text("\n".join(lines)[:4000], reply_markup=InlineKeyboardMarkup(kb))


# ---------------------------------------------------------------- 進入關卡
def _flat(s: str) -> str:
    return " / ".join(x.strip() for x in s.split("\n") if x.strip())


def _name(card: dict[str, Any]) -> str:
    return card["q"].split("\n")[0].strip()


async def handle_level_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    _, deck, lid = q.data.split(":", 2)
    d = _deck(deck)
    lv = d["by_id"][lid]
    st = _status(d, await _progress(q.from_user.id, deck))
    if not st[lid]["unlocked"]:
        await q.answer("這關還沒解鎖", show_alert=True)
        return
    await q.answer()
    s = {"deck": deck, "level": lid, "idx": 0, "correct": 0, "cur": None}
    await q.edit_message_text(f"{lv['title']}\n共 {len(lv['items'])} 題，準備好了！")
    await _ask(q.message, q.from_user.id, s)


# ---------------------------------------------------------------- 出題
def _build_question(deck: str, item: dict[str, Any]) -> dict[str, Any]:
    cards = _deck(deck)["cards"]
    card = cards[item["id"]]
    uid = f"{deck}:{item['id']}"
    qtype = item["type"]
    wrong = [cards[x] for x in card["d"] if x in cards]
    tag = "🔁 複習  " if item.get("review") else ""

    def recall():
        return {"mode": "recall", "text": f"{tag}{card['q']}", "answer": card["a"], "uid": uid}

    if qtype in RECALL_TYPES or len(wrong) < 2:
        return recall()

    if qtype.startswith("tf_"):
        alts = [w["a"] for w in wrong if _flat(w["a"]) != _flat(card["a"])]
        if not alts:  # 沒有可用的錯誤敘述 → 不出「永遠正確」的是非題
            return recall()
        use_true = random.random() < 0.5
        shown = card["a"] if use_true else random.choice(alts)
        stem = card["q"].split("\n")
        body = " ".join(x for x in stem[1:] if x.strip()) or stem[0]
        text = f"{tag}{stem[0]}\n{body}\n\n答案是：{_flat(shown)}\n\n這個說法正確嗎？"
        return {"mode": "tf", "text": text, "truth": use_true, "answer": card["a"], "uid": uid}

    reverse = qtype in REVERSE_TYPES
    f = _name if reverse else (lambda c: _flat(c["a"]))
    uniq = {f(w) for w in wrong} - {f(card)}
    if len(uniq) < 2:  # 選項不足 → 改成是非題
        return _build_question(deck, {**item, "type": "tf_auto"})

    if reverse:
        stem = f"{tag}這段描述的是哪一個？\n\n{card['a']}"
        correct = _name(card)
        wrongs = [_name(w) for w in wrong]
        reveal = f"{_name(card)}：{_flat(card['a'])}"
    else:
        stem = f"{tag}{card['q']}"
        correct = _flat(card["a"])
        wrongs = [_flat(w["a"]) for w in wrong]
        reveal = _flat(card["a"])
    wrongs = [w for w in dict.fromkeys(wrongs) if w != correct]
    options = random.sample(wrongs, min(3, len(wrongs))) + [correct]
    random.shuffle(options)
    lines = "\n".join(f"{LETTERS[i]}. {o}" for i, o in enumerate(options))
    return {"mode": "mcq", "text": f"{stem}\n\n{lines}", "options": options, "correct": options.index(correct),
            "answer": reveal, "uid": uid}


async def _ask(message, user_id: int, s: dict[str, Any]) -> None:
    lv = _deck(s["deck"])["by_id"][s["level"]]
    if s["idx"] >= len(lv["items"]):
        await _finish(message, user_id, s)
        return
    cur = _build_question(s["deck"], lv["items"][s["idx"]])
    s["cur"] = cur
    await _save(user_id, s)
    head = f"［{s['idx'] + 1}/{len(lv['items'])}］\n"
    if cur["mode"] == "mcq":
        kb = [[InlineKeyboardButton(LETTERS[i], callback_data=f"wa:{i}") for i in range(len(cur["options"]))]]
    elif cur["mode"] == "tf":
        kb = [[InlineKeyboardButton("✅ 正確", callback_data="wa:1"), InlineKeyboardButton("❌ 錯誤", callback_data="wa:0")]]
    else:
        kb = [[InlineKeyboardButton("👀 看答案", callback_data="wa:show")]]
    await message.reply_text((head + cur["text"])[:4000], reply_markup=InlineKeyboardMarkup(kb))


# ---------------------------------------------------------------- 作答
async def _record(user_id: int, uid: str, ok: bool) -> None:
    rows = await _get("wc_user_cards", {"telegram_user_id": f"eq.{user_id}", "card_uid": f"eq.{uid}", "select": "*"})
    r = rows[0] if rows else {"box": 0, "correct": 0, "wrong": 0}
    box = min(4, r["box"] + 1) if ok else 0
    await _upsert("wc_user_cards", {
        "telegram_user_id": user_id, "card_uid": uid, "box": box,
        "due": (date.today() + timedelta(days=INTERVALS[box])).isoformat(),
        "correct": r["correct"] + (1 if ok else 0), "wrong": r["wrong"] + (0 if ok else 1),
    })


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    s = await _load(q.from_user.id)
    if not s or not s.get("cur"):
        await q.answer("這一關已中斷，請用 /learn 重新開始", show_alert=True)
        return
    await q.answer()
    cur = s["cur"]
    val = q.data.split(":")[1]

    if cur["mode"] == "recall" and val == "show":
        kb = [[InlineKeyboardButton("✅ 我會", callback_data="wa:yes"), InlineKeyboardButton("❌ 不會", callback_data="wa:no")]]
        await q.edit_message_text(f"{q.message.text}\n\n答案：\n{cur['answer']}"[:4000], reply_markup=InlineKeyboardMarkup(kb))
        return

    if cur["mode"] == "mcq":
        ok = int(val) == cur["correct"]
    elif cur["mode"] == "tf":
        ok = (val == "1") == cur["truth"]
    else:
        ok = val == "yes"

    s["correct"] += 1 if ok else 0
    await _record(q.from_user.id, cur["uid"], ok)
    mark = "✅ 答對了！" if ok else "❌ 答錯了"
    detail = f"\n正解：{cur['answer']}" if (not ok or cur["mode"] != "recall") else ""
    kb = [[InlineKeyboardButton("下一題 ➡️", callback_data="wn"), InlineKeyboardButton("🚩 回報錯誤", callback_data=f"wr:{s['idx']}")]]
    await q.edit_message_text(f"{q.message.text}\n\n{mark}{detail}"[:4000], reply_markup=InlineKeyboardMarkup(kb))
    s["cur"] = None
    await _save(q.from_user.id, s)


async def handle_next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    s = await _load(q.from_user.id)
    if not s:
        await q.answer("這一關已中斷，請用 /learn 重新開始", show_alert=True)
        return
    await q.answer()
    await q.edit_message_reply_markup(reply_markup=None)
    s["idx"] += 1
    await _ask(q.message, q.from_user.id, s)


async def handle_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    s = await _load(q.from_user.id)
    idx = int(q.data.split(":")[1])
    items = _deck(s["deck"])["by_id"][s["level"]]["items"] if s else []
    if not s or idx >= len(items):
        await q.answer("已中斷", show_alert=True)
        return
    uid = f"{s['deck']}:{items[idx]['id']}"
    await _insert("wc_reports", {"telegram_user_id": q.from_user.id, "card_uid": uid, "note": "button"})
    await q.answer("已回報，謝謝！", show_alert=True)


# ---------------------------------------------------------------- 結算
async def _finish(message, user_id: int, s: dict[str, Any]) -> None:
    await _drop(user_id)
    deck, lid = s["deck"], s["level"]
    lv = _deck(deck)["by_id"][lid]
    total = len(lv["items"])
    pct = round(100 * s["correct"] / total)
    need = lv.get("unlock_pct") or 80
    passed = pct >= need
    key = f"{deck}:{lid}"
    rows = await _get("wc_user_levels", {"telegram_user_id": f"eq.{user_id}", "level_id": f"eq.{key}", "select": "*"})
    old = rows[0] if rows else {"best_pct": 0, "attempts": 0, "cleared": False}
    await _upsert("wc_user_levels", {
        "telegram_user_id": user_id, "level_id": key,
        "best_pct": max(old["best_pct"], pct), "attempts": old["attempts"] + 1,
        "cleared": old["cleared"] or passed,
    })
    if passed:
        extra = f"\n🏅 獲得：{lv['reward']}" if lv.get("reward") and not old["cleared"] else ""
        text = f"🎉 通關！{s['correct']}/{total}（{pct}%）{extra}\n下一關已解鎖。"
    else:
        text = f"{s['correct']}/{total}（{pct}%）\n需要 {need}% 才能通關，再試一次吧！"
    track = lv["track"] if lv["track"] != "final" else None
    back = f"wt:{deck}:{track}" if track else f"wd:{deck}"
    kb = [[InlineKeyboardButton("🔁 再打一次", callback_data=f"lvs:{deck}:{lid}"),
           InlineKeyboardButton("🗺️ 關卡地圖", callback_data=back)]]
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))


def register(app) -> None:
    app.add_handler(CommandHandler("learn", learn_command))
    app.add_handler(CallbackQueryHandler(handle_decks, pattern=r"^wds$"))
    app.add_handler(CallbackQueryHandler(handle_deck, pattern=r"^wd:"))
    app.add_handler(CallbackQueryHandler(handle_track, pattern=r"^wt:"))
    app.add_handler(CallbackQueryHandler(handle_level_start, pattern=r"^lvs:"))
    app.add_handler(CallbackQueryHandler(handle_answer, pattern=r"^wa:"))
    app.add_handler(CallbackQueryHandler(handle_next, pattern=r"^wn$"))
    app.add_handler(CallbackQueryHandler(handle_report, pattern=r"^wr:"))
