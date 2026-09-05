# 布根地地圖遷移到 Vue 3 + Mapbox GL 說明

## ⚠️ 套用前必須確認一件事

我把 story_data.json 裡的地圖連結,從舊的
`https://chungshu224.github.io/wine_explorer_bot/?map=xxx`
改成了 **`https://wineacademy.vercel.app/bourgogne/map-embed?map=xxx`**。

`wineacademy.vercel.app` 是我從 bordeaux-map 的 GitHub repo「About」欄位讀到的
網址,**但我不確定這是不是你目前實際在用的正式網域**(可能你後來換了自訂
網域,或這只是舊的預覽網址)。套用之前,請先確認:

1. 打開 `wine_explorer_bot_v2/story_data.json`,搜尋 `wineacademy.vercel.app`
2. 如果你的正式網域不是這個,直接在編輯器裡「全部取代」成正確的網域即可
   (共 4 處:corton、montrachet、chablis_gc、vougeot)

## 這次改了什麼

### bordeaux-map(Vue 3 + Mapbox GL 專案)

新增一個檔案:`src/components/bourgogne/BourgognePublicMapEmbed.vue`

這是一個**獨立、免登入**的地圖頁面,專門給 `wine_explorer_bot` 這個
Telegram 遊戲的深連結用。跟站內完整付費地圖(`BourgogneMapSection.vue`)
刻意分開,原因:

- 完整地圖是設計給站內導覽用的,props/state 都是為了跟
  `BourgognePage.vue` 這個父層元件配合,不是為了被外部連結直接命中而設計。
  硬掛在免登入路由上等於把整個付費地圖操作介面暴露出去,不是原本想開的
  「一扇小門」。
- 這裡的需求很單純:網址帶 `?map=xxx`,就秀出對應的產區邊界。獨立元件
  好維護,也不會被完整地圖之後的改版意外波及。

資料**沒有另外複製一份**——直接讀取你 repo 裡本來就有的
`public/bourgogne/geojson/`,跟付費地圖共用同一份檔案。渲染引擎、
Mapbox token 取得邏輯(含沒有 token 時自動退回 OSM 底圖的機制)都是
直接重用 `src/utils/getMapboxToken.js` 現成的工具函式,沒有另外發明一套。

修改一個檔案:`src/router/index.js`

新增一筆路由:

```js
{
  path: '/bourgogne/map-embed',
  name: 'BourgogneMapEmbed',
  component: () => import('../components/bourgogne/BourgognePublicMapEmbed.vue'),
  meta: { public: true, title: '🗺️ 布根地產區地圖 · 侍酒師的筆記本' }
}
```

**沒有**把這條路由加進 `COURSE_ACCESS_RULES`,所以 `beforeEach` 守衛
不會套用任何訂閱等級限制;`meta: { public: true }` 沿用你的
`/reset-password` 路由已經在用的免登入寫法,不是新發明的機制。

**目前只公開 4 個產區的邊界**(白名單機制,寫在元件裡的 `PRESETS` 物件):
- `corton`:柯通丘紅白特級園
- `montrachet`:蒙哈榭跨村特級園群
- `chablis_gc`:夏布利七座特級園
- `vougeot`:Clos de Vougeot

之後要加新的深連結,在 `PRESETS` 裡加一筆設定即可,不用碰路由或其他
元件。**不會**自動把整個布根地資料庫都公開出去。

### wine_explorer_bot(Telegram bot)

`story_data.json` 裡 4 個章節的節點文字,連結從舊的 GitHub Pages Leaflet
版本,改成新的 Vue+Mapbox 免登入嵌入頁。內容本身沒有改。

舊的 `index.html`(Leaflet 版本)我**沒有刪**,先留著沒關係,等你確認新
版本正常運作之後,可以自己決定要不要從 repo 移除,或保留當備援。

## 已經跑過的驗證

- **實際執行了 `npm run build`**(不是只看語法),整個 bordeaux-map 專案
  build 成功,新元件 `BourgognePublicMapEmbed` 有被正確打包進
  `dist/assets/`,沒有任何 build 錯誤。
- `story_data.json` 跑過完整性掃描(章節連結、start_node、badge 依賴鏈),
  4 條連結文字修改後結構依然完整無誤。

**沒有測試過的部分**:沒有實際部署到 Vercel 上用瀏覽器打開這個頁面看
畫面,也沒有實際用你的 Mapbox token 測試地圖有沒有正確渲染出邊界。
建議部署後你自己點開連結看一下(至少測 `?map=corton` 這個),確認地圖
真的有秀出邊界、圖例文字正確、右下角有回到完整課程的引導連結。

## 怎麼套用

**bordeaux-map**:把這個資料夾裡的 `src/components/bourgogne/BourgognePublicMapEmbed.vue`
複製到你 repo 對應位置(新檔案),`src/router/index.js` 用這份蓋掉你的
(或手動把上面那段路由設定加進你現有的 router 檔案,取決於你原本
router 有沒有其他未同步的修改)。

**wine_explorer_bot**:`story_data.json` 蓋掉即可(先確認網域,見最上面
那段)。`bot.py` 這次沒有再改,不用動。

兩個 repo 都是 `git add -A` → `git commit` → `git push`(PowerShell 記得
分行下指令,不要用 `&&`)。bordeaux-map 如果是接 Vercel 自動部署,push
上去後應該會自動重新 build;wine_explorer_bot 一樣是 push 後 Railway
自動重新部署。
