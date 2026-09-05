# /campaigns 兩層(其實是三層)選單改造說明

## 改了什麼

`story_data.json`:每條故事線新增一個 `major_region` 欄位,目前全部 13 條
都標成 `"布根地 Bourgogne"`。`region`(次產區,例如「夜丘」)欄位完全沒動。

`bot.py`:選單邏輯從「產區 → 故事線」兩層,變成「大產區 → 次產區 → 故事線」
三層,但做了一個關鍵設計:**只有一個大產區時,自動跳過大產區選單**,
直接顯示次產區列表。也就是說,在波爾多真的有第一條故事線上線之前,
玩家看到的 `/start` 跟 `/campaigns` 畫面**跟現在一模一樣**,不會多按一次
按鈕,也不會看到只有布根地一個選項的奇怪選單。

等你之後幫波爾多的故事線標上 `"major_region": "波爾多 Bordeaux"`,
大產區選單會自動出現,不用再改一行程式碼。

## 新的 callback_data 路由表

| 動作 | callback_data 格式 | 說明 |
|---|---|---|
| 回到導覽最上層 | `topmenu:{mode}` | 深層選單的「回到總覽」統一走這裡 |
| 選大產區 | `selectmajor:{mode}:{major_idx}` | 只有 >1 個大產區時會出現這一層 |
| 返回大產區選單 | `majormenu:{mode}` | |
| 選次產區 | `selectregion:{mode}:{major_idx}:{region_idx}` | |
| 返回次產區選單 | `regionmenu:{mode}:{major_idx}` | |
| 選故事線開始遊玩 | `startcampaign:{idx}`(不變) | 沿用原本的扁平索引 |

`mode` 是 `"p"`(picker,`/start` 第一次選故事線用)或 `"c"`(`/campaigns`
總覽用,會多顯示已獲得印記數),跟原本邏輯一樣沒變。

## 已經跑過的測試

在沙盒裡用假資料模擬了兩種情境(見對話紀錄):
1. 目前狀態(只有布根地):確認選單直接跳過大產區層,行為跟舊版一致。
2. 模擬塞一條波爾多假故事線進去:確認大產區選單正確出現、往下點兩層
   能正常走到故事線列表、返回按鈕路徑也都正確。

沒有實際連 Telegram 或 Supabase 測試(沒有 token),純粹測選單建構
邏輯本身,建議你部署前自己在測試 bot 上點過一輪 `/start` 跟 `/campaigns`。

## 怎麼套用

**方法一:直接複製這兩個檔案**
把這個資料夾裡的 `bot.py` 跟 `story_data.json` 蓋掉你 repo 裡的同名檔案,
`git add -A && git commit -m "campaigns 選單改成三層,支援布根地/波爾多分組" && git push`。

**方法二:用 patch**
```
cd 你的wine_explorer_bot本機資料夾
git apply changes.patch
```

## 之後波爾多故事線要怎麼接

新增波爾多故事線時,在 `story_data.json` 的 `campaigns` 底下新增
campaign 物件時,記得比照布根地的格式多加一個欄位:

```json
"你的波爾多故事線id": {
  "title": "...",
  "tagline": "...",
  "knowledge_focus": "...",
  "major_region": "波爾多 Bordeaux",
  "region": "梅多克 Médoc",
  "chapter_order": [...],
  "chapters": {...}
}
```

`major_region` 用一致的字串(例如都寫 `"波爾多 Bordeaux"`,不要有時候
漏掉法文、有時候不加空格),因為分組是直接用字串比對的,拼寫不一致
會被拆成兩組。
