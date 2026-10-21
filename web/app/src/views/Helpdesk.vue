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
      <!-- Toolbar -->
      <div class="toolbar">
        <div class="toolbar-left">
          <div class="tab-pills">
            <button 
              class="tab-pill" 
              :class="{ active: currentTab === 'open' }"
              @click="switchTab('open')"
            >
              🔴 Новые ({{ openCount }})
            </button>
            <button 
              class="tab-pill" 
              :class="{ active: currentTab === 'in_progress' }"
              @click="switchTab('in_progress')"
            >
              🟡 В работе ({{ inProgressCount }})
            </button>
            <button 
              class="tab-pill" 
              :class="{ active: currentTab === 'resolved' }"
              @click="switchTab('resolved')"
            >
              🟢 Решенные ({{ resolvedCount }})
            </button>
            <button 
              class="tab-pill" 
              :class="{ active: currentTab === 'all' }"
              @click="switchTab('all')"
            >
              Все тикеты ({{ total }})
            </button>
          </div>
        </div>

        <div class="toolbar-right">
          <div class="search-wrap">
            <input 
              v-model="searchQuery" 
              @input="debounceSearch"
              type="text" 
              placeholder="Поиск по теме, автору, баркоду..." 
              class="search-input"
            />
          </div>
          <button @click="fetchTickets" class="btn-refresh" :disabled="loading">
            <span :class="{ 'spin-icon': loading }">🔄</span> Обновить
          </button>
        </div>
      </div>

      <!-- Tickets Table -->
      <div class="table-container">
        <table v-if="!loading || tickets.length > 0" class="minimal-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Пользователь</th>
              <th>Тема обращения</th>
              <th>Сообщение</th>
              <th>Статус</th>
              <th>Дата</th>
              <th class="text-right">Действия</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in tickets" :key="t.id" :class="{ 'row-open': t.status.toLowerCase() === 'open' }">
              <td class="mono">#{{ t.id }}</td>
              <td>
                <div class="user-meta">
                  <strong>{{ t.user?.full_name || ('ID: ' + t.user_id) }}</strong>
                  <span class="sub-text">
                    {{ t.user?.barcode ? '💳 ' + t.user_barcode || t.user?.barcode : '' }} 
                    {{ t.user?.academic_group ? '· ' + t.user.academic_group : '' }}
                    {{ t.user?.username ? '@' + t.user.username : '' }}
                  </span>
                </div>
              </td>
              <td>
                <span class="subject-title">{{ t.subject }}</span>
              </td>
              <td>
                <p class="message-preview">{{ t.message_text }}</p>
              </td>
              <td>
                <span class="status-chip" :class="t.status.toLowerCase()">
                  {{ t.status }}
                </span>
              </td>
              <td>
                <span class="time-text">{{ formatDate(t.created_at) }}</span>
              </td>
              <td class="text-right">
                <button @click="openDialog(t)" class="btn-action">
                  💬 Открыть тикет
                </button>
              </td>
            </tr>
            <tr v-if="tickets.length === 0 && !loading">
              <td colspan="7" class="empty-state">
                {{ currentTab === 'open' ? 'Нет открытых тикетов — служба поддержки свободна! 🎉' : 'Тикеты не найдены' }}
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="loading" class="loading-overlay">
          <div class="spinner"></div>
        </div>

        <div class="pagination">
          <span class="page-info">Показано {{ tickets.length }} из {{ total }}</span>
          <div class="page-controls">
            <button @click="prevPage" :disabled="offset === 0" class="btn-page">◀ Назад</button>
            <button @click="nextPage" :disabled="offset + limit >= total" class="btn-page">Вперед ▶</button>
          </div>
        </div>
      </div>
    </main>

    <!-- Ticket Detail & Reply Modal -->
    <div v-if="activeTicket" class="modal-backdrop" @click.self="activeTicket = null">
      <div class="modal-card wide">
        <div class="modal-header">
          <div>
            <h3>Тикет #{{ activeTicket.id }}: {{ activeTicket.subject }}</h3>
            <span class="modal-sub">
              Автор: {{ activeTicket.user?.full_name || ('ID: ' + activeTicket.user_id) }} 
              ({{ activeTicket.user?.username ? '@' + activeTicket.user.username : 'Telegram User' }})
            </span>
          </div>
          <button @click="activeTicket = null" class="btn-close">✕</button>
        </div>

        <div class="modal-body dialog-body">
          <!-- Student Message Bubble -->
          <div class="msg-bubble user-bubble">
            <div class="bubble-header">
              <span class="sender-name">👤 {{ activeTicket.user?.full_name || 'Студент' }}</span>
              <span class="msg-time">{{ formatDate(activeTicket.created_at) }}</span>
            </div>
            <div class="bubble-text">{{ activeTicket.message_text }}</div>
          </div>

          <!-- Status Controls -->
          <div class="status-control-strip">
            <span class="strip-label">Текущий статус:</span>
            <button 
              @click="setStatus('open')" 
              class="status-btn" 
              :class="{ active: activeTicket.status.toLowerCase() === 'open' }"
            >
              🔴 Open
            </button>
            <button 
              @click="setStatus('in_progress')" 
              class="status-btn" 
              :class="{ active: activeTicket.status.toLowerCase() === 'in_progress' }"
            >
              🟡 In Progress
            </button>
            <button 
              @click="setStatus('resolved')" 
              class="status-btn" 
              :class="{ active: activeTicket.status.toLowerCase() === 'resolved' }"
            >
              🟢 Resolved
            </button>
          </div>

          <!-- Admin Reply Form -->
          <form @submit.prevent="sendReply" class="reply-form">
            <label class="form-label">
              Ответ службы поддержки (отправится пользователю в Telegram-бот):
            </label>
            <textarea 
              v-model="replyText" 
              required 
              rows="4" 
              placeholder="Здравствуйте! Ваш вопрос решен..." 
              class="form-textarea"
            ></textarea>

            <div class="reply-actions">
              <label class="checkbox-label">
                <input type="checkbox" v-model="resolveOnReply" />
                <span>Отметить тикет как решенный (Resolved)</span>
              </label>

              <button type="submit" :disabled="sendingReply || !replyText.trim()" class="btn-reply">
                {{ sendingReply ? 'Отправка...' : '✉️ Отправить ответ в Telegram' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AdminNav from '../components/AdminNav.vue'
import { helpdeskApi } from '../services/api'

const loading = ref(false)
const tickets = ref([])
const total = ref(0)
const openCount = ref(0)
const inProgressCount = ref(0)
const resolvedCount = ref(0)
const limit = ref(25)
const offset = ref(0)
const searchQuery = ref('')
const currentTab = ref('open') // 'open' | 'in_progress' | 'resolved' | 'all'

const activeTicket = ref(null)
const replyText = ref('')
const resolveOnReply = ref(true)
const sendingReply = ref(false)

const toast = ref({ message: '', type: 'info' })
const showToast = (message, type = 'info') => {
  toast.value = { message, type }
  setTimeout(() => { toast.value.message = '' }, 3500)
}

let searchTimeout = null

const fetchTickets = async () => {
  loading.value = true
  try {
    const statusParam = currentTab.value === 'all' ? undefined : currentTab.value
    const res = await helpdeskApi.getTickets({
      status: statusParam,
      query: searchQuery.value || undefined,
      limit: limit.value,
      offset: offset.value,
    })
    tickets.value = res.data.items || []
    total.value = res.data.total || 0
    openCount.value = res.data.open_count || 0
    inProgressCount.value = res.data.in_progress_count || 0
    resolvedCount.value = res.data.resolved_count || 0
  } catch (err) {
    showToast('Ошибка загрузки тикетов', 'error')
  } finally {
    loading.value = false
  }
}

const switchTab = (tab) => {
  currentTab.value = tab
  offset.value = 0
  fetchTickets()
}

const debounceSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    offset.value = 0
    fetchTickets()
  }, 300)
}

const prevPage = () => {
  if (offset.value >= limit.value) {
    offset.value -= limit.value
    fetchTickets()
  }
}

const nextPage = () => {
  if (offset.value + limit.value < total.value) {
    offset.value += limit.value
    fetchTickets()
  }
}

const openDialog = (t) => {
  activeTicket.value = t
  replyText.value = ''
  resolveOnReply.value = true
}

const setStatus = async (newStatus) => {
  if (!activeTicket.value) return
  try {
    await helpdeskApi.updateStatus(activeTicket.value.id, newStatus)
    activeTicket.value.status = newStatus
    showToast(`Статус тикета #${activeTicket.value.id} изменен на ${newStatus}`, 'success')
    fetchTickets()
  } catch (err) {
    showToast('Ошибка смены статуса', 'error')
  }
}

const sendReply = async () => {
  if (!activeTicket.value || !replyText.value.trim()) return
  sendingReply.value = true
  try {
    const newStatus = resolveOnReply.value ? 'resolved' : 'in_progress'
    const res = await helpdeskApi.replyTicket(activeTicket.value.id, {
      reply: replyText.value,
      new_status: newStatus,
    })
    activeTicket.value.status = newStatus
    const notifiedText = res.data.telegram_notified ? 'пользователь уведомлен в Telegram' : 'бот офлайн'
    showToast(`Ответ отправлен (${notifiedText})`, 'success')
    activeTicket.value = null
    fetchTickets()
  } catch (err) {
    showToast(err.response?.data?.detail || 'Ошибка отправки ответа', 'error')
  } finally {
    sendingReply.value = false
  }
}

const formatDate = (iso) => {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleString('ru-RU', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

onMounted(() => {
  fetchTickets()
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
  max-width: 1500px;
  margin: 0 auto;
  padding: 1.5rem;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
}

.tab-pills {
  display: flex;
  gap: 0.5rem;
}

.tab-pill {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #94a3b8;
  font-size: 0.82rem;
  padding: 0.45rem 0.9rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.tab-pill.active {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.35);
  color: #ffffff;
  font-weight: 600;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.search-input {
  background: #11141e;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #f1f5f9;
  font-size: 0.82rem;
  padding: 0.45rem 0.85rem;
  border-radius: 6px;
  width: 280px;
}

.btn-refresh {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  padding: 0.45rem 0.85rem;
  border-radius: 6px;
  font-size: 0.82rem;
  cursor: pointer;
}

.table-container {
  background: #11141e;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  overflow: hidden;
  position: relative;
}

.minimal-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.84rem;
  text-align: left;
}

.minimal-table th {
  background: rgba(255, 255, 255, 0.02);
  color: #64748b;
  font-weight: 600;
  text-transform: uppercase;
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.minimal-table td {
  padding: 0.85rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  vertical-align: middle;
}

.row-open {
  background: rgba(239, 68, 68, 0.02);
}

.mono {
  font-family: monospace;
  color: #64748b;
}

.user-meta {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.sub-text {
  font-size: 0.72rem;
  color: #64748b;
}

.subject-title {
  font-weight: 600;
  color: #f1f5f9;
}

.message-preview {
  margin: 0;
  max-width: 320px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #94a3b8;
  font-size: 0.8rem;
}

.status-chip {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.2rem 0.5rem;
  border-radius: 999px;
  text-transform: uppercase;
}

.status-chip.open {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.status-chip.in_progress {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.status-chip.resolved, .status-chip.closed {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.time-text {
  font-size: 0.75rem;
  color: #64748b;
}

.btn-action {
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: #60a5fa;
  font-size: 0.76rem;
  font-weight: 500;
  padding: 0.35rem 0.75rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-action:hover {
  background: rgba(59, 130, 246, 0.25);
}

.text-right {
  text-align: right;
}

.empty-state {
  text-align: center;
  padding: 3rem 1rem;
  color: #64748b;
}

.pagination {
  padding: 0.85rem 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 0.8rem;
  color: #64748b;
}

.page-controls {
  display: flex;
  gap: 0.5rem;
}

.btn-page {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #cbd5e1;
  font-size: 0.76rem;
  padding: 0.3rem 0.65rem;
  border-radius: 4px;
  cursor: pointer;
}

.btn-page:disabled {
  opacity: 0.3;
  cursor: not-allowed;
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

.modal-card.wide {
  background: #11141e;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  width: 100%;
  max-width: 640px;
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
}

.modal-header {
  padding: 1.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.05rem;
  color: #f1f5f9;
}

.modal-sub {
  font-size: 0.76rem;
  color: #64748b;
  display: block;
  margin-top: 0.2rem;
}

.dialog-body {
  padding: 1.25rem;
}

.msg-bubble {
  background: #181d2c;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  padding: 1rem;
  margin-bottom: 1.25rem;
}

.bubble-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  font-size: 0.75rem;
  color: #94a3b8;
}

.sender-name {
  font-weight: 600;
  color: #f1f5f9;
}

.bubble-text {
  font-size: 0.88rem;
  color: #e2e8f0;
  line-height: 1.5;
  white-space: pre-wrap;
}

.status-control-strip {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.65rem 0.85rem;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  margin-bottom: 1.25rem;
}

.strip-label {
  font-size: 0.78rem;
  color: #94a3b8;
  margin-right: 0.25rem;
}

.status-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #94a3b8;
  font-size: 0.75rem;
  padding: 0.25rem 0.65rem;
  border-radius: 4px;
  cursor: pointer;
}

.status-btn.active {
  background: rgba(239, 68, 68, 0.2);
  border-color: #ef4444;
  color: #ffffff;
  font-weight: 600;
}

.form-label {
  display: block;
  font-size: 0.78rem;
  color: #94a3b8;
  margin-bottom: 0.4rem;
  font-weight: 500;
}

.form-textarea {
  width: 100%;
  background: #090a0f;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #ffffff;
  padding: 0.65rem 0.85rem;
  border-radius: 6px;
  font-size: 0.85rem;
  box-sizing: border-box;
  resize: vertical;
}

.reply-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 0.85rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  color: #94a3b8;
  cursor: pointer;
}

.btn-reply {
  background: #ef4444;
  border: none;
  color: #ffffff;
  font-weight: 600;
  font-size: 0.82rem;
  padding: 0.5rem 1.1rem;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.btn-reply:hover:not(:disabled) {
  background: #dc2626;
}

.btn-reply:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
