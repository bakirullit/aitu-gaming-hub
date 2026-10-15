<template>
  <div class="login-container">
    <div class="login-box glass-panel">
      <!-- Back link and Brand -->
      <div class="login-header">
        <router-link to="/tournaments" class="back-link">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
            <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/>
          </svg>
          <span>Турниры & Hub</span>
        </router-link>
        <div class="brand">
          <img src="/logo.png" alt="AITU Gaming" class="brand-logo-login" />
          <div class="brand-text">
            <h2>AITU Gaming Hub</h2>
            <span class="badge-role">Admin / Staff Access</span>
          </div>
        </div>
        <p class="subtitle">Авторизуйтесь через ваш корпоративный Telegram-аккаунт.</p>
      </div>

      <!-- Telegram Web App Auto-Authenticating State -->
      <div v-if="isTwaAuthenticating" class="twa-auth-box">
        <div class="twa-icon-glow">
          <svg viewBox="0 0 24 24" width="36" height="36" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.75-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
          </svg>
        </div>
        <p class="twa-text">Бесшовный вход через Telegram Web App...</p>
        <div class="minimal-spinner"></div>
      </div>

      <!-- Telegram Web App Non-Admin Notification -->
      <div v-else-if="twaNonAdminUser" class="step">
        <div class="twa-notice-box">
          <span class="user-greeting">👋 Привет, {{ twaNonAdminUser.first_name || 'Игрок' }}!</span>
          <p class="notice-desc">Вы успешно авторизованы через Telegram Mini App, однако у вашей учетной записи нет роли администратора.</p>
          <div class="user-pill mono">@{{ twaNonAdminUser.username || twaNonAdminUser.telegram_id }}</div>
        </div>
        <router-link to="/tournaments" class="btn-submit text-center">
          Перейти к Турнирам
        </router-link>
        <button @click="resetToManualLogin" class="btn-resend">
          Войти под другим администратором
        </button>
      </div>

      <!-- Step 1: Request Code -->
      <div v-else-if="!otpSent" class="step">
        <!-- Quick button if inside Telegram Web App -->
        <button 
          v-if="hasTwaData" 
          @click="attemptTwaLogin" 
          :disabled="loading" 
          class="btn-twa"
        >
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.75-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
          </svg>
          <span>Войти в 1 клик через Telegram</span>
        </button>

        <div v-if="hasTwaData" class="divider">
          <span>или по коду</span>
        </div>

        <div class="input-wrap">
          <label>Telegram ID или @username</label>
          <input 
            v-model="identifier" 
            type="text" 
            placeholder="@username или 123456789" 
            @keyup.enter="requestOtp"
            class="minimal-input"
            autocomplete="username"
          />
        </div>
        <button @click="requestOtp" :disabled="loading || !identifier.trim()" class="btn-submit">
          {{ loading ? 'Отправка...' : 'Получить код в Telegram' }}
        </button>
        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
      </div>

      <!-- Step 2: Enter 6-digit Code -->
      <div v-else class="step">
        <div class="input-wrap">
          <label>6-значный проверочный код</label>
          <input 
            v-model="code" 
            type="text" 
            placeholder="000000" 
            maxlength="6"
            inputmode="numeric"
            pattern="[0-9]*"
            @keyup.enter="verifyOtp"
            class="minimal-input code-input"
            autocomplete="one-time-code"
          />
        </div>
        <button @click="verifyOtp" :disabled="loading || code.length !== 6" class="btn-submit">
          {{ loading ? 'Проверка...' : 'Подтвердить и войти' }}
        </button>
        
        <p class="cooldown-text" v-if="cooldown > 0">Повторный запрос через {{ cooldown }}с</p>
        <button v-else @click="requestOtp" class="btn-resend">Запросить новый код</button>
        
        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '../services/api'

const router = useRouter()

const identifier = ref('')
const code = ref('')
const otpSent = ref(false)
const loading = ref(false)
const errorMsg = ref('')
const cooldown = ref(0)
const isTwaAuthenticating = ref(false)
const twaNonAdminUser = ref(null)
const hasTwaData = ref(false)

let timer = null

const startCooldown = () => {
  cooldown.value = 60
  clearInterval(timer)
  timer = setInterval(() => {
    cooldown.value--
    if (cooldown.value <= 0) clearInterval(timer)
  }, 1000)
}

const telegramId = ref(null)

const attemptTwaLogin = async () => {
  const twa = window.Telegram?.WebApp
  if (!twa?.initData) return

  errorMsg.value = ''
  isTwaAuthenticating.value = true

  try {
    const res = await authApi.loginTelegramWebApp(twa.initData)
    if (res.data?.access_token) {
      localStorage.setItem('access_token', res.data.access_token)
      localStorage.setItem('user', JSON.stringify(res.data.user))
      window.dispatchEvent(new Event('auth-changed'))

      const isAdmin = res.data.is_admin || res.data.user?.is_admin
      if (isAdmin) {
        router.push('/admin')
      } else {
        twaNonAdminUser.value = res.data.user
      }
    }
  } catch (err) {
    console.warn('TWA login error:', err)
    errorMsg.value = err.response?.data?.detail || 'Не удалось выполнить автоматический вход через Telegram'
  } finally {
    isTwaAuthenticating.value = false
  }
}

const resetToManualLogin = () => {
  twaNonAdminUser.value = null
  otpSent.value = false
  code.value = ''
}

onMounted(() => {
  const twa = window.Telegram?.WebApp
  if (twa?.initData && twa.initData.trim() !== '') {
    hasTwaData.value = true
    attemptTwaLogin()
  }
})

const requestOtp = async () => {
  if (!identifier.value) return
  errorMsg.value = ''
  loading.value = true
  
  try {
    const res = await authApi.requestOtp(identifier.value)
    telegramId.value = res.data.telegram_id
    otpSent.value = true
    startCooldown()
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'Не удалось отправить код в Telegram'
  } finally {
    loading.value = false
  }
}

const verifyOtp = async () => {
  if (code.value.length !== 6 || !telegramId.value) return
  errorMsg.value = ''
  loading.value = true
  
  try {
    const res = await authApi.verifyOtp(telegramId.value, code.value)
    localStorage.setItem('access_token', res.data.access_token)
    localStorage.setItem('user', JSON.stringify(res.data.user))
    window.dispatchEvent(new Event('auth-changed'))
    router.push('/admin')
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'Неверный или устаревший код'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  min-height: 100dvh;
  background-color: var(--bg-color, #090a0f);
  padding: 1.25rem;
  padding-top: max(1.5rem, env(safe-area-inset-top));
  padding-bottom: max(1.5rem, env(safe-area-inset-bottom));
}

.login-box {
  width: 100%;
  max-width: 400px;
  background: var(--surface-bg, #0f1117);
  border: 1px solid var(--surface-border, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-lg, 14px);
  padding: 2rem;
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.45);
}

.login-header {
  margin-bottom: 1.75rem;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.84rem;
  color: var(--text-muted, #64748b);
  margin-bottom: 1.25rem;
  transition: color 0.15s;
}

.back-link:hover {
  color: #fff;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  margin-bottom: 0.5rem;
}

.brand-logo-login {
  height: 40px;
  width: 40px;
  object-fit: contain;
  display: block;
}

.brand-text h2 {
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: -0.3px;
  color: #fff;
}

.badge-role {
  display: inline-block;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
  color: var(--accent);
}

.subtitle {
  font-size: 0.86rem;
  color: var(--text-secondary, #94a3b8);
  line-height: 1.4;
  margin-top: 0.35rem;
}

.step {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Telegram Web App Specific Elements */
.btn-twa {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  width: 100%;
  padding: 0.8rem;
  background: #2aabee;
  color: #fff;
  border-radius: var(--radius-sm, 6px);
  font-size: 0.92rem;
  font-weight: 600;
  transition: all 0.15s;
  cursor: pointer;
}

.btn-twa:hover {
  background: #229ed9;
  box-shadow: 0 0 16px rgba(42, 171, 238, 0.4);
}

.divider {
  display: flex;
  align-items: center;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.78rem;
  margin: 0.15rem 0;
}

.divider::before, .divider::after {
  content: '';
  flex: 1;
  border-bottom: 1px solid var(--surface-border);
}

.divider span {
  padding: 0 0.75rem;
}

.twa-auth-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem 1rem;
  gap: 1rem;
  text-align: center;
}

.twa-icon-glow {
  color: #2aabee;
  animation: pulse 2s infinite ease-in-out;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 0.9; }
  50% { transform: scale(1.1); opacity: 1; }
}

.twa-text {
  font-size: 0.92rem;
  color: var(--text-secondary);
}

.twa-notice-box {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-sm);
  padding: 1.1rem;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.user-greeting {
  font-size: 1.05rem;
  font-weight: 700;
  color: #fff;
}

.notice-desc {
  font-size: 0.84rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

.user-pill {
  align-self: center;
  font-size: 0.8rem;
  background: rgba(255, 255, 255, 0.06);
  padding: 0.25rem 0.65rem;
  border-radius: 9999px;
  color: var(--text-primary);
}

/* Inputs & Buttons */
.input-wrap label {
  display: block;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-secondary, #94a3b8);
  margin-bottom: 0.45rem;
}

.minimal-input {
  width: 100%;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--surface-border, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-sm, 6px);
  padding: 0.75rem 0.9rem;
  font-size: 0.98rem;
  color: #fff;
  transition: border-color 0.15s;
}

.minimal-input:focus {
  border-color: var(--accent);
}

.code-input {
  letter-spacing: 8px;
  font-size: 1.4rem;
  text-align: center;
  font-family: monospace;
}

.btn-submit {
  width: 100%;
  padding: 0.75rem;
  border-radius: var(--radius-sm, 6px);
  background: var(--accent);
  color: #fff;
  font-size: 0.92rem;
  font-weight: 600;
  transition: all 0.15s;
  margin-top: 0.35rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-submit:hover:not(:disabled) {
  background: var(--accent-hover);
  box-shadow: 0 0 14px var(--accent-glow);
}

.btn-submit:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-resend {
  font-size: 0.84rem;
  color: var(--text-secondary);
  text-align: center;
  padding: 0.4rem;
  transition: color 0.15s;
}

.btn-resend:hover {
  color: #fff;
}

.cooldown-text {
  text-align: center;
  font-size: 0.82rem;
  color: var(--text-muted);
}

.error-msg {
  color: #f87171;
  font-size: 0.85rem;
  text-align: center;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  padding: 0.6rem;
  border-radius: var(--radius-sm);
}

.minimal-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(255, 255, 255, 0.15);
  border-top-color: #2aabee;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* Mobile adaptations */
@media (max-width: 480px) {
  .login-container {
    padding: 0.75rem;
    align-items: flex-start;
  }
  .login-box {
    padding: 1.5rem 1.25rem;
    margin-top: 1rem;
    border-radius: 12px;
  }
  .brand-text h2 {
    font-size: 1.1rem;
  }
}
</style>
