# 《風土探勘者》Telegram Bot 雛形

## 檔案說明
- `bot.py` — 主程式,狀態機邏輯與 Telegram 互動處理
- `story_data.json` — 劇情樹(多故事線 × 多章節結構,可自行擴充新村莊/新故事線)
- 玩家進度**不再存在本機檔案**,改存在 Supabase 的 `wine_bot_users` / `wine_bot_progress` 兩張表,詳見下方「進度持久化」章節

## 本地執行方式
```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="你跟 BotFather 申請到的 token"
export SUPABASE_URL="https://你的專案id.supabase.co"
export SUPABASE_ANON_KEY="你的 anon 或 publishable key"
python bot.py
```


## 多故事線架構(campaigns)

從這個版本開始,`story_data.json` 最上層是 `campaigns`,每條故事線各自獨立:

```
{
  "campaigns": {
    "故事線id": {
      "title": "故事線標題",
      "tagline": "一句話簡介",
      "knowledge_focus": "這條故事線主打的知識領域",
      "region": "產區",
      "chapter_order": [...],
      "chapters": {...}     // 結構跟原本單一故事線版本完全一樣
    }
  }
}
```

### 目前收錄的故事線

| 故事線 | 知識主線 | 章節數 |
|---|---|---|
| **風土偵探** | 村莊風土對比、AOC 制度邏輯、品飲推理方法論 | 10 章 |
| **地契與繼承** | 均分繼承制、地塊破碎化、GFA/美塔亞/indivision 等共有制度、négociant vs domaine、根瘤蚜重建史 | 6 章 |

### 地契與繼承線 · 章節總表

| 章節 | 層級 | 需要印記 |
|---|---|---|
| 第一章:公證處的檔案室 | 核心章節 | 無 |
| 驛站:不擁有土地的種植者(美塔亞制) | 知識驛站 | 無 |
| 第二章:半壟葡萄藤的遺產 | 核心章節 | 均分繼承制 |
| 驛站:分級金字塔的地價 | 知識驛站 | 無 |
| 支線:根瘤蚜蟲害之後 | 中繼站 | 均分繼承制 |
| 支線:懸而未決的共有(indivision) | 中繼站 | GFA 與裝瓶制度 |

兩條故事線共用同一個世界觀(同村莊、同時代,角色可交叉出現)——「地契與繼承」的主角是同一位調查者,幾個月後受雇於公證處,途中會發現跟「風土偵探」重疊的家族線索,形成兩條故事互相佐證的效果。

### 玩家進度按故事線分開儲存(Supabase)

進度存在 Supabase 專案(跟你的 POS 系統共用同一個 project)裡的兩張表:

```
wine_bot_users
  telegram_user_id (PK)  active_campaign  updated_at

wine_bot_progress
  telegram_user_id, campaign_id (複合 PK)
  current_chapter  current_node  badges(jsonb)  flags(jsonb)  fog_zones(jsonb)  attempts(jsonb)  updated_at
```

玩家可以隨時用 `/campaigns` 切換故事線,每條線的印記、進度、迷霧區域完全獨立,互不影響,而且**重新部署也不會遺失**。

### 新增指令
- `/campaigns` — 顯示所有故事線、目前在哪一條、每條線已獲得的印記數,可直接點按鈕切換

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


## 目前收錄章節(十章)

| 章節 | 村莊 | 層級 | 需要印記 |
|---|---|---|---|
| 第一章 | Gevrey-Chambertin | 核心村莊 | 無 |
| 驛站 | Fixin | 知識驛站 | 無 |
| 驛站 | Marsannay | 知識驛站 | 無 |
| 第二章 | Chambolle-Musigny | 核心村莊 | Chambertin Clos de Bèze |
| 支線 | Morey-Saint-Denis | 中繼站 | Chambertin Clos de Bèze |
| 驛站 | Côte de Nuits-Villages | 知識驛站 | 無 |
| 第三章 | Vougeot | 核心村莊 | Les Amoureuses |
| 支線 | Nuits-Saint-Georges | 中繼站 | Les Amoureuses |
| 終章 | Vosne-Romanée | 核心村莊(終章) | Clos de Vougeot |
| 彩蛋支線 | Flagey-Échézeaux | 中繼站(完結後) | 馮內-侯瑪內 · 守夜人的地(即完成終章) |

中繼站/知識驛站不會卡住主線進度,是平行的選讀支線,適合想多累積印記或補充風土知識的玩家。弗拉吉是特別設計的「完結後彩蛋」,只有玩完終章拿到最後印記才會解鎖,適合當作系列的收尾小驚喜。

## 章節分層設計(擴充新村莊時參考)

| tier | 說明 | 建議劇情量 |
|---|---|---|
| `core`(核心村莊) | 完整角色支線,貫穿主線劇情 | 3-4 個章節深度,像 Étienne/Marguerite 這條線 |
| `waypoint`(中繼站) | 單章短劇情,靠核心角色「轉介」帶出 | 1 章,可引用已建立角色 |
| `outpost`(知識驛站) | 一段對話 + 一道品飲題 + 一張知識卡片,用來補完地圖完整性 | 最輕量,不需要新角色 |

新增章節時,記得同步把章節 id 加進最上層的 `chapter_order`,否則 `/chapters` 選單不會顯示它。

## 接下來可以擴充的部分
1. 把 `knowledge_card` 內容換成 Bourgogne Aujourd'hui 資料庫裡對應文章的摘要與出處
2. 依照分層設計新增更多村莊章節或第三條故事線(例如年份與氣候變異、釀酒工藝與缺陷辨識)
3. 加入排程機制(例如 APScheduler),讓 fog_zones 裡的知識點在幾天後透過新訊息主動推送複習
4. 在 Supabase 建一個簡單的統計 View(例如「有多少人破了終章」),之後可以直接用 SQL 查詢玩家整體進度

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
5. 進到專案的 **Variables** 分頁,新增三個環境變數:
   - `TELEGRAM_BOT_TOKEN`:你的 Telegram bot token
   - `SUPABASE_URL`:`https://cpvrqwtoaqqsdosgiupy.supabase.co`
   - `SUPABASE_ANON_KEY`:到 Supabase 專案的 **Settings → API** 分頁複製 anon / publishable key
6. 儲存後 Railway 會自動重新部署,到 **Deployments** 分頁看 log,出現「風土探勘者 bot(Supabase 持久化版)啟動中...」就成功了
7. 之後每次 `git push`,Railway 會自動偵測並重新部署,不用手動操作

### ✅ 進度持久化已解決

玩家進度存在 Supabase,不再依賴 Railway 的本機檔案系統,**重新部署、重啟、甚至換一台機器跑,進度都不會遺失**。之前提到的 Railway Volume 方案不再需要。

這張表用的是 anon/publishable key 搭配寬鬆的 RLS policy(因為 Telegram user_id 不是 Supabase Auth 的身份,沒辦法用一般的「只能存取自己資料」規則)。這代表理論上任何拿得到這組 anon key 的人都能讀寫這兩張表——但因為裡面只存遊戲進度(不是金流或個資),風險可以接受。如果之後想收緊,可以改成透過一個小型後端中介(例如 Supabase Edge Function)搭配 service_role key 存取,不直接把 anon key 暴露給 bot 本身。

### Railway 費用提醒
新帳號通常有一次性的免費試用額度(以 Railway 官網當下公告為準,額度政策會變動),小型 Telegram bot 這種服務通常能撐一段時間。額度用完後是照使用量計費,可在 Usage 頁面隨時查看花費。
