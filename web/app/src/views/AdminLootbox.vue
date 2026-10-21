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
        <h1 class="page-title">🎁 Контроль Mystery Box и Staff-ролей</h1>
        <p class="page-subtitle">Мониторинг запечатанных и раскрытых ролей сотрудников клуба</p>
      </div>

      <!-- KPI Summary -->
      <div class="kpi-grid">
        <div class="kpi-card">
          <span class="kpi-label">Всего сотрудников</span>
          <span class="kpi-num">{{ overview.total_staff || 0 }}</span>
        </div>
        <div class="kpi-card green">
          <span class="kpi-label">🎁 Раскрыли бокс</span>
          <span class="kpi-num">{{ overview.revealed_count || 0 }}</span>
        </div>
        <div class="kpi-card gold">
          <span class="kpi-label">🔒 Запечатано (не открыто)</span>
          <span class="kpi-num">{{ overview.sealed_count || 0 }}</span>
        </div>
      </div>

      <!-- Staff List -->
      <div class="panel">
        <div class="panel-header">
          <div class="tab-pills">
            <button 
              class="tab-pill" 
              :class="{ active: filter === 'all' }"
              @click="filter = 'all'"
            >
              Все ({{ overview.total_staff || 0 }})
            </button>
            <button 
              class="tab-pill" 
              :class="{ active: filter === 'sealed' }"
              @click="filter = 'sealed'"
            >
              🔒 Не открыли ({{ overview.sealed_count || 0 }})
            </button>
            <button 
              class="tab-pill" 
              :class="{ active: filter === 'revealed' }"
              @click="filter = 'revealed'"
            >
              🎁 Раскрыты ({{ overview.revealed_count || 0 }})
            </button>
          </div>
          <button @click="fetchOverview" class="btn-refresh" :disabled="loading">
            <span :class="{ 'spin-icon': loading }">🔄</span> Обновить
          </button>
        </div>

        <div class="table-container">
          <table v-if="!loading || filteredItems.length > 0" class="minimal-table">
            <thead>
              <tr>
                <th>Сотрудник</th>
                <th>Баркод / Группа</th>
                <th>Назначенная роль</th>
                <th>Дисциплина</th>
                <th>Статус Mystery Box</th>
                <th>Дата открытия</th>
                <th class="text-right">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in filteredItems" :key="s.telegram_id">
                <td>
                  <div class="user-cell">
                    <strong>{{ s.full_name }}</strong>
                    <span class="sub-text">{{ s.username ? '@' + s.username : 'ID: ' + s.telegram_id }}</span>
                  </div>
                </td>
                <td>
                  <span class="mono">{{ s.barcode || '—' }}</span>
                  <span v-if="s.academic_group" class="group-sub">· {{ s.academic_group }}</span>
                </td>
                <td>
                  <span class="role-badge">{{ s.staff_role }}</span>
                </td>
                <td>
                  <span class="disc-sub">{{ s.discipline_id || 'Все дисциплины' }}</span>
                </td>
                <td>
                  <span class="box-status" :class="s.is_role_revealed ? 'revealed' : 'sealed'">
                    {{ s.is_role_revealed ? '🎁 Раскрыт' : '🔒 Запечатан' }}
                  </span>
                </td>
                <td>
                  <span class="time-text">{{ formatDate(s.role_revealed_at) }}</span>
                </td>
                <td class="text-right">
                  <div class="action-wrap">
                    <button 
                      v-if="s.is_role_revealed"
                      @click="resealBox(s)"
                      class="btn-reseal"
                      title="Сбросить статус, чтобы пользователь мог снова открыть Mystery Box"
                    >
                      🔄 Перезапечатать
                    </button>
                    <button 
                      v-else
                      @click="revealBox(s)"
                      class="btn-reveal"
                      title="Принудительно раскрыть роль"
                    >
                      ⚡ Раскрыть
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="filteredItems.length === 0 && !loading">
                <td colspan="7" class="empty-state">Сотрудники не найдены</td>
              </tr>
            </tbody>
          </table>

          <div v-if="loading" class="loading-overlay">
            <div class="spinner"></div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import AdminNav from '../components/AdminNav.vue'
import { lootboxAdminApi } from '../services/api'

const loading = ref(false)
const overview = ref({ total_staff: 0, revealed_count: 0, sealed_count: 0, items: [] })
const filter = ref('all') // 'all' | 'sealed' | 'revealed'

const toast = ref({ message: '', type: 'info' })
const showToast = (message, type = 'info') => {
  toast.value = { message, type }
  setTimeout(() => { toast.value.message = '' }, 3500)
}

const filteredItems = computed(() => {
  if (filter.value === 'sealed') {
    return overview.value.items.filter(x => !x.is_role_revealed)
  }
  if (filter.value === 'revealed') {
    return overview.value.items.filter(x => x.is_role_revealed)
  }
  return overview.value.items
})

const fetchOverview = async () => {
  loading.value = true
  try {
    const res = await lootboxAdminApi.getOverview()
    overview.value = res.data
  } catch (err) {
    showToast('Ошибка загрузки данных лутбокса', 'error')
  } finally {
    loading.value = false
  }
}

const resealBox = async (s) => {
  try {
    await lootboxAdminApi.reseal(s.telegram_id)
    showToast(`Mystery Box для ${s.full_name} перезапечатан`, 'success')
    fetchOverview()
  } catch (err) {
    showToast('Ошибка перезапечатывания', 'error')
  }
}

const revealBox = async (s) => {
  try {
    await lootboxAdminApi.reveal(s.telegram_id)
    showToast(`Роль для ${s.full_name} раскрыта`, 'info')
    fetchOverview()
  } catch (err) {
    showToast('Ошибка раскрытия роли', 'error')
  }
}

const formatDate = (iso) => {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleString('ru-RU', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
  } catch {
    return '—'
  }
}

onMounted(() => {
  fetchOverview()
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

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.kpi-card {
  background: #11141e;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
}

.kpi-card.green {
  border-color: rgba(34, 197, 94, 0.3);
  background: linear-gradient(135deg, #11141e 0%, rgba(34, 197, 94, 0.05) 100%);
}

.kpi-card.gold {
  border-color: rgba(245, 158, 11, 0.3);
  background: linear-gradient(135deg, #11141e 0%, rgba(245, 158, 11, 0.05) 100%);
}

.kpi-label {
  font-size: 0.78rem;
  color: #94a3b8;
  font-weight: 500;
}

.kpi-num {
  font-size: 1.8rem;
  font-weight: 700;
  color: #ffffff;
  margin-top: 0.25rem;
}

.panel {
  background: #11141e;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
  overflow: hidden;
}

.panel-header {
  padding: 0.85rem 1.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  justify-content: space-between;
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
  padding: 0.4rem 0.85rem;
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

.btn-refresh {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  padding: 0.4rem 0.75rem;
  border-radius: 6px;
  font-size: 0.8rem;
  cursor: pointer;
}

.table-container {
  overflow-x: auto;
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
  font-size: 0.72rem;
  text-transform: uppercase;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.minimal-table td {
  padding: 0.85rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  vertical-align: middle;
}

.user-cell {
  display: flex;
  flex-direction: column;
}

.sub-text {
  font-size: 0.72rem;
  color: #64748b;
}

.mono {
  font-family: monospace;
  color: #94a3b8;
}

.group-sub {
  font-size: 0.75rem;
  color: #64748b;
}

.role-badge {
  font-size: 0.76rem;
  font-weight: 600;
  color: #f1f5f9;
  background: rgba(255, 255, 255, 0.06);
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
}

.disc-sub {
  font-size: 0.76rem;
  color: #94a3b8;
}

.box-status {
  font-size: 0.74rem;
  font-weight: 600;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
}

.box-status.revealed {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.box-status.sealed {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.time-text {
  font-size: 0.75rem;
  color: #64748b;
}

.action-wrap {
  display: inline-flex;
  gap: 0.4rem;
}

.btn-reseal {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  font-size: 0.72rem;
  padding: 0.25rem 0.55rem;
  border-radius: 4px;
  cursor: pointer;
}

.btn-reseal:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.btn-reveal {
  background: rgba(245, 158, 11, 0.15);
  border: 1px solid rgba(245, 158, 11, 0.3);
  color: #f59e0b;
  font-size: 0.72rem;
  padding: 0.25rem 0.55rem;
  border-radius: 4px;
  cursor: pointer;
}

.btn-reveal:hover {
  background: rgba(245, 158, 11, 0.25);
}

.text-right {
  text-align: right;
}

.empty-state {
  text-align: center;
  padding: 3rem 1rem;
  color: #64748b;
}
</style>
