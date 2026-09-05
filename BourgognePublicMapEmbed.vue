<template>
  <div class="public-map-embed">
    <div id="title-bar">{{ titleText }}</div>
    <div ref="mapContainer" id="map"></div>
    <div id="legend" v-if="legendItems.length">
      <div class="legend-item" v-for="item in legendItems" :key="item.label">
        <span class="legend-swatch" :style="{ background: item.color }"></span>
        <span>{{ item.label }}</span>
      </div>
    </div>
    <div id="error-box" v-if="errorMsg">{{ errorMsg }}</div>
    <a id="footer-credit" href="/bourgogne" target="_blank" rel="noopener">
      🍇 侍酒師的筆記本 · 完整布根地課程與地圖 →
    </a>
  </div>
</template>

<script setup>
/**
 * 布根地公開地圖嵌入頁 —— 專給外部深連結用(目前是 wine_explorer_bot 這個
 * Telegram 互動小說遊戲),路由設定是 meta: { public: true },不用登入、
 * 不吃訂閱等級限制。
 *
 * 跟 BourgogneMapSection.vue(完整付費地圖)刻意分開成獨立元件,原因:
 * 1. 付費地圖的 props/state 是設計給站內導覽用的(regionConfig 由父層
 *    BourgognePage.vue 控制),不是為了被外部連結直接命中而設計。
 *    硬把它掛在免登入路由上,等於把整個付費地圖的操作介面暴露出去,
 *    不是原本想開的「一扇小門」。
 * 2. 這裡的需求很單純:網址帶 ?map=xxx,就秀出對應的產區邊界,加一個
 *    「回到完整課程」的引導連結。跟完整地圖比,這是很小的獨立需求,
 *    獨立元件比較好維護,也不會被完整地圖之後的改動意外影響。
 *
 * 只有下面 PRESETS 白名單裡列出的產區會被公開,新增其他深連結時,
 * 在這裡加一筆設定即可,不用改路由或其他元件。
 */
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import {
  getMapboxToken,
  shouldUseMapbox,
  getMapboxStyleUrl,
  getOSMStyle
} from '@/utils/getMapboxToken'

const route = useRoute()
const mapContainer = ref(null)
const errorMsg = ref('')
const legendItems = ref([])
const titleText = ref('載入中…')

// GeoJSON 資料就放在這個 Vue 專案自己的 public/ 資料夾裡(跟付費地圖共用
// 同一份檔案),用相對路徑讀取即可,不需要像舊版 wine_explorer_bot 的
// Leaflet 頁面那樣去 GitHub raw content 抓資料。
const GEOJSON_BASE = '/bourgogne/geojson/'

// 白名單:只有這裡列出的 key 可以被公開存取。要新增深連結時在這裡加一筆。
const PRESETS = {
  corton: {
    title: '柯通丘:紅白特級園並存的邊界',
    layers: [
      {
        label: 'Corton(紅酒特級園)',
        color: '#e24b4a',
        files: [
          'Cote-de-Beaune/03Aloxe-Corton/Grand Cru/AOC Corton Grand Cru(Aloxe).geojson',
          'Cote-de-Beaune/01Pernand-Vergelesses/Grand Cru/AOC Corton Grand Cru(Pernand).geojson',
          'Cote-de-Beaune/02Ladoix/Grand Cru/AOC Corton Grand Cru(Ladoix).geojson',
        ],
      },
      {
        label: 'Corton-Charlemagne(白酒特級園)',
        color: '#1d9e75',
        files: [
          'Cote-de-Beaune/03Aloxe-Corton/Grand Cru/AOC Corton-Charlemagne Grand Cru(Aloxe).geojson',
          'Cote-de-Beaune/01Pernand-Vergelesses/Grand Cru/AOC Corton-Charlemagne Grand Cru(Pernand).geojson',
          'Cote-de-Beaune/02Ladoix/Grand Cru/AOC Corton-Charlemagne Grand Cru(Ladoix).geojson',
        ],
      },
      {
        label: 'Charlemagne(白酒特級園)',
        color: '#378add',
        files: [
          'Cote-de-Beaune/03Aloxe-Corton/Grand Cru/AOC Charlemagne Grand Cru (Aloxe).geojson',
          'Cote-de-Beaune/01Pernand-Vergelesses/Grand Cru/AOC Charlemagne Grand Cru(Pernand).geojson',
        ],
      },
    ],
  },
  montrachet: {
    title: '蒙哈榭:橫跨普里尼與夏山兩村的特級園',
    layers: [
      {
        label: 'Montrachet(跨兩村)',
        color: '#e2b33d',
        files: [
          'Cote-de-Beaune/14Puligny-Montrachet/Grand Cru/AOC Montrachet Grand Cru(Puligny).geojson',
          'Cote-de-Beaune/15Chassagne-Montrachet/Grand Cru/AOC Montrachet Grand Cru(Chassagne).geojson',
        ],
      },
      {
        label: 'Chevalier-Montrachet(普里尼側)',
        color: '#378add',
        files: [
          'Cote-de-Beaune/14Puligny-Montrachet/Grand Cru/AOC Chevalier-Montrachet Grand Cru.geojson',
        ],
      },
      {
        label: 'Bâtard-Montrachet(跨兩村)',
        color: '#1d9e75',
        files: [
          'Cote-de-Beaune/14Puligny-Montrachet/Grand Cru/AOC Bâtard-Montrachet Grand Cru(Puligny).geojson',
          'Cote-de-Beaune/15Chassagne-Montrachet/Grand Cru/AOC Bâtard-Montrachet Grand Cru(Chassagne).geojson',
        ],
      },
      {
        label: 'Bienvenues- / Criots-Bâtard(附屬小園)',
        color: '#a35fd1',
        files: [
          'Cote-de-Beaune/14Puligny-Montrachet/Grand Cru/AOC Bienvenues-Bâtard-Montrachet Grand Cru .geojson',
          'Cote-de-Beaune/15Chassagne-Montrachet/Grand Cru/AOC Criots-Bâtard-Montrachet Grand Cru.geojson',
        ],
      },
    ],
  },
  chablis_gc: {
    title: '夏布利特級園:一座產區,七個名字',
    layers: [
      { label: 'Blanchot', color: '#e24b4a', files: ['Chablis/Chablis Grand Cru/AOC Chablis Grand Cru Blanchot.geojson'] },
      { label: 'Bougros', color: '#e2914d', files: ['Chablis/Chablis Grand Cru/AOC Chablis Grand Cru Bougros.geojson'] },
      { label: 'Preuses', color: '#e2c23d', files: ['Chablis/Chablis Grand Cru/AOC Chablis Grand Cru Preuses.geojson'] },
      { label: 'Vaudésir', color: '#8fc93a', files: ['Chablis/Chablis Grand Cru/AOC Chablis Grand Cru Vaudésir.geojson'] },
      { label: 'Grenouilles', color: '#1d9e75', files: ['Chablis/Chablis Grand Cru/AOC Chablis Grand Cru Grenouilles.geojson'] },
      { label: 'Valmur', color: '#378add', files: ['Chablis/Chablis Grand Cru/AOC Chablis Grand Cru Valmur.geojson'] },
      { label: 'Les Clos(面積最大)', color: '#a35fd1', files: ['Chablis/Chablis Grand Cru/AOC Chablis Grand Cru Les Clos.geojson'] },
    ],
  },
  vougeot: {
    title: 'Clos de Vougeot:八十幾位地主共有的圍牆園',
    layers: [
      {
        label: 'Clos de Vougeot(特級園)',
        color: '#e24b4a',
        files: [
          'Cote-de-Nuits/09Vougeot/Grand Crus/AOC Clos de Vougeot ou Clos Vougeot Grand Cru.geojson',
        ],
      },
      {
        label: 'Vougeot 一級園',
        color: '#378add',
        files: [
          'Cote-de-Nuits/09Vougeot/1er Crus/AOC Vougeot 1er Cru.geojson',
        ],
      },
      {
        label: 'Vougeot 村莊級',
        color: '#8fc93a',
        files: [
          'Cote-de-Nuits/09Vougeot/AOC Vougeot.geojson',
        ],
      },
    ],
  },
}

let map = null

async function fetchGeojson(relativePath) {
  const url = GEOJSON_BASE + relativePath.split('/').map(encodeURIComponent).join('/')
  const resp = await fetch(url)
  if (!resp.ok) {
    throw new Error(`讀取失敗(${resp.status}):${relativePath}`)
  }
  return resp.json()
}

onMounted(async () => {
  const presetKey = String(route.query.map || '')
  const preset = PRESETS[presetKey]

  if (!preset) {
    titleText.value = '找不到這個地圖設定'
    errorMsg.value = `網址參數 map=${presetKey || '(空白)'} 沒有對應的公開設定,請確認連結是否正確。`
    return
  }

  titleText.value = preset.title

  const MAPBOX_TOKEN = getMapboxToken()
  const useMapbox = shouldUseMapbox(MAPBOX_TOKEN)
  mapboxgl.accessToken = useMapbox ? MAPBOX_TOKEN : 'pk.notarealtoken'
  const style = useMapbox ? getMapboxStyleUrl(MAPBOX_TOKEN, 'satellite-streets-v12') : getOSMStyle()
  if (!useMapbox) {
    console.warn('[BourgognePublicMapEmbed] 未偵測到 Mapbox token,改用 OSM 背景。')
  }

  map = new mapboxgl.Map({
    container: mapContainer.value,
    style,
    center: [4.85, 47.05], // 布根地大致中心,載入完 geojson 後會 fitBounds 覆蓋掉
    zoom: 12,
  })
  map.addControl(new mapboxgl.NavigationControl(), 'top-right')

  map.on('load', async () => {
    let bounds = null

    for (const [layerIdx, layer] of preset.layers.entries()) {
      let mergedFeatures = []
      for (const file of layer.files) {
        try {
          const geo = await fetchGeojson(file)
          mergedFeatures = mergedFeatures.concat(geo.features || [])
        } catch (err) {
          console.error(err)
          errorMsg.value = err.message
        }
      }
      if (mergedFeatures.length === 0) continue

      const sourceId = `preset-layer-${layerIdx}`
      map.addSource(sourceId, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: mergedFeatures },
      })
      map.addLayer({
        id: `${sourceId}-fill`,
        type: 'fill',
        source: sourceId,
        paint: { 'fill-color': layer.color, 'fill-opacity': 0.45 },
      })
      map.addLayer({
        id: `${sourceId}-line`,
        type: 'line',
        source: sourceId,
        paint: { 'line-color': layer.color, 'line-width': 2 },
      })

      legendItems.value.push({ label: layer.label, color: layer.color })

      for (const feature of mergedFeatures) {
        const featureBounds = getFeatureBounds(feature)
        if (!featureBounds) continue
        bounds = bounds ? extendBounds(bounds, featureBounds) : featureBounds
      }
    }

    if (bounds) {
      map.fitBounds(bounds, { padding: 40, duration: 0 })
    }
  })
})

// --- 簡易的 GeoJSON bounds 計算(Mapbox GL 沒有內建 Leaflet 那種
// L.geoJSON().getBounds(),自己掃座標算最小/最大範圍) ---
function getFeatureBounds(feature) {
  let minLng = Infinity, minLat = Infinity, maxLng = -Infinity, maxLat = -Infinity
  const visit = (coords, depth) => {
    if (depth === 0) {
      const [lng, lat] = coords
      minLng = Math.min(minLng, lng); maxLng = Math.max(maxLng, lng)
      minLat = Math.min(minLat, lat); maxLat = Math.max(maxLat, lat)
    } else {
      coords.forEach((c) => visit(c, depth - 1))
    }
  }
  const geom = feature.geometry
  if (!geom) return null
  const depthByType = { Point: 0, MultiPoint: 1, LineString: 1, MultiLineString: 2, Polygon: 2, MultiPolygon: 3 }
  const depth = depthByType[geom.type]
  if (depth === undefined) return null
  visit(geom.coordinates, depth)
  if (!isFinite(minLng)) return null
  return [[minLng, minLat], [maxLng, maxLat]]
}

function extendBounds(a, b) {
  return [
    [Math.min(a[0][0], b[0][0]), Math.min(a[0][1], b[0][1])],
    [Math.max(a[1][0], b[1][0]), Math.max(a[1][1], b[1][1])],
  ]
}
</script>

<style scoped>
.public-map-embed { position: fixed; inset: 0; font-family: -apple-system, "PingFang TC", "Microsoft JhengHei", sans-serif; }
#map { position: absolute; inset: 0; }
#title-bar {
  position: absolute; top: 0; left: 0; right: 0; z-index: 10;
  background: rgba(20, 24, 20, 0.82); color: #fff;
  padding: 10px 14px; font-size: 15px; font-weight: 600;
  box-shadow: 0 2px 6px rgba(0,0,0,0.3);
}
#legend {
  position: absolute; bottom: 44px; left: 10px; z-index: 10;
  background: rgba(20, 24, 20, 0.82); color: #fff;
  padding: 10px 14px; border-radius: 8px; font-size: 13px; line-height: 1.8;
}
.legend-item { display: flex; align-items: center; gap: 8px; }
.legend-swatch { width: 14px; height: 14px; border-radius: 3px; flex-shrink: 0; }
#error-box {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
  z-index: 20; background: #fff; padding: 16px 20px; border-radius: 8px;
  max-width: 80%; text-align: center; font-size: 14px;
}
#footer-credit {
  position: absolute; bottom: 0; left: 0; right: 0; z-index: 10;
  background: rgba(114, 47, 55, 0.92); color: #fff; text-decoration: none;
  text-align: center; padding: 8px 10px; font-size: 13px; font-weight: 500;
}
#footer-credit:hover { background: rgba(114, 47, 55, 1); }
</style>
