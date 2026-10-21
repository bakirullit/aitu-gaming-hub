<template>
  <div class="admin-page">
    <AdminNav />

    <main class="page-body">
      <!-- Welcome Banner -->
      <div class="welcome-header">
        <div>
          <h1 class="page-title">Панель управления AITU Gaming Hub</h1>
          <p class="page-subtitle">Обзор метрик, турниров, игроков и активности платформы</p>
        </div>
        <button @click="fetchData" class="btn-refresh" :disabled="loading">
          <span :class="{ 'spin-icon': loading }">🔄</span> Обновить
        </button>
      </div>

      <div v-if="loading && !stats.metrics" class="loading-state">
        <div class="spinner"></div>
        <p>Загрузка статистики...</p>
      </div>

      <div v-else class="dashboard-content">
        <!-- KPI Cards Grid -->
        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-icon">👥</div>
            <div class="kpi-data">
              <span class="kpi-label">Всего участников</span>
              <span class="kpi-value">{{ stats.metrics?.total_users || 0 }}</span>
              <span class="kpi-sub">
                🎓 {{ stats.metrics?.verified_students || 0 }} студентов / 👤 {{ stats.metrics?.guests || 0 }} гостей
              </span>
            </div>
          </div>

          <div class="kpi-card highlight-red">
            <div class="kpi-icon">🏆</div>
            <div class="kpi-data">
              <span class="kpi-label">Турниры</span>
              <span class="kpi-value">{{ stats.metrics?.total_tournaments || 0 }}</span>
              <span class="kpi-sub">
                ⏳ <strong class="text-warning">{{ stats.metrics?.pending_tournaments || 0 }} на модерации</strong> / 📅 {{ stats.metrics?.upcoming_tournaments || 0 }} активных
              </span>
            </div>
          </div>

          <div class="kpi-card">
            <div class="kpi-icon">🎫</div>
            <div class="kpi-data">
              <span class="kpi-label">Тикеты поддержки</span>
              <span class="kpi-value">{{ stats.metrics?.open_tickets || 0 }}</span>
              <span class="kpi-sub">
                В работе: {{ stats.metrics?.in_progress_tickets || 0 }}
              </span>
            </div>
          </div>

          <div class="kpi-card">
            <div class="kpi-icon">⛏️</div>
            <div class="kpi-data">
              <span class="kpi-label">Minecraft Сервер</span>
              <span class="kpi-value">{{ stats.metrics?.mc_whitelist || 0 }}</span>
              <span class="kpi-sub">
                Игроков в вайтлисте / {{ stats.metrics?.mc_sessions || 0 }} активных сессий
              </span>
            </div>
          </div>
        </div>

        <!-- Quick Action Nav Shortcuts -->
        <div class="quick-actions-bar">
          <router-link to="/admin/tournaments" class="action-chip red">
            🏆 Модерация турниров ({{ stats.metrics?.pending_tournaments || 0 }})
          </router-link>
          <router-link to="/admin/helpdesk" class="action-chip blue">
            🎫 Открытые тикеты ({{ stats.metrics?.open_tickets || 0 }})
          </router-link>
          <router-link to="/admin/minecraft" class="action-chip green">
            ⛏️ Вайтлист Minecraft
          </router-link>
          <router-link to="/admin/broadcast" class="action-chip purple">
            📢 Отправить рассылку
          </router-link>
          <router-link to="/admin/lootbox" class="action-chip gold">
            🎁 Контроль Mystery Box
          </router-link>
        </div>

        <!-- Two Column Layout: Timeline + Recent Activities -->
        <div class="dashboard-columns">
          <!-- Left: Registration Timeline -->
          <div class="panel">
            <div class="panel-header">
              <h3>📈 Динамика регистраций (за 7 дней)</h3>
            </div>
            <div class="timeline-container">
              <div v-if="stats.timeline?.length > 0" class="bar-chart">
                <div v-for="t in stats.timeline" :key="t.date" class="bar-col">
                  <div class="bar-tooltip">{{ t.count }} рег.</div>
                  <div 
                    class="bar-fill" 
                    :style="{ height: getBarHeight(t.count) }"
                  ></div>
                  <span class="bar-date">{{ formatBarDate(t.date) }}</span>
                </div>
              </div>
              <div v-else class="empty-state">
                За последние 7 дней регистраций не зафиксировано
              </div>
            </div>
          </div>

          <!-- Right: Recent Activities Feed -->
          <div class="panel">
            <div class="panel-header">
              <h3>⚡ Последние события платформы</h3>
            </div>
            <div class="activities-list">
              <div 
                v-for="(act, idx) in stats.recent_activity" 
                :key="idx" 
                class="activity-item"
              >
                <div class="activity-icon" :class="act.type">
                  <span v-if="act.type === 'user_registered'">👤</span>
                  <span v-else-if="act.type === 'ticket_opened'">🎫</span>
                  <span v-else>🏆</span>
                </div>
                <div class="activity-content">
                  <span class="activity-title">{{ act.title }}</span>
                  <span class="activity-detail">{{ act.detail }}</span>
                </div>
                <span class="activity-time">{{ formatTime(act.time) }}</span>
              </div>
              <div v-if="!stats.recent_activity?.length" class="empty-state">
                Событий пока нет
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AdminNav from '../components/AdminNav.vue'
import { dashboardApi } from '../services/api'

const loading = ref(true)
const stats = ref({ metrics: null, timeline: [], recent_activity: [] })

const fetchData = async () => {
  loading.value = true
  try {
    const res = await dashboardApi.getStats()
    stats.value = res.data || {}
  } catch (err) {
    console.error('Failed to load dashboard stats:', err)
  } finally {
    loading.value = false
  }
}

const getBarHeight = (count) => {
  if (!stats.value.timeline?.length) return '10%'
  const max = Math.max(...stats.value.timeline.map(x => x.count), 1)
  const pct = Math.max(Math.round((count / max) * 100), 12)
  return `${pct}%`
}

const formatBarDate = (dateStr) => {
  if (!dateStr) return ''
  const parts = dateStr.split('-')
  return `${parts[2]}/${parts[1]}`
}

const formatTime = (iso) => {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

onMounted(() => {
  fetchData()
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

.welcome-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
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

.btn-refresh {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  padding: 0.45rem 0.9rem;
  border-radius: 6px;
  font-size: 0.82rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-refresh:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.loading-state {
  text-align: center;
  padding: 4rem 1rem;
  color: #64748b;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: #ef4444;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.kpi-card {
  background: #11141e;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  padding: 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  transition: transform 0.15s ease, border-color 0.15s ease;
}

.kpi-card:hover {
  transform: translateY(-2px);
  border-color: rgba(255, 255, 255, 0.15);
}

.kpi-card.highlight-red {
  border-color: rgba(239, 68, 68, 0.35);
  background: linear-gradient(135deg, #11141e 0%, rgba(239, 68, 68, 0.06) 100%);
}

.kpi-icon {
  font-size: 1.75rem;
  background: rgba(255, 255, 255, 0.04);
  width: 50px;
  height: 50px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.kpi-data {
  display: flex;
  flex-direction: column;
}

.kpi-label {
  font-size: 0.78rem;
  color: #94a3b8;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.kpi-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: #ffffff;
  line-height: 1.2;
  margin: 0.2rem 0;
}

.kpi-sub {
  font-size: 0.75rem;
  color: #64748b;
}

.text-warning {
  color: #f59e0b;
}

.quick-actions-bar {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  flex-wrap: wrap;
  margin-bottom: 1.5rem;
}

.action-chip {
  font-size: 0.8rem;
  font-weight: 600;
  padding: 0.45rem 0.85rem;
  border-radius: 8px;
  text-decoration: none;
  transition: all 0.15s ease;
  border: 1px solid transparent;
}

.action-chip.red {
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.25);
}
.action-chip.red:hover {
  background: rgba(239, 68, 68, 0.2);
}

.action-chip.blue {
  background: rgba(59, 130, 246, 0.12);
  color: #3b82f6;
  border-color: rgba(59, 130, 246, 0.25);
}
.action-chip.blue:hover {
  background: rgba(59, 130, 246, 0.2);
}

.action-chip.green {
  background: rgba(34, 197, 94, 0.12);
  color: #22c55e;
  border-color: rgba(34, 197, 94, 0.25);
}
.action-chip.green:hover {
  background: rgba(34, 197, 94, 0.2);
}

.action-chip.purple {
  background: rgba(168, 85, 247, 0.12);
  color: #a855f7;
  border-color: rgba(168, 85, 247, 0.25);
}
.action-chip.purple:hover {
  background: rgba(168, 85, 247, 0.2);
}

.action-chip.gold {
  background: rgba(245, 158, 11, 0.12);
  color: #f59e0b;
  border-color: rgba(245, 158, 11, 0.25);
}
.action-chip.gold:hover {
  background: rgba(245, 158, 11, 0.2);
}

.dashboard-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

@media (max-width: 960px) {
  .dashboard-columns {
    grid-template-columns: 1fr;
  }
}

.panel {
  background: #11141e;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  overflow: hidden;
}

.panel-header {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.panel-header h3 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: #f1f5f9;
}

.timeline-container {
  padding: 1.5rem;
  min-height: 250px;
  display: flex;
  align-items: flex-end;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  width: 100%;
  height: 180px;
  gap: 0.75rem;
}

.bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  justify-content: flex-end;
  position: relative;
}

.bar-fill {
  width: 100%;
  max-width: 38px;
  background: linear-gradient(180deg, #ef4444 0%, #b91c1c 100%);
  border-radius: 5px 5px 0 0;
  transition: height 0.3s ease;
}

.bar-col:hover .bar-tooltip {
  opacity: 1;
  transform: translateY(-5px);
}

.bar-tooltip {
  position: absolute;
  top: -24px;
  background: #1e293b;
  color: #f8fafc;
  font-size: 0.7rem;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  opacity: 0;
  pointer-events: none;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.bar-date {
  font-size: 0.72rem;
  color: #64748b;
  margin-top: 0.5rem;
}

.activities-list {
  padding: 0.5rem 1rem;
}

.activity-item {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  padding: 0.75rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.activity-item:last-child {
  border-bottom: none;
}

.activity-icon {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.04);
  font-size: 1rem;
  flex-shrink: 0;
}

.activity-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.activity-title {
  font-size: 0.84rem;
  font-weight: 500;
  color: #f1f5f9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.activity-detail {
  font-size: 0.75rem;
  color: #64748b;
}

.activity-time {
  font-size: 0.72rem;
  color: #475569;
  flex-shrink: 0;
}

.empty-state {
  color: #64748b;
  font-size: 0.85rem;
  text-align: center;
  padding: 2rem 0;
  width: 100%;
}
</style>
