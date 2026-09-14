"""
每日布根地雙語聽力練習腳本（edge-tts 版）
------------------------------------
流程：
1. 隨機挑一個布根地相關主題
2. 呼叫 Claude API 生成英文（高一程度）+ 法文（B1程度）短文與生字
3. 用 edge-tts（免費，不需 API key）把兩段文字轉成 mp3
4. 透過既有的 Telegram bot 把文字 + 語音檔推播到你自己的聊天室


用法：
    每天固定時間執行一次即可（用 Railway cron 排程觸發），
    不需要常駐進程，跑完就結束。

需要的套件：
    pip install edge-tts requests

需要的環境變數（比 Azure 版少兩組，不用申請任何語音服務帳號）：
    TELEGRAM_BOT_TOKEN     沿用你現有 bot 的 token
    TELEGRAM_CHAT_ID       要推播到的聊天室 id（你自己跟 bot 的對話）
    ANTHROPIC_API_KEY      用來生成文章內容
"""
