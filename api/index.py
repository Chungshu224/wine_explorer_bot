"""Vercel Serverless 入口：Telegram Webhook → python-telegram-bot。

每次請求建立一個 Application、處理一則 update、結束；進度全部存在 Supabase。
環境變數：TELEGRAM_BOT_TOKEN、SUPABASE_URL、SUPABASE_ANON_KEY、
          TELEGRAM_WEBHOOK_SECRET（選填，建議設定，和 setWebhook 的 secret_token 相同）
"""
import asyncio
import json
import logging
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from telegram import Update  # noqa: E402

import bot  # noqa: E402

logger = logging.getLogger(__name__)


async def _process(data: dict) -> None:
    app = bot.build_application(webhook=True)
    await app.initialize()
    try:
        await app.process_update(Update.de_json(data, app.bot))
    finally:
        await app.shutdown()


class handler(BaseHTTPRequestHandler):
    def _reply(self, code: int, body: str = "ok") -> None:
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):  # 健康檢查：瀏覽器開網址看到 ok 代表部署成功
        self._reply(200, "wine bot webhook ok")

    def do_POST(self):
        secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
        if secret and self.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
            self._reply(403, "forbidden")
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
            asyncio.run(_process(data))
        except Exception:  # 一律回 200，避免 Telegram 反覆重送同一則更新
            logger.exception("webhook 處理失敗")
        self._reply(200)
