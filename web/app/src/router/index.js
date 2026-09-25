import { createRouter, createWebHistory } from 'vue-router'

import Admin from '../views/Admin.vue'
import Disciplines from '../views/Disciplines.vue'
import Login from '../views/Login.vue'
import Tournaments from '../views/Tournaments.vue'

const routes = [
  { path: '/', redirect: '/tournaments' },
  { path: '/tournaments', component: Tournaments },
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
]


const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const isAuthenticated = !!localStorage.getItem('access_token')
  
  if (to.meta.requiresAuth && !isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && isAuthenticated) {
    next('/admin')
  } else {
    next()
  }
})

export default router