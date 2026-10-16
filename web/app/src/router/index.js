import { createRouter, createWebHistory } from 'vue-router'
import { authApi } from '../services/api'

import Admin from '../views/Admin.vue'
import Chats from '../views/Chats.vue'
import Disciplines from '../views/Disciplines.vue'
import Login from '../views/Login.vue'
import Tournaments from '../views/Tournaments.vue'
import TournamentHub from '../views/TournamentHub.vue'
import Lootbox from '../views/Lootbox.vue'

const routes = [
  { path: '/', redirect: '/tournaments' },
  { path: '/tournaments', component: Tournaments },
  { path: '/tournaments/cs2-2v2', component: TournamentHub },
  { path: '/tournaments/open-sunday', component: TournamentHub },
  { path: '/tournaments/open-sunday-cs2', component: TournamentHub },
  { path: '/tournaments/hub', component: TournamentHub },
  { path: '/lootbox', component: Lootbox },
  { path: '/admin/tournaments', component: Tournaments },
  { path: '/login', component: Login },
  { 
    path: '/admin', 
    component: Admin,
    meta: { requiresAuth: true }
  },
  { 
    path: '/admin/disciplines', 
    component: Disciplines,
    meta: { requiresAuth: true }
  },
  { 
    path: '/admin/chats', 
    component: Chats,
    meta: { requiresAuth: true }
  },
]


const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, from, next) => {
  let isAuthenticated = !!localStorage.getItem('access_token')

  // If not authenticated yet but inside Telegram Web App, try seamless authentication
  if (!isAuthenticated && window.Telegram?.WebApp?.initData) {
    try {
      const res = await authApi.loginTelegramWebApp(window.Telegram.WebApp.initData)
      if (res.data?.access_token) {
        localStorage.setItem('access_token', res.data.access_token)
        localStorage.setItem('user', JSON.stringify(res.data.user))
        window.dispatchEvent(new Event('auth-changed'))
        isAuthenticated = true
      }
    } catch (e) {
      console.warn('Seamless login in router guard failed:', e)
    }
  }

  if (to.meta.requiresAuth && !isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && isAuthenticated) {
    next('/admin')
  } else {
    next()
  }
})


export default router