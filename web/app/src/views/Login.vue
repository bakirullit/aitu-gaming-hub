<template>
  <div class="login-container">
    <div class="glass-panel login-box">
      <h2>AITU Gaming Hub Admin</h2>
      
      <div v-if="!otpSent" class="step-1">
        <p>Authenticate via Telegram</p>
        <div class="input-group">
          <input 
            v-model="identifier" 
            type="text" 
            placeholder="Telegram ID or @username" 
            @keyup.enter="requestOtp"
          />
        </div>
        <button @click="requestOtp" :disabled="loading" class="btn-primary">
          {{ loading ? 'Sending...' : 'Request Code' }}
        </button>
        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
      </div>

      <div v-else class="step-2">
        <p>Enter the 6-digit code sent to your Telegram.</p>
        <div class="input-group">
          <input 
            v-model="code" 
            type="text" 
            placeholder="000000" 
            maxlength="6"
            @keyup.enter="verifyOtp"
          />
        </div>
        <button @click="verifyOtp" :disabled="loading || code.length !== 6" class="btn-primary">
          {{ loading ? 'Verifying...' : 'Login' }}
        </button>
        
        <p class="cooldown-text" v-if="cooldown > 0">Resend available in {{ cooldown }}s</p>
        <button v-else @click="requestOtp" class="btn-text">Resend Code</button>
        
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
    
    // Save tokens and user data
    localStorage.setItem('access_token', res.data.access_token)
    localStorage.setItem('user', JSON.stringify(res.data.user))
    
    // Redirect to Admin panel
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
  background: radial-gradient(circle at top left, #1a1a2e, #16213e, #0f3460);
}

.login-box {
  width: 100%;
  max-width: 400px;
  padding: 3rem 2rem;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

h2 {
  margin-bottom: 0.5rem;
  font-size: 1.75rem;
  color: #fff;
}

p {
  color: #a0a0b0;
  margin-bottom: 1.5rem;
}

.input-group input {
  width: 100%;
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.2);
  color: #fff;
  font-size: 1.1rem;
  transition: all 0.2s;
  box-sizing: border-box;
}

.input-group input:focus {
  outline: none;
  border-color: #6c5ce7;
  box-shadow: 0 0 10px rgba(108, 92, 231, 0.4);
}

.btn-primary {
  width: 100%;
  padding: 1rem;
  border-radius: 8px;
  background: linear-gradient(135deg, #6c5ce7, #a29bfe);
  color: white;
  font-weight: 600;
  font-size: 1.1rem;
  border: none;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  margin-top: 1rem;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(108, 92, 231, 0.4);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-text {
  background: none;
  border: none;
  color: #a29bfe;
  cursor: pointer;
  margin-top: 1rem;
  text-decoration: underline;
}

.error-msg {
  color: #ff7675;
  margin-top: 1rem;
  font-size: 0.9rem;
}

.cooldown-text {
  color: #a0a0b0;
  margin-top: 1rem;
  font-size: 0.9rem;
}
</style>
