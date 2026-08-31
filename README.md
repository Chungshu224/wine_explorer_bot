# 《風土探勘者》Telegram Bot 雛形

## 檔案說明
- `bot.py` — 主程式,狀態機邏輯與 Telegram 互動處理
- `story_data.json` — 第一章劇情樹(可自行擴充新章節)
- `user_state.json` — 執行後自動產生,儲存每位玩家的進度(印記/迷霧區域/答題紀錄)

## 本地執行方式
```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="你跟 BotFather 申請到的 token"
python bot.py
```

## 部署到 Railway

1. 把這個資料夾推到一個新的 GitHub repo(私有 repo 也可以,Railway 支援)
   ```bash
   git init
   git add .
   git commit -m "風土探勘者 bot 雛形"
   git branch -M main
   git remote add origin https://github.com/你的帳號/wine_explorer_bot.git
   git push -u origin main
   ```
2. 到 [railway.app](https://railway.app) 用 GitHub 帳號登入
3. **New Project** → **Deploy from GitHub repo** → 選你剛推上去的 repo
4. Railway 會自動偵測到 `requirements.txt` 跟 `Procfile`,照 `worker: python bot.py` 這行啟動
5. 進到專案的 **Variables** 分頁,新增環境變數:
   - Key: `TELEGRAM_BOT_TOKEN`
   - Value: 你的 token
6. 儲存後 Railway 會自動重新部署,到 **Deployments** 分頁看 log,出現「風土探勘者 bot 啟動中...」就成功了

### ⚠️ 重要:關於 user_state.json 的持久性

Railway 的免費方案預設是**無狀態檔案系統**——每次重新部署,`user_state.json` 會被重置,玩家進度會消失。有兩個處理方式:

- **短期測試沒關係**,先不用管,重新部署再玩一次就好
- **要長期保留進度**,建議兩個方向擇一:
  1. 在 Railway 加掛一個 **Volume**(專案設定裡的 Volumes 分頁),掛載到 `/app` 目錄,讓 `user_state.json` 持久化
  2. 改用你已經在用的 **Supabase**(反正你 POS 系統也是用它),把 `get_user_state` / `update_user_state` 那幾個函式改成讀寫 Supabase 資料表,這樣多裝置、多次部署都不會丟資料——這個之後可以幫你改

### Railway 費用提醒
新帳號通常有一次性的免費試用額度(以 Railway 官網當下公告為準,額度政策會變動),小型 Telegram bot 這種 24 小時但耗資源很低的服務,額度通常能撐一段時間。額度用完後是**照使用量計費**,不是整月訂閱,你可以在 Railway 的 Usage 頁面隨時盯著花費。

## 指令
- `/start` — 開始遊戲,或從上次中斷的節點繼續
- `/status` — 查看目前收集的產區印記,以及「迷霧區域」(答錯待複習的知識點)

## 劇情樹格式(story_data.json)
每個節點可以有:
- `text`:敘事文字
- `choices`:選項陣列,每個選項有 `label`(按鈕文字)與 `next`(目標節點 id)
- `type: "quiz"`:標記為品飲判斷題,選項可加 `correct: true/false`
- `knowledge_card`:quiz 節點答題後彈出的知識卡片文字
- `grants_badge`:抵達此節點時發放的產區印記名稱
- `sets_flag` / `sets_fog`(選項層級):設定劇情旗標或加入迷霧複習區

## 接下來可以擴充的部分
1. 把 `knowledge_card` 內容換成 Bourgogne Aujourd'hui 資料庫裡對應文章的摘要與出處
2. 新增第二章 `clos_st_jacques_02` 到 story_data.json 的 chapters 底下
3. 加入排程機制(例如 APScheduler),讓 fog_zones 裡的知識點在幾天後透過新訊息主動推送複習
4. 把 user_state.json 換成 SQLite 或串接你既有的 Supabase,方便多裝置同步進度
