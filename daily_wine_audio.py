"""
每日布根地雙語聽力練習腳本（edge-tts 版）
"""

import os
import json
import random
import asyncio
from datetime import datetime

import requests
import edge_tts

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

EN_VOICE = "en-US-AriaNeural"
FR_VOICE = "fr-FR-DeniseNeural"

TOPICS = [
    "Volnay", "Pommard", "Meursault", "Gevrey-Chambertin", "Chablis",
    "Nuits-Saint-Georges", "Vosne-Romanée", "Puligny-Montrachet",
    "Chambolle-Musigny", "Aloxe-Corton",
    "climat 分級概念", "Premier Cru 與 Grand Cru 的差異",
    "布根地的石灰岩土壤", "Côte de Nuits 與 Côte de Beaune 的差異",
]


def pick_topic() -> str:
    return random.choice(TOPICS)


def generate_bilingual_text(topic: str) -> dict:
    prompt = f"""請針對布根地酒鄉主題「{topic}」，生成學習用短文。

要求：
1. 英文版：高中一年級程度，60-80字，用簡單句型，介紹這個主題相關的酒或風土特色
2. 法文版：B1程度，80-120字，可用1-2個稍進階詞彙
3. 各附3-5個生字，附中文意思

只回傳這個 JSON 格式，不要有其他文字或 markdown 符號：
{{"en": "...", "fr": "...", "vocab_en": ["word - 中文意思"], "vocab_fr": ["mot - 中文意思"]}}
"""
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 700,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    raw = resp.json()["content"][0]["text"].strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


async def _synthesize_async(text: str, voice_name: str, filepath: str) -> None:
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(filepath)


def synthesize_speech(text: str, voice_name: str, filepath: str) -> str:
    asyncio.run(_synthesize_async(text, voice_name, filepath))
    return filepath


def send_telegram_message(text: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text})
    r.raise_for_status()


def send_telegram_audio(filepath: str, caption: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio"
    with open(filepath, "rb") as f:
        r = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
            files={"audio": f},
        )
    r.raise_for_status()


def main() -> None:
    topic = pick_topic()
    content = generate_bilingual_text(topic)

    vocab_en = "\n".join(f"• {v}" for v in content.get("vocab_en", []))
    vocab_fr = "\n".join(f"• {v}" for v in content.get("vocab_fr", []))

    message = (
        f"📅 {datetime.now().strftime('%Y-%m-%d')} 每日布根地聽力：{topic}\n\n"
        f"🇬🇧 {content['en']}\n\n生字：\n{vocab_en}\n\n"
        f"🇫🇷 {content['fr']}\n\n生字：\n{vocab_fr}"
    )
    send_telegram_message(message)

    en_file = synthesize_speech(content["en"], EN_VOICE, "/tmp/daily_en.mp3")
    fr_file = synthesize_speech(content["fr"], FR_VOICE, "/tmp/daily_fr.mp3")

    send_telegram_audio(en_file, "🇬🇧 英文語音")
    send_telegram_audio(fr_file, "🇫🇷 法文語音")


if __name__ == "__main__":
    main()