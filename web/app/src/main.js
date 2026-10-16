import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'

// Guard against native Qt WebEngine infinite window expansion / crash bug in Telegram Desktop
if (typeof window !== 'undefined') {
  window.alert = function (msg) {
    if (window.Telegram?.WebApp?.showAlert) {
      window.Telegram.WebApp.showAlert(String(msg ?? ''))
    } else {
      console.warn('[App Alert]:', msg)
    }
  }

  window.confirm = function (msg) {
    console.warn('[App Confirm intercepted to prevent Qt WebEngine crash]:', msg)
    return true
  }
}

createApp(App)
  .use(router)
  .mount('#app')