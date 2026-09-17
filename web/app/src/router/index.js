import { createRouter, createWebHistory } from 'vue-router'

import Admin from '../views/Admin.vue'
import Login from '../views/Login.vue'

const routes = [
  { path: '/', redirect: '/admin' },
  { path: '/login', component: Login },
  { 
    path: '/admin', 
    component: Admin,
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