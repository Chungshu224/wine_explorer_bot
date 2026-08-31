# 《風土探勘者》Telegram Bot 雛形

## 檔案說明
- `bot.py` — 主程式,狀態機邏輯與 Telegram 互動處理
- `story_data.json` — 劇情樹(多章節結構,可自行擴充新村莊)
- `user_state.json` — 執行後自動產生,儲存每位玩家的進度(印記/迷霧區域/答題紀錄)

## 本地執行方式
```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="你跟 BotFather 申請到的 token"
python bot.py
```

## 指令
- `/start` — 開始遊戲,或從上次中斷的節點繼續
- `/chapters` — 章節地圖總覽:已解鎖章節可直接點按鈕跳過去,未解鎖顯示還需要哪些印記
- `/status` — 查看目前收集的產區印記,以及「迷霧區域」(答錯待複習的知識點)

## story_data.json 資料結構(多章節版)

```
{
  "region": "夜丘 Côte de Nuits",
  "chapter_order": ["章節id1", "章節id2", ...],   // 建議遊玩順序,/chapters 依此排序顯示

  "chapters": {
    "章節id": {
      "title": "第X章:標題",
      "meta": {
        "village": "村莊英文名",
        "tier": "core | waypoint | outpost",       // 對應「核心村莊/中繼站/知識驛站」分層設計
        "tier_label": "核心村莊",                    // 顯示用中文標籤
        "style_focus": "這章要教的風土對比重點",
        "requires_badges": ["需要的印記1", "..."]    // 章節解鎖條件,留空陣列代表一開始就解鎖
      },
      "start_node": "opening",
      "nodes": { ... }
    }
  }
}
```

### 節點層級欄位
- `text`:敘事文字
- `choices`:選項陣列,每個選項有:
  - `label`:按鈕文字
  - `next`:目標節點 id
  - `chapter`(可選):目標章節 id,不填則預設留在目前章節。用這個欄位做跨章節跳轉(例如某章結尾直接接到下一章開場)
  - `correct`(quiz 節點專用):布林值,是否為正確答案
  - `sets_flag` / `sets_fog`(可選):設定劇情旗標或加入 Leitner 複習區
- `type: "quiz"`:標記為品飲判斷題
- `knowledge_card`:quiz 節點答題後彈出的知識卡片文字
- `grants_badge`:抵達此節點時發放的產區印記名稱
- `is_ending`:標記章節結尾節點

## 章節分層設計(擴充新村莊時參考)

| tier | 說明 | 建議劇情量 |
|---|---|---|
| `core`(核心村莊) | 完整角色支線,貫穿主線劇情 | 3-4 個章節深度,像 Étienne/Marguerite 這條線 |
| `waypoint`(中繼站) | 單章短劇情,靠核心角色「轉介」帶出 | 1 章,可引用已建立角色 |
| `outpost`(知識驛站) | 一段對話 + 一道品飲題 + 一張知識卡片,用來補完地圖完整性 | 最輕量,不需要新角色 |

新增章節時,記得同步把章節 id 加進最上層的 `chapter_order`,否則 `/chapters` 選單不會顯示它。

## 接下來可以擴充的部分
1. 把 `knowledge_card` 內容換成 Bourgogne Aujourd'hui 資料庫裡對應文章的摘要與出處
2. 依照分層設計新增更多村莊章節(例如梧玖 Vougeot、馮內-侯瑪內 Vosne-Romanée)
3. 加入排程機制(例如 APScheduler),讓 fog_zones 裡的知識點在幾天後透過新訊息主動推送複習
4. 把 user_state.json 換成 SQLite 或串接你既有的 Supabase,方便多裝置同步進度、也解決 Railway 重新部署後進度重置的問題

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
7. 之後每次 `git push`,Railway 會自動偵測並重新部署,不用手動操作

### ⚠️ 重要:關於 user_state.json 的持久性

Railway 的免費方案預設是**無狀態檔案系統**——每次重新部署,`user_state.json` 會被重置,玩家進度會消失。有兩個處理方式:

- **短期測試沒關係**,先不用管,重新部署再玩一次就好
- **要長期保留進度**,建議兩個方向擇一:
  1. 在 Railway 加掛一個 **Volume**(專案設定裡的 Volumes 分頁),掛載到 `/app` 目錄,讓 `user_state.json` 持久化
  2. 改用你已經在用的 **Supabase**,把 `get_user_state` / `update_user_state` 那幾個函式改成讀寫 Supabase 資料表

### Railway 費用提醒
新帳號通常有一次性的免費試用額度(以 Railway 官網當下公告為準,額度政策會變動),小型 Telegram bot 這種服務通常能撐一段時間。額度用完後是照使用量計費,可在 Usage 頁面隨時查看花費。
