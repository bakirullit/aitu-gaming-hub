<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from './services/api'

const router = useRouter()

onMounted(async () => {
  // 1. Initialize Telegram WebApp SDK if available
  const twa = window.Telegram?.WebApp
  if (twa) {
    try {
      twa.ready()
      twa.expand()
      if (typeof twa.disableVerticalSwipes === 'function') {
        twa.disableVerticalSwipes()
      }
      if (typeof twa.setHeaderColor === 'function') twa.setHeaderColor('#0a0d14')
      if (typeof twa.setBackgroundColor === 'function') twa.setBackgroundColor('#0a0d14')
    } catch (e) {
      console.warn('Telegram WebApp setup error:', e)
    }

    // 2. Seamless Telegram Web App login if initData is present
    if (twa.initData && twa.initData.trim() !== '') {
      try {
        const res = await authApi.loginTelegramWebApp(twa.initData)
        if (res.data && res.data.access_token) {
          localStorage.setItem('access_token', res.data.access_token)
          localStorage.setItem('user', JSON.stringify(res.data.user))
          window.dispatchEvent(new Event('auth-changed'))

          // If currently on login page, redirect based on admin status
          const currentPath = window.location.pathname
          if (currentPath === '/login') {
            const isAdmin = res.data.is_admin || res.data.user?.is_admin
            if (isAdmin) {
              router.push('/admin')
            } else {
              router.push('/tournaments')
            }
          }
        }
      } catch (err) {
        console.warn('Seamless WebApp authentication not applicable or failed:', err)
      }
    }
  }
})
</script>
