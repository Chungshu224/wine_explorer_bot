import { createRouter, createWebHistory } from 'vue-router'
import { authState, authInitPromise, authActions } from '../stores/authStore.js'
import { getCourseAccess } from '../lib/purchaseService.js'

// ============================================================
//  訂閱層級功能對照表 (Tier Access Map)
// ============================================================
//  免費 (free)  — 只要註冊即可
//    ✅ 登入、設定
//    ✅ Level 1 課程（永久免費體驗）
//    ✅ 地圖探索 (限 Regional AOC + LeftBank-Medoc AOC 兩個群組)
//    ❌ Level 2~4 課程（需訂閱；例外由優惠碼發放的試用期）
//    ❌ 地圖進階圖層：等高線、地質土壤、氣候熱力
//    ❌ 地圖內「顯示知名酒莊」功能
//    ❌ 互動練習中心 (GameHub)
//    ❌ 品飲筆記本 (TastingNotebook)
//
//  初階付費 (basic) — 訂閱單一產區即完整解鎖該產區
//    ✅ Level 1~4 課程 (全部)
//    ✅ 探索地圖 (全部 AOC 群組)
//    ✅ 地圖進階圖層：等高線、地質土壤、氣候熱力
//    ✅ 地圖內「顯示知名酒莊」功能
//    ✅ 互動練習中心 (全部 4 種互動遊戲)
//    ✅ 品飲筆記本 (TastingNotebook)
//    ❌ 其他產區課程（需另外訂閱，或購買全球產區通行證）
//
//  進階付費 (premium) — 保留給未來多產區/加值方案使用，目前無獨立販售管道
// ============================================================

const routes = [
  // ─── 平台首頁（公開，無需登入）────────────────────────────────────────────
  {
    path: '/',
    name: 'PlatformHome',
    component: () => import('../components/PlatformHome.vue'),
    meta: { public: true }
  },

  // ─── 波爾多課程主頁（原 '/' Home）──────────────────────────────────────────
  {
    path: '/bordeaux',
    name: 'Home',
    component: () => import('../components/bordeaux/LevelSelection.vue'),
    meta: { requiresAuth: true, minimumTier: 'free', title: '波爾多 · 侍酒師的筆記本' }
  },

  // ─── 布根地課程 ─────────────────────────────────────────────────────────────
  {
    path: '/bourgogne',
    name: 'Bourgogne',
    component: () => import('../components/bourgogne/BourgognePage.vue'),
    meta: { requiresAuth: true, minimumTier: 'free', title: '🍇 布根地 · 侍酒師的筆記本' }
  },

  // ─── 布根地公開地圖嵌入頁(免登入,給外部深連結用,目前是 wine_explorer_bot
  //     這個 Telegram 遊戲的故事文字裡引用)────────────────────────────────────
  //     只公開白名單裡列出的產區邊界,不是完整付費地圖,詳見元件內註解。
  //     沒有加進 COURSE_ACCESS_RULES,所以下方 beforeEach 不會套用任何
  //     tier 限制;meta.public 沿用 /reset-password 已經在用的免登入寫法。
  {
    path: '/bourgogne/map-embed',
    name: 'BourgogneMapEmbed',
    component: () => import('../components/bourgogne/BourgognePublicMapEmbed.vue'),
    meta: { public: true, title: '🗺️ 布根地產區地圖 · 侍酒師的筆記本' }
  },

  // ─── 義大利課程 ─────────────────────────────────────────────────────────────
  {
    path: '/italy',
    name: 'Italy',
    component: () => import('../components/italy/ItalyPage.vue'),
    meta: { requiresAuth: true, minimumTier: 'free', title: '🇮🇹 義大利 · 侍酒師的筆記本' }
  },

  // ─── 西班牙探索地圖 ─────────────────────────────────────────────────────────
  {
    path: '/spain',
    name: 'Spain',
    component: () => import('../components/spain/SpainPage.vue'),
    meta: { requiresAuth: true, minimumTier: 'free', title: '🇪🇸 西班牙 · 侍酒師的筆記本' }
  },

  // ─── 德國探索地圖 ───────────────────────────────────────────────────────────
  {
    path: '/germany',
    name: 'Germany',
    component: () => import('../components/germany/GermanyPage.vue'),
    meta: { requiresAuth: true, minimumTier: 'free', title: '🇩🇪 德國 · 侍酒師的筆記本' }
  },

  // ─── 葡萄牙探索地圖 ─────────────────────────────────────────────────────────
  {
    path: '/portugal',
    name: 'Portugal',
    component: () => import('../components/portugal/PortugalPage.vue'),
    meta: { requiresAuth: true, minimumTier: 'free', title: '🇵🇹 葡萄牙 · 侍酒師的筆記本' }
  },

  // ─── 澳洲葡萄酒課程 ─────────────────────────────────────────────────────────
  {
    path: '/australia',
    name: 'Australia',
    component: () => import('../components/australia/AustraliaPage.vue'),
    meta: { requiresAuth: true, minimumTier: 'free', title: '🦘 澳洲 · 侍酒師的筆記本' }
  },

  // ─── 紐西蘭葡萄酒課程 ───────────────────────────────────────────────────────
  {
    path: '/newzealand',
    name: 'NewZealand',
    component: () => import('../components/newzealand/NewZealandPage.vue'),
    meta: { requiresAuth: true, minimumTier: 'free', title: '🥝 紐西蘭 · 侍酒師的筆記本' }
  },

  // ─── 阿爾薩斯葡萄酒課程 ─────────────────────────────────────────────────────
  {
    path: '/alsace',
    name: 'Alsace',
    component: () => import('../components/alsace/AlsacePage.vue'),
    meta: { requiresAuth: true, minimumTier: 'free', title: '🍇 阿爾薩斯 · 侍酒師的筆記本' }
  },

  // ─── 羅亞爾河谷探索地圖 ──────────────────────────────────────────────────────
  {
    path: '/loire',
    name: 'Loire',
    component: () => import('../components/loire/LoirePage.vue'),
    meta: { requiresAuth: true, minimumTier: 'free', title: '� 羅亞爾河谷 · 侍酒師的筆記本' }
  },
  {
    path: '/loire/course',
    name: 'LoireCourse',
    component: () => import('../components/loire/LoireLearningSystem.vue'),
    meta: { requiresAuth: true, minimumTier: 'free', title: '🌊 羅亞爾河谷葡萄酒課程 · 侍酒師的筆記本' }
  },

  // ─── 匈牙利葡萄酒產區地圖 ────────────────────────────────────────────────────
  {
    path: '/hungary',
    name: 'Hungary',
    component: () => import('../components/hungary/HungaryPage.vue'),
    meta: { requiresAuth: true, minimumTier: 'free', title: '🇭🇺 匈牙利 · 侍酒師的筆記本' }
  },
  {
    path: '/hungary/course',
    redirect: '/hungary'
  },

  // ─── 加州 AVA 探索地圖 ───────────────────────────────────────────────────────
  {
    path: '/california',
    name: 'California',
    component: () => import('../components/california/CaliforniaPage.vue'),
    meta: { requiresAuth: true, minimumTier: 'free', title: '加州葡萄酒產區 · 侍酒師的筆記本' }
  },
  // ─── 加州葡萄酒課程 ──────────────────────────────────────────────────────────
  {
    path: '/california/course',
    name: 'CaliforniaCourse',
    component: () => import('../components/california/CaliforniaLearningSystem.vue'),
    meta: { requiresAuth: true, minimumTier: 'free', title: '加州葡萄酒課程 · 侍酒師的筆記本' }
  },

  // ─── 定價方案頁 ──────────────────────────────────────────────────────────────
  {
    path: '/pricing',
    name: 'Pricing',
    component: () => import('../components/PricingPage.vue'),
  },

  {
    path: '/checkout/cart',
    name: 'CheckoutCart',
    component: () => import('../components/CheckoutCartPage.vue'),
    meta: { requiresAuth: true, minimumTier: 'free' }
  },

  // ─── 使用者儀表板 ───────────────────────────────────────────────────────────
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../components/UserDashboard.vue'),
    meta: { requiresAuth: true, minimumTier: 'free' }
  },

  // ─── 付款結果頁（Stripe success_url 跳回）────────────────────────────────
  {
    path: '/payment/result',
    name: 'PaymentResult',
    component: () => import('../components/PaymentResult.vue'),
    meta: { requiresAuth: true, minimumTier: 'free' }
  },

  {
    path: '/login',
    name: 'Login',
    component: () => import('../components/Login.vue'),
    meta: { public: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../components/Register.vue'),
    meta: { public: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../components/UserSettings.vue'),
    meta: { requiresAuth: true, minimumTier: 'free' }
  },
  {
    //  Level 1 免費，Level 2~4 需 basic 以上（見下方 beforeEach 的 Learning 特判，依 query.level 動態判斷）
    path: '/learning',
    name: 'Learning',
    component: () => import('../components/bordeaux/LearningSystem.vue'),
    meta: { requiresAuth: true, minimumTier: 'free', title: '📖 波爾多課程 · 侍酒師的筆記本' }
  },
  {
    // 地圖探索：free 以上均可進入 (AOC 群組與圖層由元件內部依 Tier 控管)
    path: '/explore',
    name: 'Explore',
    component: () => import('../components/bordeaux/BordeauxMap.vue'),
    meta: { requiresAuth: true, minimumTier: 'free', title: '🗺️ 波爾多地圖 · 侍酒師的筆記本' }
  },
  {
    // 互動練習中心：basic 以上
    path: '/gamehub',
    name: 'GameHub',
    component: () => import('../components/bordeaux/GameHubPage.vue'),
    meta: { requiresAuth: true, minimumTier: 'basic', title: '🎮 互動練習 · 侍酒師的筆記本' }
  },
  {
    // 品飲筆記本：basic 以上
    path: '/notebook',
    name: 'Notebook',
    component: () => import('../components/bordeaux/TastingNotebookPage.vue'),
    meta: { requiresAuth: true, minimumTier: 'basic', title: '📝 品飲筆記 · 侍酒師的筆記本' }
  },
  {
    path: '/upgrade',
    name: 'Upgrade',
    component: () => import('../components/bordeaux/LevelSelection.vue'),
    meta: { public: true }
  },

  // ─── 學員討論區（需登入才能瀏覽與發言）────────────────────────────────────────
  {
    path: '/forum',
    name: 'Forum',
    component: () => import('../components/ForumPage.vue'),
    meta: { requiresAuth: true, minimumTier: 'free' }
  },
  {
    path: '/forum/:id',
    name: 'ForumPost',
    component: () => import('../components/ForumPostDetail.vue'),
    meta: { requiresAuth: true, minimumTier: 'free' }
  },

  // ─── 互動特化 Slide 索引頁 ────────────────────────────────────────────────
  {
    path: '/slides-index',
    name: 'SpecializedSlideIndex',
    component: () => import('../components/SpecializedSlideIndex.vue'),
    meta: { requiresAuth: true, minimumTier: 'free', title: '🎛️ 互動特化 Slide 全覽 · 侍酒師的筆記本' }
  },

  // ─── 管理員後台（需登入且為 admin 角色）────────────────────────────────────
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('../components/AdminDashboard.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },

  // ─── 密碼重設（Email 連結回調）─────────────────────────────────────────────
  {
    path: '/reset-password',
    name: 'ResetPassword',
    component: () => import('../components/ResetPassword.vue'),
    meta: { public: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const COURSE_ACCESS_RULES = {
  Home: { courseId: 'bordeaux', minimumTier: 'free' },
  Bourgogne: { courseId: 'bourgogne', minimumTier: 'basic' },
  Italy: { courseId: 'italy', minimumTier: 'basic' },
  Spain: { courseId: 'spain', minimumTier: 'free' },
  Germany: { courseId: 'germany', minimumTier: 'free' },
  Portugal: { courseId: 'portugal', minimumTier: 'free' },
  Australia: { courseId: 'australia', minimumTier: 'free' },
  NewZealand: { courseId: 'newzealand', minimumTier: 'free' },
  Alsace: { courseId: 'alsace', minimumTier: 'basic' },
  Loire: { courseId: 'loire', minimumTier: 'free' },
  LoireCourse: { courseId: 'loire', minimumTier: 'basic' },
  Hungary: { courseId: 'hungary', minimumTier: 'free' },
  California: { courseId: 'california', minimumTier: 'free' },
  CaliforniaCourse: { courseId: 'california', minimumTier: 'basic' },
  Learning: { courseId: 'bordeaux', minimumTier: 'free' },
  Explore: { courseId: 'bordeaux', minimumTier: 'free' },
  GameHub: { courseId: 'bordeaux', minimumTier: 'basic' },
  Notebook: { courseId: 'bordeaux', minimumTier: 'basic' },
  SpecializedSlideIndex: { courseId: 'bordeaux', minimumTier: 'free' }
}

// 訂閱等級的數值權重
export const TIER_WEIGHT = {
  free: 0,
  basic: 1,
  premium: 2
}

// 各等級的升級提示文字
const UPGRADE_MESSAGES = {
  basic: '📚 此功能需要「初階付費」方案\n\nLevel 2~4 課程 + 地圖探索 + 互動練習，立即升級解鎖！',
  premium: '⭐ 此功能需要「進階付費」方案\n\n進階地圖圖層（等高線/地質/氣候）+ 酒莊標記 + 品飲筆記本，解鎖全部學習工具！'
}

router.beforeEach(async (to, from, next) => {
  // 等待 auth 初始化完成 (避免 F5 重整時被誤判為未登入)
  if (authState.loading) {
    await authInitPromise
  }

  const user = authState.user

  // 管理員信箱自動賦予 premium；否則讀 user_metadata
  const isAdmin = authActions.isAdmin?.() || false
  const userTier = authActions.getEffectiveTier()
  const routeRule = COURSE_ACCESS_RULES[to.name]

  // 1. 檢查是否需要登入
  if (to.meta.requiresAuth && !user) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }

  // 1b. 管理員專屬路由防護
  if (to.meta.requiresAdmin && !isAdmin) {
    console.warn('[權限阻擋] 此路由僅限管理員')
    return next({ name: 'Home' })
  }

  // 2. 課程路由的動態 Tier 判斷
  let requiredTier = routeRule?.minimumTier ?? to.meta.minimumTier
  let accessTier = userTier

  if (routeRule?.courseId && !isAdmin) {
    accessTier = await getCourseAccess(user.id, routeRule.courseId)
  }

  if (to.name === 'Learning') {
    // Level 1 永久免費；Level 2 以上需 basic 訂閱
    const requestedLevel = parseInt(to.query.level) || 1
    requiredTier = requestedLevel === 1 ? 'free' : 'basic'
  }

  // 3. 比對 Tier 權重
  if (requiredTier) {
    const requiredWeight = TIER_WEIGHT[requiredTier]
    const currentWeight = TIER_WEIGHT[accessTier]

    if (currentWeight < requiredWeight) {
      console.warn(`[權限阻擋] 此路由需要 "${requiredTier}"，目前為 "${accessTier}"`)
      const msg = UPGRADE_MESSAGES[requiredTier] || '🔒 此功能為付費訂閱專屬，請升級您的方案解鎖！'
      alert(msg)
      // 退回前一頁；若無前一頁則回首頁
      return next(from.name ? false : { name: 'Home' })
    }
  }

  // 4. 放行
  next()
})

// ── 路由切換後更新瀏覽器標題 ─────────────────────────────────────────────────
const LEVEL_TITLES = {
  1: '📖 L1 波爾多入門',
  2: '📗 L2 波爾多進階',
  3: '📘 L3 波爾多深探',
  4: '📙 L4 波爾多精通',
}

router.afterEach((to) => {
  let title = to.meta.title

  // /learning 依 level query 動態標題
  if (to.name === 'Learning') {
    const level = parseInt(to.query.level) || 1
    title = `${LEVEL_TITLES[level] || `L${level} 課程`} · 侍酒師的筆記本`
  }

  document.title = title || '侍酒師的筆記本 · The Sommelier\'s Notebook'
})

export default router
