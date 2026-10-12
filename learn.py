"""
/learn — 勃艮第闖關學習模式（資料表 wc_*，與劇情模式 wine_bot_* 互不影響）

流程：/learn → 關卡地圖 → 進入關卡 → 逐題作答（選擇題 / 是非題 / 回想題）
      → 結算（≥解鎖門檻即通關，解鎖下一關）。答題結果同步寫入 Leitner 間隔複習表 wc_user_cards。
進行中的關卡暫存在 context.user_data（重新部署會中斷該次關卡，但進度與通關紀錄都在 Supabase）。
"""

import os
import random
from datetime import date, timedelta
from typing import Any

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes


SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
_KEY = os.environ.get("SUPABASE_ANON_KEY", "")


def _headers() -> dict[str, str]:
    return {"apikey": _KEY, "Authorization": f"Bearer {_KEY}", "Content-Type": "application/json"}

INTERVALS = [0, 1, 3, 7, 16]  # Leitner 箱 0–4 的複習間隔（天），與眼鏡版相同
LETTERS = "ABCD"
RECALL_TYPES = {"recall_list", "flip_cloze"}
REVERSE_TYPES = {"blind_clue", "mcq_style"}  # 給描述，猜名稱


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
        r = await c.post(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers={**_headers(), "Prefer": "return=minimal"},
            json=row,
        )
        r.raise_for_status()


# ---------------------------------------------------------------- 關卡地圖
async def _load_map(user_id: int):
    levels = await _get("wc_levels", {"deck": "eq.bg", "select": "*", "order": "ord.asc"})
    prog = await _get("wc_user_levels", {"telegram_user_id": f"eq.{user_id}", "select": "*"})
    by_id = {p["level_id"]: p for p in prog}
    cleared = {lid for lid, p in by_id.items() if p["cleared"]}
    for lv in levels:
        lv["unlocked"] = all(r in cleared for r in (lv["requires"] or []))
        lv["best"] = by_id.get(lv["id"], {}).get("best_pct", 0)
        lv["cleared"] = lv["id"] in cleared
    return levels


def _map_view(levels: list[dict[str, Any]]):
    lines = ["🍷 勃艮第闖關學習", "每關達 80% 即通關並解鎖下一關\n"]
    buttons: list[list[InlineKeyboardButton]] = []
    nxt = None
    for lv in levels:
        icon = "✅" if lv["cleared"] else ("▶️" if lv["unlocked"] else "🔒")
        boss = "👑 " if lv["kind"] == "boss" else ""
        score = f"（最佳 {lv['best']}%）" if lv["best"] else ""
        lines.append(f"{icon} {lv['ord']}. {boss}{lv['title']}{score}")
        if lv["unlocked"] and not lv["cleared"] and nxt is None:
            nxt = lv
    if nxt:
        buttons.append([InlineKeyboardButton(f"▶️ 繼續：第 {nxt['ord']} 關", callback_data=f"lvs:{nxt['ord']}")])
    done = [lv for lv in levels if lv["cleared"]]
    # 已通關的關卡可重打（每列兩顆，只列最近 6 關避免訊息過長）
    row: list[InlineKeyboardButton] = []
    for lv in done[-6:]:
        row.append(InlineKeyboardButton(f"🔁 第 {lv['ord']} 關", callback_data=f"lvs:{lv['ord']}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    if not nxt and len(done) == len(levels):
        lines.append("\n🏆 全部通關！可以重打任何一關。")
    return "\n".join(lines), InlineKeyboardMarkup(buttons)


async def learn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    levels = await _load_map(update.effective_user.id)
    text, kb = _map_view(levels)
    await update.message.reply_text(text, reply_markup=kb)


async def handle_map(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    levels = await _load_map(q.from_user.id)
    text, kb = _map_view(levels)
    await q.edit_message_text(text, reply_markup=kb)


# ---------------------------------------------------------------- 進入關卡
def _flat(s: str) -> str:
    return " / ".join(x.strip() for x in s.split("\n") if x.strip())


def _name(card: dict[str, Any]) -> str:
    return card["q"].split("\n")[0].strip()


async def handle_level_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    ord_ = int(q.data.split(":")[1])
    levels = await _load_map(q.from_user.id)
    lv = next(l for l in levels if l["ord"] == ord_)
    if not lv["unlocked"]:
        await q.answer("這關還沒解鎖", show_alert=True)
        return
    items = await _get(
        "wc_level_items",
        {"level_id": f"eq.{lv['id']}", "select": "pos,qtype,is_review,wc_cards(*)", "order": "pos.asc"},
    )
    uids = {u for it in items for u in it["wc_cards"]["distractors"]}
    quoted = ",".join(f'"{u}"' for u in uids)
    pool = {c["uid"]: c for c in await _get("wc_cards", {"uid": f"in.({quoted})", "select": "uid,q,a"})} if uids else {}
    context.user_data["wc"] = {
        "level": lv, "items": items, "pool": pool, "idx": 0, "correct": 0, "cur": None,
    }
    await q.edit_message_text(f"第 {lv['ord']} 關：{lv['title']}\n共 {len(items)} 題，準備好了！")
    await _ask(q.message, context)


# ---------------------------------------------------------------- 出題
def _build_question(item: dict[str, Any], pool: dict[str, Any]) -> dict[str, Any]:
    card = item["wc_cards"]
    qtype = item["qtype"]
    wrong_cards = [pool[u] for u in card["distractors"] if u in pool]
    tag = "🔁 複習  " if item["is_review"] else ""

    if qtype in RECALL_TYPES or len(wrong_cards) < 2:
        return {"mode": "recall", "text": f"{tag}{card['q']}", "answer": card["a"], "uid": card["uid"]}

    if qtype.startswith("tf_"):
        use_true = random.random() < 0.5
        shown = card["a"]
        if not use_true:
            alts = [w["a"] for w in wrong_cards if _flat(w["a"]) != _flat(card["a"])]
            if alts:
                shown = random.choice(alts)
            else:
                use_true = True
        stem = card["q"].split("\n")
        body = " ".join(x for x in stem[1:] if x.strip()) or stem[0]
        text = f"{tag}{stem[0]}\n{body}\n\n答案是：{_flat(shown)}\n\n這個說法正確嗎？"
        return {"mode": "tf", "text": text, "truth": use_true, "answer": card["a"], "uid": card["uid"]}

    # 選擇題選項不足（例如品種題答案常重複）→ 改成是非題
    if qtype.startswith("mcq") or qtype in REVERSE_TYPES:
        f = _name if qtype in REVERSE_TYPES else (lambda c: _flat(c["a"]))
        uniq = {f(w) for w in wrong_cards} - {f(card)}
        if len(uniq) < 2:
            return _build_question({**item, "qtype": "tf_auto"}, pool)

    # 選擇題（含反向的「給描述猜名稱」）
    if qtype in REVERSE_TYPES:
        stem = f"{tag}這段描述的是哪一個？\n\n{card['a']}"
        correct = _name(card)
        wrongs = [_name(w) for w in wrong_cards]
        reveal = f"{_name(card)}：{_flat(card['a'])}"
    else:
        stem = f"{tag}{card['q']}"
        correct = _flat(card["a"])
        wrongs = [_flat(w["a"]) for w in wrong_cards]
        reveal = _flat(card["a"])
    wrongs = [w for w in dict.fromkeys(wrongs) if w != correct]
    options = random.sample(wrongs, min(3, len(wrongs))) + [correct]
    random.shuffle(options)
    lines = "\n".join(f"{LETTERS[i]}. {o}" for i, o in enumerate(options))
    return {"mode": "mcq", "text": f"{stem}\n\n{lines}", "options": options, "correct": options.index(correct),
            "answer": reveal, "uid": card["uid"]}


async def _ask(message, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = context.user_data["wc"]
    if s["idx"] >= len(s["items"]):
        await _finish(message, context)
        return
    cur = _build_question(s["items"][s["idx"]], s["pool"])
    s["cur"] = cur
    head = f"［{s['idx'] + 1}/{len(s['items'])}］\n"
    if cur["mode"] == "mcq":
        kb = [[InlineKeyboardButton(LETTERS[i], callback_data=f"wa:{i}") for i in range(len(cur["options"]))]]
    elif cur["mode"] == "tf":
        kb = [[InlineKeyboardButton("✅ 正確", callback_data="wa:1"), InlineKeyboardButton("❌ 錯誤", callback_data="wa:0")]]
    else:
        kb = [[InlineKeyboardButton("👀 看答案", callback_data="wa:show")]]
    await message.reply_text(head + cur["text"], reply_markup=InlineKeyboardMarkup(kb))


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
    s = context.user_data.get("wc")
    if not s or not s.get("cur"):
        await q.answer("這一關已中斷，請用 /learn 重新開始", show_alert=True)
        return
    await q.answer()
    cur = s["cur"]
    val = q.data.split(":")[1]

    if cur["mode"] == "recall" and val == "show":
        kb = [[InlineKeyboardButton("✅ 我會", callback_data="wa:yes"), InlineKeyboardButton("❌ 不會", callback_data="wa:no")]]
        await q.edit_message_text(f"{q.message.text}\n\n答案：\n{cur['answer']}", reply_markup=InlineKeyboardMarkup(kb))
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
    cur_uid = cur["uid"]
    kb = [[InlineKeyboardButton("下一題 ➡️", callback_data="wn"), InlineKeyboardButton("🚩 回報錯誤", callback_data=f"wr:{s['idx']}")]]
    await q.edit_message_text(f"{q.message.text}\n\n{mark}{detail}", reply_markup=InlineKeyboardMarkup(kb))
    s["cur"] = None
    s["last_uid"] = cur_uid


async def handle_next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    s = context.user_data.get("wc")
    if not s:
        await q.answer("這一關已中斷，請用 /learn 重新開始", show_alert=True)
        return
    await q.answer()
    await q.edit_message_reply_markup(reply_markup=None)
    s["idx"] += 1
    await _ask(q.message, context)


async def handle_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    s = context.user_data.get("wc")
    idx = int(q.data.split(":")[1])
    if not s or idx >= len(s["items"]):
        await q.answer("已中斷", show_alert=True)
        return
    uid = s["items"][idx]["wc_cards"]["uid"]
    await _insert("wc_reports", {"telegram_user_id": q.from_user.id, "card_uid": uid, "note": "button"})
    await q.answer("已回報，謝謝！", show_alert=True)


# ---------------------------------------------------------------- 結算
async def _finish(message, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = context.user_data.pop("wc")
    lv = s["level"]
    total = len(s["items"])
    pct = round(100 * s["correct"] / total)
    passed = pct >= (lv["unlock_pct"] or 80)
    user_id = message.chat.id  # 私訊中 chat.id == user id
    rows = await _get("wc_user_levels", {"telegram_user_id": f"eq.{user_id}", "level_id": f"eq.{lv['id']}", "select": "*"})
    old = rows[0] if rows else {"best_pct": 0, "attempts": 0, "cleared": False}
    await _upsert("wc_user_levels", {
        "telegram_user_id": user_id, "level_id": lv["id"],
        "best_pct": max(old["best_pct"], pct), "attempts": old["attempts"] + 1,
        "cleared": old["cleared"] or passed,
    })
    if passed:
        extra = f"\n🏅 獲得：{lv['reward']}" if lv.get("reward") and not old["cleared"] else ""
        text = f"🎉 通關！{s['correct']}/{total}（{pct}%）{extra}\n下一關已解鎖。"
    else:
        text = f"{s['correct']}/{total}（{pct}%）\n需要 {lv['unlock_pct']}% 才能通關，再試一次吧！"
    kb = [[InlineKeyboardButton("🔁 再打一次", callback_data=f"lvs:{lv['ord']}"),
           InlineKeyboardButton("🗺️ 關卡地圖", callback_data="wmap")]]
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))


def register(app) -> None:
    app.add_handler(CommandHandler("learn", learn_command))
    app.add_handler(CallbackQueryHandler(handle_map, pattern=r"^wmap$"))
    app.add_handler(CallbackQueryHandler(handle_level_start, pattern=r"^lvs:"))
    app.add_handler(CallbackQueryHandler(handle_answer, pattern=r"^wa:"))
    app.add_handler(CallbackQueryHandler(handle_next, pattern=r"^wn$"))
    app.add_handler(CallbackQueryHandler(handle_report, pattern=r"^wr:"))
