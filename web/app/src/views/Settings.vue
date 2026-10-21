<template>
  <div class="admin-page">
    <AdminNav />

    <!-- Toast Notification -->
    <transition name="fade">
      <div v-if="toast.message" class="toast-banner" :class="toast.type">
        <span>{{ toast.message }}</span>
        <button @click="toast.message = ''" class="toast-close">✕</button>
      </div>
    </transition>

    <main class="page-body">
      <div class="header-intro">
        <h1 class="page-title">⚙️ Настройки платформы</h1>
        <p class="page-subtitle">Глобальные параметры клуба, переключатели режимов и ссылки интеграций</p>
      </div>

      <div class="settings-wrap">
        <form @submit.prevent="saveSettings" class="settings-form">
          <!-- Section 1: Global Platform Switches -->
          <div class="settings-section">
            <h3 class="section-title">Переключатели режимов работы</h3>
            
            <div class="switch-row">
              <div class="switch-info">
                <strong>Регистрация открыта</strong>
                <span>Разрешить новым участникам регистрироваться через бота и веб</span>
              </div>
              <label class="toggle-switch">
                <input type="checkbox" v-model="form.registration_open" />
                <span class="slider"></span>
              </label>
            </div>

            <div class="switch-row">
              <div class="switch-info">
                <strong>Отключение обязательной OTP-верификации</strong>
                <span>Регистрировать студентов сразу без ввода 6-значного кода из почты</span>
              </div>
              <label class="toggle-switch">
                <input type="checkbox" v-model="form.otp_bypass_enabled" />
                <span class="slider"></span>
              </label>
            </div>

            <div class="switch-row">
              <div class="switch-info">
                <strong>Режим технического обслуживания (Maintenance)</strong>
                <span>Блокирует публичные действия и выводит сообщение о техработах</span>
              </div>
              <label class="toggle-switch">
                <input type="checkbox" v-model="form.maintenance_mode" />
                <span class="slider"></span>
              </label>
            </div>
          </div>

          <!-- Section 2: Club Info & Socials -->
          <div class="settings-section">
            <h3 class="section-title">Информация о клубе и ссылки</h3>

            <div class="form-row">
              <div class="form-group">
                <label>Название сообщества</label>
                <input v-model="form.club_name" class="form-input" />
              </div>
              <div class="form-group">
                <label>Юзернейм бота Telegram</label>
                <input v-model="form.bot_username" placeholder="aitu_gaming_bot" class="form-input" />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Официальный Telegram-канал</label>
                <input v-model="form.channel_url" type="url" class="form-input" />
              </div>
              <div class="form-group">
                <label>Discord-сервер</label>
                <input v-model="form.discord_url" type="url" class="form-input" />
              </div>
            </div>

            <div class="form-group">
              <label>Чат поддержки AITU Gaming</label>
              <input v-model="form.support_chat_url" type="url" class="form-input" />
            </div>
          </div>

          <!-- Section 3: Minecraft Server -->
          <div class="settings-section">
            <h3 class="section-title">Сервер Minecraft</h3>

            <div class="form-row">
              <div class="form-group">
                <label>IP-адрес сервера (публичный хост)</label>
                <input v-model="form.minecraft_server_host" class="form-input" />
              </div>
              <div class="form-group">
                <label>Версия ядра и модов</label>
                <input v-model="form.minecraft_version" class="form-input" />
              </div>
            </div>
          </div>

          <div class="form-footer">
            <button type="submit" :disabled="saving" class="btn-save">
              {{ saving ? 'Сохранение настроек...' : '💾 Сохранить изменения' }}
            </button>
          </div>
        </form>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AdminNav from '../components/AdminNav.vue'
import { settingsApi } from '../services/api'

const saving = ref(false)
const form = ref({
  club_name: '',
  bot_username: '',
  channel_url: '',
  discord_url: '',
  support_chat_url: '',
  minecraft_server_host: '',
  minecraft_version: '',
  registration_open: true,
  otp_bypass_enabled: true,
  maintenance_mode: false,
})

const toast = ref({ message: '', type: 'info' })
const showToast = (message, type = 'info') => {
  toast.value = { message, type }
  setTimeout(() => { toast.value.message = '' }, 3500)
}

const loadSettings = async () => {
  try {
    const res = await settingsApi.getSettings()
    form.value = { ...form.value, ...res.data }
  } catch (err) {
    showToast('Ошибка загрузки настроек', 'error')
  }
}

const saveSettings = async () => {
  saving.value = true
  try {
    await settingsApi.updateSettings(form.value)
    showToast('Настройки платформы успешно сохранены!', 'success')
  } catch (err) {
    showToast('Ошибка сохранения настроек', 'error')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.admin-page {
  min-height: 100vh;
  background-color: #090a0f;
  color: #f8fafc;
  padding-bottom: 4rem;
}

.page-body {
  max-width: 900px;
  margin: 0 auto;
  padding: 1.5rem;
}

.header-intro {
  margin-bottom: 1.5rem;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0;
  color: #f1f5f9;
}

.page-subtitle {
  margin: 0.25rem 0 0;
  font-size: 0.85rem;
  color: #64748b;
}

.settings-wrap {
  background: #11141e;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 1.5rem;
}

.settings-section {
  padding-bottom: 1.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.settings-section:last-of-type {
  border-bottom: none;
  padding-bottom: 0;
  margin-bottom: 0;
}

.section-title {
  margin: 0 0 1rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: #f1f5f9;
}

.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.switch-row:last-child {
  border-bottom: none;
}

.switch-info {
  display: flex;
  flex-direction: column;
}

.switch-info strong {
  font-size: 0.86rem;
  color: #f1f5f9;
}

.switch-info span {
  font-size: 0.76rem;
  color: #64748b;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background-color: rgba(255, 255, 255, 0.1);
  transition: 0.2s;
  border-radius: 24px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.2s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: #22c55e;
}

input:checked + .slider:before {
  transform: translateX(20px);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

@media (max-width: 640px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  font-size: 0.78rem;
  color: #94a3b8;
  margin-bottom: 0.35rem;
  font-weight: 500;
}

.form-input {
  width: 100%;
  background: #090a0f;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #ffffff;
  padding: 0.55rem 0.85rem;
  border-radius: 6px;
  font-size: 0.85rem;
  box-sizing: border-box;
}

.form-footer {
  margin-top: 1.5rem;
  display: flex;
  justify-content: flex-end;
}

.btn-save {
  background: #ef4444;
  border: none;
  color: #ffffff;
  font-weight: 600;
  font-size: 0.88rem;
  padding: 0.65rem 1.4rem;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.btn-save:hover:not(:disabled) {
  background: #dc2626;
}

.btn-save:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.toast-banner {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 300;
  background: #1e293b;
  border: 1px solid rgba(255, 255, 255, 0.15);
  padding: 0.75rem 1.25rem;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.84rem;
}

.toast-banner.success {
  border-color: #22c55e;
  color: #22c55e;
}

.toast-banner.error {
  border-color: #ef4444;
  color: #ef4444;
}

.toast-close {
  background: transparent;
  border: none;
  color: inherit;
  cursor: pointer;
}
</style>
