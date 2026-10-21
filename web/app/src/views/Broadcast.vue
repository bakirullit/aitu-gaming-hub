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
        <h1 class="page-title">📢 Массовая рассылка уведомлений</h1>
        <p class="page-subtitle">Отправка официальных анонсов, новостей и турнирных оповещений в Telegram</p>
      </div>

      <div class="broadcast-layout">
        <!-- Left: Composer Form -->
        <div class="panel composer-panel">
          <div class="panel-header">
            <h3>Составление рассылки</h3>
          </div>

          <form @submit.prevent="confirmSend" class="panel-form">
            <!-- Target Audience Selector -->
            <div class="form-group">
              <label>Целевая аудитория *</label>
              <div class="audience-grid">
                <label 
                  v-for="aud in audiencesData.audiences" 
                  :key="aud.id" 
                  class="audience-card"
                  :class="{ selected: target === aud.id }"
                >
                  <input type="radio" v-model="target" :value="aud.id" />
                  <span class="aud-name">{{ aud.label }}</span>
                  <span class="aud-count">{{ aud.count }} получателей</span>
                </label>
              </div>
            </div>

            <!-- Specific Chat Selector if 'chats' or individual chat -->
            <div v-if="audiencesData.chats?.length" class="form-group">
              <label>Или выбрать конкретный чат/группу:</label>
              <select v-model="target" class="form-input">
                <option value="all">-- Использовать выбранную группу выше --</option>
                <option v-for="c in audiencesData.chats" :key="c.id" :value="'chat:' + c.id">
                  Чат: {{ c.title }} (ID: {{ c.id }})
                </option>
              </select>
            </div>

            <!-- Message Text -->
            <div class="form-group">
              <label>Текст сообщения (поддерживается HTML теги: &lt;b&gt;, &lt;i&gt;, &lt;code&gt;, &lt;a&gt;) *</label>
              <textarea 
                v-model="message" 
                rows="8" 
                required 
                placeholder="🏆 <b>Внимание, киберспортсмены AITU!</b>&#10;&#10;Открыта регистрация на осенний кубок..." 
                class="form-textarea"
              ></textarea>
            </div>

            <!-- Optional Inline Button -->
            <div class="form-row">
              <div class="form-group">
                <label>Текст инлайн-кнопки (опционально)</label>
                <input v-model="buttonText" placeholder="📝 Зарегистрироваться" class="form-input" />
              </div>
              <div class="form-group">
                <label>Ссылка кнопки (URL)</label>
                <input v-model="buttonUrl" type="url" placeholder="https://..." class="form-input" />
              </div>
            </div>

            <button type="submit" :disabled="sending || !message.trim()" class="btn-send">
              {{ sending ? 'Идет отправка сообщений...' : '🚀 Запустить рассылку' }}
            </button>
          </form>
        </div>

        <!-- Right: Telegram Mockup Preview -->
        <div class="panel preview-panel">
          <div class="panel-header">
            <h3>📱 Превью сообщения в Telegram</h3>
          </div>

          <div class="phone-frame">
            <div class="phone-bar">
              <span class="bot-info-title">AITU Gaming Bot</span>
              <span class="bot-badge">bot</span>
            </div>

            <div class="phone-screen">
              <div class="telegram-bubble">
                <div class="tg-text" v-html="renderedPreview"></div>
                <div v-if="buttonText && buttonUrl" class="tg-btn-wrap">
                  <a :href="buttonUrl" target="_blank" class="tg-inline-btn">
                    {{ buttonText }}
                  </a>
                </div>
                <div class="tg-time">12:00</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Confirmation Modal -->
    <div v-if="showConfirmModal" class="modal-backdrop" @click.self="showConfirmModal = false">
      <div class="modal-card mini">
        <div class="modal-header">
          <h3>Подтверждение рассылки</h3>
          <button @click="showConfirmModal = false" class="btn-close">✕</button>
        </div>
        <div class="modal-body">
          <p>Вы уверены, что хотите запустить рассылку?</p>
          <p class="target-summary">
            Аудитория: <strong>{{ target }}</strong>
          </p>
          <p class="warning-text">⚠️ Сообщения будут доставлены реальным пользователям в Telegram.</p>
        </div>
        <div class="modal-actions">
          <button @click="showConfirmModal = false" class="btn-cancel">Отмена</button>
          <button @click="executeSend" class="btn-danger">Да, отправить сейчас</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import AdminNav from '../components/AdminNav.vue'
import { broadcastApi } from '../services/api'

const target = ref('students')
const message = ref('🏆 <b>Внимание, игроки AITU!</b>\n\nВ эти выходные стартует турнир по <b>CS2 2v2</b>.\nПриглашаем всех студентов принять участие и побороться за призовой фонд!\n\nРегистрация бесплатна прямо через бота.')
const buttonText = ref('🎮 Открыть Турниры')
const buttonUrl = ref('https://aitu-gaming.y-not-devs.com/tournaments')

const audiencesData = ref({ audiences: [], chats: [] })
const sending = ref(false)
const showConfirmModal = ref(false)

const toast = ref({ message: '', type: 'info' })
const showToast = (message, type = 'info') => {
  toast.value = { message, type }
  setTimeout(() => { toast.value.message = '' }, 4000)
}

const renderedPreview = computed(() => {
  if (!message.value) return '<i>Введите текст для предпросмотра...</i>'
  return message.value.replace(/\n/g, '<br/>')
})

const fetchAudiences = async () => {
  try {
    const res = await broadcastApi.getAudiences()
    audiencesData.value = res.data
  } catch (err) {
    console.warn('Could not fetch broadcast audiences:', err)
  }
}

const confirmSend = () => {
  showConfirmModal.value = true
}

const executeSend = async () => {
  showConfirmModal.value = false
  sending.value = true
  try {
    const res = await broadcastApi.send({
      target: target.value,
      message: message.value,
      button_text: buttonText.value || undefined,
      button_url: buttonUrl.value || undefined,
    })
    showToast(`Рассылка завершена: успешно отправлено ${res.data.sent_count} из ${res.data.total_targets}`, 'success')
  } catch (err) {
    showToast(err.response?.data?.detail || 'Ошибка отправки рассылки', 'error')
  } finally {
    sending.value = false
  }
}

onMounted(() => {
  fetchAudiences()
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
  max-width: 1400px;
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

.broadcast-layout {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 1.5rem;
}

@media (max-width: 960px) {
  .broadcast-layout {
    grid-template-columns: 1fr;
  }
}

.panel {
  background: #11141e;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
  overflow: hidden;
}

.panel-header {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.panel-header h3 {
  margin: 0;
  font-size: 0.95rem;
  color: #f1f5f9;
}

.panel-form {
  padding: 1.25rem;
}

.form-group {
  margin-bottom: 1.25rem;
}

.form-group label {
  display: block;
  font-size: 0.78rem;
  color: #94a3b8;
  margin-bottom: 0.4rem;
  font-weight: 500;
}

.audience-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.65rem;
}

.audience-card {
  background: #090a0f;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  position: relative;
  transition: all 0.15s ease;
}

.audience-card input {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
}

.audience-card.selected {
  border-color: #ef4444;
  background: rgba(239, 68, 68, 0.06);
}

.aud-name {
  font-size: 0.82rem;
  font-weight: 600;
  color: #f1f5f9;
}

.aud-count {
  font-size: 0.72rem;
  color: #64748b;
  margin-top: 0.2rem;
}

.form-input, .form-textarea {
  width: 100%;
  background: #090a0f;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #ffffff;
  padding: 0.65rem 0.85rem;
  border-radius: 6px;
  font-size: 0.85rem;
  box-sizing: border-box;
}

.form-textarea {
  font-family: inherit;
  resize: vertical;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.btn-send {
  width: 100%;
  background: #ef4444;
  border: none;
  color: #ffffff;
  font-weight: 700;
  font-size: 0.9rem;
  padding: 0.75rem;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.btn-send:hover:not(:disabled) {
  background: #dc2626;
}

.btn-send:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Telegram Mockup */
.preview-panel {
  display: flex;
  flex-direction: column;
}

.phone-frame {
  margin: 1.5rem auto;
  width: 320px;
  background: #17212b;
  border-radius: 18px;
  border: 2px solid rgba(255, 255, 255, 0.1);
  overflow: hidden;
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.6);
}

.phone-bar {
  background: #242f3d;
  padding: 0.65rem 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.2);
}

.bot-info-title {
  font-size: 0.82rem;
  font-weight: 600;
  color: #ffffff;
}

.bot-badge {
  font-size: 0.62rem;
  background: #5288c1;
  color: #ffffff;
  padding: 0.05rem 0.35rem;
  border-radius: 4px;
  text-transform: uppercase;
}

.phone-screen {
  padding: 1rem;
  min-height: 340px;
  background: #0e1621;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

.telegram-bubble {
  background: #182533;
  border-radius: 10px 10px 10px 2px;
  padding: 0.75rem 0.85rem;
  color: #ffffff;
  font-size: 0.82rem;
  line-height: 1.45;
  position: relative;
}

.tg-text {
  word-break: break-word;
}

.tg-btn-wrap {
  margin-top: 0.65rem;
}

.tg-inline-btn {
  display: block;
  text-align: center;
  background: rgba(82, 136, 193, 0.2);
  color: #64b5f6;
  border: 1px solid rgba(82, 136, 193, 0.4);
  padding: 0.4rem;
  border-radius: 6px;
  font-size: 0.78rem;
  text-decoration: none;
  font-weight: 500;
}

.tg-time {
  text-align: right;
  font-size: 0.65rem;
  color: #6c7883;
  margin-top: 0.3rem;
}

/* Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.modal-card.mini {
  background: #11141e;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  width: 100%;
  max-width: 440px;
  overflow: hidden;
}

.modal-header {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-header h3 {
  margin: 0;
  font-size: 1rem;
  color: #f1f5f9;
}

.modal-body {
  padding: 1.25rem;
  font-size: 0.85rem;
  color: #cbd5e1;
}

.warning-text {
  color: #f59e0b;
  font-size: 0.78rem;
  margin-top: 0.75rem;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.65rem;
  padding: 1rem 1.25rem;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.btn-cancel {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #94a3b8;
  padding: 0.45rem 0.85rem;
  border-radius: 6px;
  cursor: pointer;
}

.btn-danger {
  background: #ef4444;
  border: none;
  color: #ffffff;
  font-weight: 600;
  padding: 0.45rem 1rem;
  border-radius: 6px;
  cursor: pointer;
}
</style>
