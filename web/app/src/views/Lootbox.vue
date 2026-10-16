<template>
  <div class="lootbox-page">
    <!-- Background dynamic glow effects -->
    <div class="ambient-glow" :class="{ 'epic-burst': revealed }"></div>

    <!-- Header bar -->
    <header class="tma-header">
      <div class="brand">
        <span class="hub-badge">AITU GAMING HUB</span>
        <span class="season-badge">SEASON 2026</span>
      </div>
      <button v-if="canClose" @click="closeWebApp" class="close-btn" title="Закрыть">✕</button>
    </header>

    <div class="content-container">
      <div v-if="errorText" class="error-banner">
        <span>{{ errorText }}</span>
        <button @click="errorText = ''" class="btn-close-error">✕</button>
      </div>

      <!-- Loading state -->
      <div v-if="loading" class="state-box">
        <div class="cyber-spinner"></div>
        <p class="loading-label">Синхронизация профиля с хабом...</p>
      </div>

      <!-- No role assigned -->
      <div v-else-if="!status.has_role" class="state-box empty-state">
        <div class="empty-icon">🛡️</div>
        <h2>Привет, {{ status.first_name }}!</h2>
        <p class="desc">
          Вам пока не назначена роль стаффа в AITU Gaming Club.
          Роли распределяются администрацией клуба после прохождения отбора.
        </p>
        <button class="action-btn secondary" @click="closeWebApp">Вернуться в Hub</button>
      </div>

      <!-- Case not opened yet -->
      <div v-else-if="!revealed" class="case-stage">
        <div class="intro-text">
          <span class="case-rarity-pill">CLASSIFIED CASE</span>
          <h1 class="headline">Вам назначена роль в клубе!</h1>
          <p class="sub-headline">Откройте наградной кейс AITU Hub, чтобы раскрыть вашу должность и допуск.</p>
        </div>

        <!-- 3D / Pseudo-3D Mystery Box -->
        <div 
          class="case-viewport" 
          :class="{ 'shaking-intense': isOpening }"
          @click="!isOpening && handleOpen()"
        >
          <div class="case-platform"></div>
          <div class="case-box">
            <div class="case-lid">
              <div class="lid-stripe"></div>
              <div class="lock-seal">★</div>
            </div>
            <div class="case-body">
              <div class="case-core-glow"></div>
              <div class="case-insignia">AITU</div>
              <div class="case-details">STAFF PASS</div>
            </div>
          </div>
          <!-- Holo pedestal ring -->
          <div class="holo-ring"></div>
        </div>

        <button 
          class="claim-btn" 
          :disabled="isOpening" 
          @click="handleOpen"
        >
          <span v-if="!isOpening" class="btn-text">⚡ ОТКРЫТЬ КЕЙС</span>
          <span v-else class="btn-text opening">РАСПАКОВКА...</span>
          <div class="btn-reflection"></div>
        </button>

        <p class="tap-hint">Нажмите на кнопку или на кейс</p>
      </div>

      <!-- Role Revealed Screen -->
      <div v-else class="reveal-stage fade-scale-in">
        <div class="confetti-sparks"></div>

        <div class="card-glow-halo" :class="getRoleRarity(result.staff_role)"></div>

        <div class="role-card" :class="getRoleRarity(result.staff_role)">
          <div class="card-top-bar">
            <span class="org-name">AITU ESPORTS CLUB</span>
            <span class="rarity-label">{{ getRarityLabel(result.staff_role) }}</span>
          </div>

          <div class="role-icon-wrapper">
            <span class="role-emoji">{{ getRoleIcon(result.staff_role) }}</span>
          </div>

          <span class="reveal-greeting">Поздравляем, {{ status.first_name }}!</span>
          <h2 class="role-main-title">{{ result.role_title }}</h2>

          <div v-if="result.discipline" class="discipline-badge">
            <span class="disc-label">ДИСЦИПЛИНА</span>
            <span class="disc-value">{{ result.discipline.toUpperCase() }}</span>
          </div>

          <div class="card-footer-info">
            <div class="badge-status">
              <span class="dot-online"></span>
              ДОСТУП АКТИВИРОВАН
            </div>
            <span class="date-stamp" v-if="result.revealed_at">{{ formatDate(result.revealed_at) }}</span>
          </div>
        </div>

        <div class="card-actions">
          <button class="action-btn primary" @click="closeWebApp">
            ✓ ПРИНЯТЬ И ПЕРЕЙТИ В HUB
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'

const loading = ref(true)
const isOpening = ref(false)
const revealed = ref(false)

const status = ref({
  has_role: false,
  is_revealed: false,
  first_name: '',
  staff_role: null,
  role_title: null,
  discipline: null,
})

const result = ref({
  staff_role: '',
  role_title: '',
  discipline: null,
  revealed_at: null,
})

const canClose = computed(() => !!window.Telegram?.WebApp)
const errorText = ref('')

const getAuthHeaders = () => {
  const headers = {}
  const token = localStorage.getItem('access_token')
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  if (window.Telegram?.WebApp?.initData) {
    headers['X-Telegram-Init-Data'] = window.Telegram.WebApp.initData
  }
  return headers
}

const fetchStatus = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/v1/lootbox/status', {
      headers: getAuthHeaders(),
    })
    status.value = res.data
    if (res.data.is_revealed && res.data.staff_role) {
      result.value = {
        staff_role: res.data.staff_role,
        role_title: res.data.role_title || res.data.staff_role,
        discipline: res.data.discipline,
      }
      revealed.value = true
    }
  } catch (err) {
    console.error('Failed to load lootbox status:', err)
  } finally {
    loading.value = false
  }
}

const handleOpen = async () => {
  if (isOpening.value) return
  isOpening.value = true

  // Haptic Feedback start
  if (window.Telegram?.WebApp?.HapticFeedback) {
    try {
      window.Telegram.WebApp.HapticFeedback.impactOccurred('heavy')
    } catch (e) {
      console.debug('Haptic error:', e)
    }
  }

  try {
    const res = await axios.post('/api/v1/lootbox/open', {}, {
      headers: getAuthHeaders(),
    })

    // Rhythmic haptics during 2.2s opening
    setTimeout(() => {
      if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.impactOccurred('medium')
      }
    }, 700)

    setTimeout(() => {
      if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.impactOccurred('heavy')
      }
    }, 1400)

    setTimeout(() => {
      result.value = res.data
      isOpening.value = false
      revealed.value = true

      if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.notificationOccurred('success')
      }
    }, 2200)
  } catch (err) {
    isOpening.value = false
    const msg = err.response?.data?.detail || 'Не удалось открыть кейс. Попробуйте снова.'
    errorText.value = msg
  }
}

const getRoleRarity = (role) => {
  const r = (role || '').toLowerCase()
  if (['head_admin', 'president', 'vice_president'].includes(r)) return 'mythical-gold'
  if (['discipline_admin', 'manager'].includes(r)) return 'covert-crimson'
  if (['designer', 'commentator', 'streamer'].includes(r)) return 'classified-purple'
  return 'restricted-blue'
}

const getRarityLabel = (role) => {
  const r = (role || '').toLowerCase()
  if (['head_admin', 'president', 'vice_president'].includes(r)) return 'LEGENDARY TIER'
  if (['discipline_admin', 'manager'].includes(r)) return 'COVERT TIER'
  if (['designer', 'commentator', 'streamer'].includes(r)) return 'SPECIALIST TIER'
  return 'OFFICIAL STAFF'
}

const getRoleIcon = (role) => {
  const r = (role || '').toLowerCase()
  const map = {
    discipline_admin: '⚔️',
    manager: '📋',
    smm: '📱',
    designer: '🎨',
    commentator: '🎙️',
    streamer: '🎥',
    discord_admin: '💬',
    head_admin: '🛡️',
    president: '👑',
    vice_president: '🎖️',
  }
  return map[r] || '⚡'
}

const formatDate = (isoString) => {
  if (!isoString) return ''
  try {
    const d = new Date(isoString)
    return d.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return ''
  }
}

const closeWebApp = () => {
  if (window.Telegram?.WebApp) {
    window.Telegram.WebApp.close()
  } else {
    window.location.href = '/'
  }
}

onMounted(() => {
  if (window.Telegram?.WebApp) {
    window.Telegram.WebApp.ready()
    window.Telegram.WebApp.expand()
  }
  fetchStatus()
})
</script>

<style scoped>
.lootbox-page {
  position: relative;
  min-height: 100vh;
  min-height: 100dvh;
  width: 100%;
  background: radial-gradient(circle at 50% 20%, #171d2d 0%, #090c14 70%);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  user-select: none;
  font-family: var(--font-family, sans-serif);
}

.ambient-glow {
  position: absolute;
  top: 15%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 380px;
  height: 380px;
  background: radial-gradient(circle, rgba(239, 68, 68, 0.22) 0%, rgba(239, 68, 68, 0) 70%);
  filter: blur(50px);
  pointer-events: none;
  transition: all 1s ease;
}

.ambient-glow.epic-burst {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(255, 187, 0, 0.35) 0%, rgba(239, 68, 68, 0.2) 40%, transparent 75%);
}

.tma-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  z-index: 10;
}

.brand {
  display: flex;
  gap: 8px;
  align-items: center;
}

.hub-badge {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1.2px;
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.season-badge {
  font-size: 11px;
  font-weight: 700;
  color: #f59e0b;
}

.close-btn {
  background: rgba(255, 255, 255, 0.08);
  border: none;
  color: #94a3b8;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}

.content-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 5;
}

.state-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  max-width: 340px;
}

.cyber-spinner {
  width: 48px;
  height: 48px;
  border: 3px solid rgba(239, 68, 68, 0.2);
  border-top-color: #ef4444;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 54px;
  margin-bottom: 12px;
}

.desc {
  font-size: 14px;
  color: #94a3b8;
  margin: 10px 0 24px;
  line-height: 1.6;
}

/* Case Stage */
.case-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  width: 100%;
  max-width: 380px;
}

.case-rarity-pill {
  display: inline-block;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 2px;
  color: #ef4444;
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.3);
  padding: 4px 14px;
  border-radius: 20px;
  margin-bottom: 10px;
}

.headline {
  font-size: 22px;
  font-weight: 800;
  color: #fff;
  margin-bottom: 6px;
}

.sub-headline {
  font-size: 13px;
  color: #94a3b8;
  margin-bottom: 24px;
  line-height: 1.4;
}

/* Pseudo-3D Case */
.case-viewport {
  position: relative;
  width: 220px;
  height: 200px;
  margin: 10px 0 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.case-viewport:hover {
  transform: translateY(-4px) scale(1.02);
}

.case-box {
  position: relative;
  width: 170px;
  height: 140px;
  background: linear-gradient(145deg, #1f2738, #101524);
  border-radius: 16px;
  border: 2px solid rgba(255, 255, 255, 0.14);
  box-shadow: 
    0 20px 40px rgba(0, 0, 0, 0.7),
    0 0 30px rgba(239, 68, 68, 0.2),
    inset 0 1px 1px rgba(255, 255, 255, 0.3);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 12px;
  overflow: hidden;
}

.case-lid {
  height: 38px;
  background: linear-gradient(180deg, #2b354c, #1a2233);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.lid-stripe {
  position: absolute;
  width: 100%;
  height: 2px;
  background: #ef4444;
  top: 50%;
  opacity: 0.8;
}

.lock-seal {
  width: 22px;
  height: 22px;
  background: #ef4444;
  border-radius: 50%;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 900;
  box-shadow: 0 0 10px #ef4444;
  z-index: 2;
}

.case-body {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-top: 8px;
}

.case-core-glow {
  position: absolute;
  width: 60px;
  height: 60px;
  background: radial-gradient(circle, rgba(239, 68, 68, 0.5) 0%, transparent 70%);
  filter: blur(10px);
}

.case-insignia {
  font-size: 20px;
  font-weight: 900;
  letter-spacing: 2px;
  color: #fff;
  text-shadow: 0 0 10px rgba(255, 255, 255, 0.4);
}

.case-details {
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 1.5px;
  color: #ef4444;
  margin-top: 4px;
}

.holo-ring {
  position: absolute;
  bottom: 0px;
  width: 190px;
  height: 40px;
  border-radius: 50%;
  border: 2px solid rgba(239, 68, 68, 0.3);
  box-shadow: 0 0 20px rgba(239, 68, 68, 0.3), inset 0 0 10px rgba(239, 68, 68, 0.2);
  transform: rotateX(65deg);
  pointer-events: none;
}

/* Shaking animation */
.shaking-intense {
  animation: caseRumble 0.15s infinite;
}

@keyframes caseRumble {
  0% { transform: translate(2px, 1px) rotate(0deg) scale(1.05); }
  25% { transform: translate(-3px, -2px) rotate(-3deg) scale(1.06); }
  50% { transform: translate(3px, 2px) rotate(3deg) scale(1.07); }
  75% { transform: translate(-2px, 1px) rotate(-2deg) scale(1.08); }
  100% { transform: translate(1px, -2px) rotate(1deg) scale(1.05); }
}

/* Open Button */
.claim-btn {
  position: relative;
  width: 100%;
  padding: 16px;
  background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
  border: none;
  border-radius: 14px;
  color: white;
  font-weight: 800;
  font-size: 16px;
  letter-spacing: 1px;
  cursor: pointer;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(239, 68, 68, 0.45);
  transition: transform 0.2s, box-shadow 0.2s;
}

.claim-btn:active {
  transform: scale(0.98);
}

.claim-btn:disabled {
  opacity: 0.85;
  cursor: wait;
}

.btn-reflection {
  position: absolute;
  top: 0;
  left: -100%;
  width: 60%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  animation: shine 3s infinite;
}

@keyframes shine {
  0% { left: -100%; }
  20% { left: 150%; }
  100% { left: 150%; }
}

.tap-hint {
  font-size: 12px;
  color: #64748b;
  margin-top: 14px;
}

/* Role Card Revealed */
.reveal-stage {
  width: 100%;
  max-width: 360px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.fade-scale-in {
  animation: popCard 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
}

@keyframes popCard {
  0% { opacity: 0; transform: scale(0.6) translateY(30px); }
  100% { opacity: 1; transform: scale(1) translateY(0); }
}

.role-card {
  width: 100%;
  background: #111624;
  border-radius: 20px;
  padding: 24px 20px;
  border: 2px solid rgba(255, 255, 255, 0.15);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  position: relative;
  overflow: hidden;
}

.role-card.mythical-gold {
  border-color: #f59e0b;
  box-shadow: 0 0 40px rgba(245, 158, 11, 0.35);
}

.role-card.covert-crimson {
  border-color: #ef4444;
  box-shadow: 0 0 40px rgba(239, 68, 68, 0.35);
}

.role-card.classified-purple {
  border-color: #a855f7;
  box-shadow: 0 0 40px rgba(168, 85, 247, 0.35);
}

.card-top-bar {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.org-name {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 1px;
  color: #94a3b8;
}

.rarity-label {
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 1px;
  color: #f59e0b;
}

.role-icon-wrapper {
  width: 84px;
  height: 84px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.12);
  margin-bottom: 16px;
}

.role-emoji {
  font-size: 42px;
}

.reveal-greeting {
  font-size: 13px;
  color: #94a3b8;
  margin-bottom: 4px;
}

.role-main-title {
  font-size: 24px;
  font-weight: 900;
  color: #fff;
  margin-bottom: 14px;
  line-height: 1.2;
}

.discipline-badge {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  padding: 6px 14px;
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 20px;
}

.disc-label {
  font-size: 10px;
  color: #94a3b8;
  font-weight: 700;
}

.disc-value {
  font-size: 12px;
  color: #ef4444;
  font-weight: 900;
  letter-spacing: 1px;
}

.card-footer-info {
  width: 100%;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding-top: 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: #94a3b8;
}

.badge-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  color: #10b981;
}

.dot-online {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
}

.card-actions {
  width: 100%;
  margin-top: 24px;
}

.action-btn {
  width: 100%;
  padding: 14px;
  border-radius: 12px;
  font-weight: 800;
  font-size: 14px;
  letter-spacing: 0.5px;
  cursor: pointer;
  border: none;
  transition: transform 0.2s;
}

.action-btn.primary {
  background: #10b981;
  color: #fff;
  box-shadow: 0 4px 16px rgba(16, 185, 129, 0.4);
}

.action-btn.secondary {
  background: rgba(255, 255, 255, 0.08);
  color: #f8fafc;
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.error-banner {
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.35);
  color: #fca5a5;
  padding: 0.75rem 1rem;
  border-radius: 10px;
  margin-bottom: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.88rem;
}

.btn-close-error {
  color: inherit;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0 0.4rem;
}
</style>
