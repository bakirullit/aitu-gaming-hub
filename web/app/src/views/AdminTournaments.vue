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
              :class="{ active: currentTab === 'pending' }"
              @click="switchTab('pending')"
            >
              ⏳ На модерации 
              <span v-if="pendingCount > 0" class="pill-count warning">{{ pendingCount }}</span>
            </button>
            <button 
              class="tab-pill" 
              :class="{ active: currentTab === 'approved' }"
              @click="switchTab('approved')"
            >
              🟢 Утвержденные ({{ approvedCount }})
            </button>
            <button 
              class="tab-pill" 
              :class="{ active: currentTab === 'all' }"
              @click="switchTab('all')"
            >
              Все турниры ({{ total }})
            </button>
          </div>
        </div>

        <div class="toolbar-right">
          <div class="search-wrap">
            <input 
              v-model="searchQuery" 
              @input="debounceSearch"
              type="text" 
              placeholder="Поиск по названию или формату..." 
              class="search-input"
            />
          </div>
          <button @click="openCreateModal" class="btn-primary">
            + Создать турнир
          </button>
        </div>
      </div>

      <!-- Tournaments Table -->
      <div class="table-container">
        <table v-if="!loading || tournaments.length > 0" class="minimal-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Турнир</th>
              <th>Дисциплина</th>
              <th>Дата проведения</th>
              <th>Формат</th>
              <th>Организатор</th>
              <th>Статус</th>
              <th class="text-right">Действия</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in tournaments" :key="t.id">
              <td class="mono">#{{ t.id }}</td>
              <td>
                <div class="tournament-title-col">
                  <strong>{{ t.title }}</strong>
                  <a v-if="t.rulebook_url" :href="t.rulebook_url" target="_blank" class="rulebook-link">
                    📄 Регламент
                  </a>
                </div>
              </td>
              <td>
                <span class="discipline-tag">{{ (t.discipline || '').toUpperCase() }}</span>
              </td>
              <td>
                <span class="date-badge">{{ t.booking_date }}</span>
              </td>
              <td>
                <span class="format-badge">{{ t.format_label || t.event_format }}</span>
              </td>
              <td>
                <span class="creator-name">{{ t.creator_name || '—' }}</span>
              </td>
              <td>
                <span class="status-chip" :class="t.status.toLowerCase()">
                  {{ t.status }}
                </span>
              </td>
              <td class="text-right">
                <div class="action-buttons">
                  <button 
                    v-if="t.status.toUpperCase() === 'PENDING'"
                    @click="approveSlot(t)"
                    class="btn-approve"
                    title="Одобрить слот"
                  >
                    ✅ Одобрить
                  </button>
                  <button 
                    v-if="t.status.toUpperCase() === 'PENDING'"
                    @click="openRejectModal(t)"
                    class="btn-reject"
                    title="Отклонить слот"
                  >
                    ❌ Отклонить
                  </button>
                  <button 
                    @click="deleteTournament(t)"
                    class="btn-delete"
                    title="Удалить"
                  >
                    🗑️
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="tournaments.length === 0 && !loading">
              <td colspan="8" class="empty-state">
                {{ currentTab === 'pending' ? 'Нет ожидающих заявок на турниры 🎉' : 'Турниры не найдены' }}
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="loading" class="loading-overlay">
          <div class="spinner"></div>
        </div>

        <div class="pagination">
          <span class="page-info">Показано {{ tournaments.length }} из {{ total }}</span>
          <div class="page-controls">
            <button @click="prevPage" :disabled="offset === 0" class="btn-page">◀ Назад</button>
            <button @click="nextPage" :disabled="offset + limit >= total" class="btn-page">Вперед ▶</button>
          </div>
        </div>
      </div>
    </main>

    <!-- Create Tournament Modal -->
    <div v-if="showCreateModal" class="modal-backdrop" @click.self="showCreateModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3>Создать турнир</h3>
          <button @click="showCreateModal = false" class="btn-close">✕</button>
        </div>
        <form @submit.prevent="createTournament" class="modal-form">
          <div class="form-group">
            <label>Название турнира *</label>
            <input v-model="form.title" required placeholder="AITU Autumn Cup CS2 5v5" class="form-input" />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>Дисциплина *</label>
              <select v-model="form.discipline" class="form-input">
                <option value="cs2">Counter-Strike 2</option>
                <option value="dota2">Dota 2</option>
                <option value="valorant">Valorant</option>
                <option value="pubg_mobile">PUBG Mobile</option>
                <option value="mobile_legends">Mobile Legends</option>
                <option value="fifa">EA FC (FIFA)</option>
                <option value="chess">Шахматы</option>
              </select>
            </div>
            <div class="form-group">
              <label>Дата проведения *</label>
              <input v-model="form.booking_date" type="date" required class="form-input" />
            </div>
          </div>

          <div class="form-group">
            <label>Формат турнира</label>
            <select v-model="form.event_format" class="form-input">
              <option value="online_single_elim_5x5">Single Elimination 5v5 (Online)</option>
              <option value="online_single_elim_2x2">Single Elimination 2v2 (Online)</option>
              <option value="lan_single_elim_5x5">LAN Single Elimination 5v5</option>
              <option value="online_swiss_5x5">Swiss System 5v5 (Online)</option>
              <option value="lan_1v1">LAN 1v1</option>
            </select>
          </div>

          <div class="form-group">
            <label>Ссылка на регламент (Rulebook)</label>
            <input v-model="form.rulebook_url" type="url" placeholder="https://docs.google.com/..." class="form-input" />
          </div>

          <div class="modal-actions">
            <button type="button" @click="showCreateModal = false" class="btn-cancel">Отмена</button>
            <button type="submit" :disabled="saving" class="btn-submit">
              {{ saving ? 'Сохранение...' : 'Создать турнир' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Reject Reason Modal -->
    <div v-if="rejectDialog.show" class="modal-backdrop" @click.self="rejectDialog.show = false">
      <div class="modal-card mini">
        <div class="modal-header">
          <h3>Отклонить слот турнира</h3>
          <button @click="rejectDialog.show = false" class="btn-close">✕</button>
        </div>
        <div class="modal-body">
          <p>Укажите причину отклонения слота для <strong>«{{ rejectDialog.target?.title }}»</strong>:</p>
          <textarea v-model="rejectDialog.reason" class="form-textarea" placeholder="На эту дату запланировано другое мероприятие..."></textarea>
        </div>
        <div class="modal-actions">
          <button @click="rejectDialog.show = false" class="btn-cancel">Отмена</button>
          <button @click="executeReject" class="btn-danger">Отклонить заявку</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AdminNav from '../components/AdminNav.vue'
import { tournamentAdminApi } from '../services/api'

const loading = ref(false)
const tournaments = ref([])
const total = ref(0)
const pendingCount = ref(0)
const approvedCount = ref(0)
const limit = ref(25)
const offset = ref(0)
const searchQuery = ref('')
const currentTab = ref('pending') // 'pending' | 'approved' | 'all'

const toast = ref({ message: '', type: 'info' })
const showToast = (message, type = 'info') => {
  toast.value = { message, type }
  setTimeout(() => { toast.value.message = '' }, 3500)
}

const showCreateModal = ref(false)
const saving = ref(false)
const form = ref({
  title: '',
  discipline: 'cs2',
  booking_date: new Date().toISOString().split('T')[0],
  event_format: 'online_single_elim_5x5',
  rulebook_url: '',
  status: 'approved',
})

const rejectDialog = ref({
  show: false,
  target: null,
  reason: '',
})

let searchTimeout = null

const fetchTournaments = async () => {
  loading.value = true
  try {
    const statusParam = currentTab.value === 'all' ? undefined : currentTab.value
    const res = await tournamentAdminApi.getTournaments({
      status: statusParam,
      query: searchQuery.value || undefined,
      limit: limit.value,
      offset: offset.value,
    })
    tournaments.value = res.data.items || []
    total.value = res.data.total || 0
    pendingCount.value = res.data.pending_count || 0
    approvedCount.value = res.data.approved_count || 0
  } catch (err) {
    showToast('Ошибка загрузки турниров', 'error')
  } finally {
    loading.value = false
  }
}

const switchTab = (tab) => {
  currentTab.value = tab
  offset.value = 0
  fetchTournaments()
}

const debounceSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    offset.value = 0
    fetchTournaments()
  }, 300)
}

const prevPage = () => {
  if (offset.value >= limit.value) {
    offset.value -= limit.value
    fetchTournaments()
  }
}

const nextPage = () => {
  if (offset.value + limit.value < total.value) {
    offset.value += limit.value
    fetchTournaments()
  }
}

const openCreateModal = () => {
  form.value = {
    title: '',
    discipline: 'cs2',
    booking_date: new Date().toISOString().split('T')[0],
    event_format: 'online_single_elim_5x5',
    rulebook_url: '',
    status: 'approved',
  }
  showCreateModal.value = true
}

const createTournament = async () => {
  saving.value = true
  try {
    await tournamentAdminApi.createTournament(form.value)
    showToast('Турнир успешно создан!', 'success')
    showCreateModal.value = false
    fetchTournaments()
  } catch (err) {
    showToast(err.response?.data?.detail || 'Ошибка создания турнира', 'error')
  } finally {
    saving.value = false
  }
}

const approveSlot = async (t) => {
  try {
    await tournamentAdminApi.approveTournament(t.id)
    showToast(`Слот #${t.id} «${t.title}» утвержден!`, 'success')
    fetchTournaments()
  } catch (err) {
    showToast(err.response?.data?.detail || 'Ошибка утверждения слота', 'error')
  }
}

const openRejectModal = (t) => {
  rejectDialog.value = {
    show: true,
    target: t,
    reason: 'Дата занята или формат не согласован с расписанием клуба',
  }
}

const executeReject = async () => {
  if (!rejectDialog.value.target) return
  try {
    await tournamentAdminApi.rejectTournament(rejectDialog.value.target.id, rejectDialog.value.reason)
    showToast(`Заявка #${rejectDialog.value.target.id} отклонена`, 'info')
    rejectDialog.value.show = false
    fetchTournaments()
  } catch (err) {
    showToast(err.response?.data?.detail || 'Ошибка отклонения заявки', 'error')
  }
}

const deleteTournament = async (t) => {
  if (!confirm(`Удалить турнир «${t.title}»?`)) return
  try {
    await tournamentAdminApi.deleteTournament(t.id)
    showToast('Турнир удален', 'info')
    fetchTournaments()
  } catch (err) {
    showToast('Ошибка удаления турнира', 'error')
  }
}

onMounted(() => {
  fetchTournaments()
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
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  transition: all 0.15s ease;
}

.tab-pill.active {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.35);
  color: #ffffff;
  font-weight: 600;
}

.pill-count {
  font-size: 0.72rem;
  background: rgba(255, 255, 255, 0.1);
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
}

.pill-count.warning {
  background: #f59e0b;
  color: #000000;
  font-weight: 700;
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
  width: 260px;
}

.btn-primary {
  background: #ef4444;
  border: none;
  color: #ffffff;
  font-weight: 600;
  font-size: 0.82rem;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.btn-primary:hover {
  background: #dc2626;
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

.mono {
  font-family: monospace;
  color: #64748b;
}

.tournament-title-col {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.rulebook-link {
  font-size: 0.74rem;
  color: #3b82f6;
  text-decoration: none;
}

.rulebook-link:hover {
  text-decoration: underline;
}

.discipline-tag {
  font-size: 0.75rem;
  font-weight: 700;
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
}

.date-badge {
  color: #cbd5e1;
  font-family: monospace;
}

.format-badge {
  font-size: 0.75rem;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.04);
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
}

.creator-name {
  color: #94a3b8;
  font-size: 0.82rem;
}

.status-chip {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.2rem 0.5rem;
  border-radius: 999px;
  text-transform: uppercase;
}

.status-chip.approved {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.status-chip.pending {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.status-chip.rejected, .status-chip.cancelled {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.action-buttons {
  display: inline-flex;
  gap: 0.4rem;
}

.btn-approve {
  background: rgba(34, 197, 94, 0.15);
  border: 1px solid rgba(34, 197, 94, 0.3);
  color: #22c55e;
  font-size: 0.74rem;
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
  cursor: pointer;
}

.btn-reject {
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #ef4444;
  font-size: 0.74rem;
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
  cursor: pointer;
}

.btn-delete {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #94a3b8;
  padding: 0.3rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
}

.btn-delete:hover {
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.3);
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

/* Modals */
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

.modal-card {
  background: #11141e;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  width: 100%;
  max-width: 520px;
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
}

.modal-card.mini {
  max-width: 440px;
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

.btn-close {
  background: transparent;
  border: none;
  color: #64748b;
  cursor: pointer;
  font-size: 1rem;
}

.modal-form, .modal-body {
  padding: 1.25rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  font-size: 0.76rem;
  color: #94a3b8;
  margin-bottom: 0.35rem;
  font-weight: 500;
}

.form-input, .form-textarea {
  width: 100%;
  background: #090a0f;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #ffffff;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
  box-sizing: border-box;
}

.form-textarea {
  min-height: 80px;
  resize: vertical;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.65rem;
  margin-top: 1.25rem;
}

.btn-cancel {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #94a3b8;
  padding: 0.45rem 0.85rem;
  border-radius: 6px;
  cursor: pointer;
}

.btn-submit {
  background: #ef4444;
  border: none;
  color: #ffffff;
  font-weight: 600;
  padding: 0.45rem 1rem;
  border-radius: 6px;
  cursor: pointer;
}

.btn-danger {
  background: #dc2626;
  border: none;
  color: #ffffff;
  font-weight: 600;
  padding: 0.45rem 1rem;
  border-radius: 6px;
  cursor: pointer;
}

/* Toast */
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
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
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
