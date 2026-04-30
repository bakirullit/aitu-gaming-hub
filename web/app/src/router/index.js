import { createRouter, createWebHistory } from 'vue-router'

import Landing from '../views/Landing.vue'
import Admin from '../views/Admin.vue'

const routes = [
  { path: '/', component: Landing },
  { path: '/admin', component: Admin },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})