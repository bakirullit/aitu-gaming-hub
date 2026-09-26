<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <router-link to="/tournaments" class="back-link">← Tournaments</router-link>
        <div class="brand">
          <img src="/logo.png" alt="AITU Gaming" class="brand-logo-login" />
          <h2>Admin Login</h2>
        </div>
        <p class="subtitle">Authenticate with your university Telegram account.</p>
      </div>

      <div v-if="!otpSent" class="step">
        <div class="input-wrap">
          <label>Telegram Identifier</label>
          <input 
            v-model="identifier" 
            type="text" 
            placeholder="Telegram ID or @username" 
            @keyup.enter="requestOtp"
            class="minimal-input"
          />
        </div>
        <button @click="requestOtp" :disabled="loading" class="btn-submit">
          {{ loading ? 'Sending...' : 'Request Code' }}
        </button>
        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
      </div>

      <div v-else class="step">
        <div class="input-wrap">
          <label>6-Digit Verification Code</label>
          <input 
            v-model="code" 
            type="text" 
            placeholder="000000" 
            maxlength="6"
            @keyup.enter="verifyOtp"
            class="minimal-input code-input"
          />
        </div>
        <button @click="verifyOtp" :disabled="loading || code.length !== 6" class="btn-submit">
          {{ loading ? 'Verifying...' : 'Authenticate' }}
        </button>
        
        <p class="cooldown-text" v-if="cooldown > 0">Resend available in {{ cooldown }}s</p>
        <button v-else @click="requestOtp" class="btn-resend">Resend Code</button>
        
        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'

const router = useRouter()

const identifier = ref('')
const code = ref('')
const otpSent = ref(false)
const loading = ref(false)
const errorMsg = ref('')
const cooldown = ref(0)

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

const requestOtp = async () => {
  if (!identifier.value) return
  errorMsg.value = ''
  loading.value = true
  
  try {
    const res = await api.post('/admin/auth/otp/request', { identifier: identifier.value })
    telegramId.value = res.data.telegram_id
    otpSent.value = true
    startCooldown()
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'Failed to request OTP'
  } finally {
    loading.value = false
  }
}

const verifyOtp = async () => {
  if (code.value.length !== 6 || !telegramId.value) return
  errorMsg.value = ''
  loading.value = true
  
  try {
    const res = await api.post('/admin/auth/otp/verify', { 
      telegram_id: telegramId.value, 
      code: code.value 
    })
    
    localStorage.setItem('access_token', res.data.access_token)
    localStorage.setItem('user', JSON.stringify(res.data.user))
    
    router.push('/admin')
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'Invalid or expired code'
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
  background-color: var(--bg-color, #090a0f);
  padding: 1.5rem;
}

.login-box {
  width: 100%;
  max-width: 380px;
  background: var(--surface-bg, #0f1117);
  border: 1px solid var(--surface-border, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-lg, 14px);
  padding: 2.25rem;
}

.login-header {
  margin-bottom: 2rem;
}

.back-link {
  display: inline-block;
  font-size: 0.82rem;
  color: var(--text-muted, #64748b);
  margin-bottom: 1.5rem;
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
  height: 36px;
  width: auto;
  object-fit: contain;
  display: block;
}

.brand h2 {
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.subtitle {
  font-size: 0.88rem;
  color: var(--text-secondary, #94a3b8);
  line-height: 1.4;
}

.step {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.input-wrap label {
  display: block;
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--text-secondary, #94a3b8);
  margin-bottom: 0.4rem;
}

.minimal-input {
  width: 100%;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--surface-border, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-sm, 6px);
  padding: 0.65rem 0.85rem;
  font-size: 0.95rem;
  color: #fff;
  transition: border-color 0.15s;
}

.minimal-input:focus {
  border-color: var(--accent);
}

.code-input {
  letter-spacing: 6px;
  font-size: 1.25rem;
  text-align: center;
  font-family: monospace;
}

.btn-submit {
  width: 100%;
  padding: 0.7rem;
  border-radius: var(--radius-sm, 6px);
  background: var(--accent);
  color: #fff;
  font-size: 0.9rem;
  font-weight: 600;
  transition: all 0.15s;
  margin-top: 0.5rem;
}

.btn-submit:hover:not(:disabled) {
  background: var(--accent-hover);
  box-shadow: 0 0 12px var(--accent-glow);
}

.btn-submit:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-resend {
  font-size: 0.82rem;
  color: var(--text-secondary);
  text-align: center;
  padding: 0.25rem;
  transition: color 0.15s;
}

.btn-resend:hover {
  color: #fff;
}

.cooldown-text {
  text-align: center;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.error-msg {
  color: #f87171;
  font-size: 0.85rem;
  text-align: center;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  padding: 0.5rem;
  border-radius: var(--radius-sm);
}
</style>
