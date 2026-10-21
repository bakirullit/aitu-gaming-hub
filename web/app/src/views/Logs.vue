<template>
  <div class="admin-page">
    <AdminNav />

    <main class="page-body">
      <div class="header-intro">
        <h1 class="page-title">🛡️ Системный аудит и мониторинг</h1>
        <p class="page-subtitle">Проверка здоровья сервисов (Health Check) и журнал событий платформы</p>
      </div>

      <!-- Health Status Cards -->
      <div class="health-grid">
        <div class="health-card" :class="health.database?.status === 'UP' ? 'up' : 'down'">
          <div class="health-icon">🗄️</div>
          <div class="health-info">
            <span class="health-name">PostgreSQL Database</span>
            <span class="health-status">
              {{ health.database?.status === 'UP' ? '🟢 Подключено' : '🔴 Ошибка связи' }}
            </span>
            <span class="health-detail">Задержка: {{ health.database?.latency_ms || 0 }} мс</span>
          </div>
        </div>

        <div class="health-card" :class="health.redis?.status === 'UP' ? 'up' : 'down'">
          <div class="health-icon">⚡</div>
          <div class="health-info">
            <span class="health-name">Redis Cache & Locks</span>
            <span class="health-status">
              {{ health.redis?.status === 'UP' ? '🟢 Активен' : '🔴 Недоступен' }}
            </span>
            <span class="health-detail">Задержка: {{ health.redis?.latency_ms || 0 }} мс</span>
          </div>
        </div>

        <div class="health-card" :class="health.telegram_bot?.status === 'UP' ? 'up' : 'down'">
          <div class="health-icon">🤖</div>
          <div class="health-info">
            <span class="health-name">Telegram Bot</span>
            <span class="health-status">
              {{ health.telegram_bot?.status === 'UP' ? '🟢 Бот онлайн' : '🔴 Офлайн' }}
            </span>
            <span class="health-detail">@{{ health.telegram_bot?.bot_username || 'aitu_gaming_bot' }}</span>
          </div>
        </div>

        <div class="health-card up">
          <div class="health-icon">📧</div>
          <div class="health-info">
            <span class="health-name">Email Service</span>
            <span class="health-status">
              {{ health.email_service?.status === 'CONFIGURED' ? '🟢 Resend API' : '🟡 Mock Режим' }}
            </span>
            <span class="health-detail">Отправка OTP кодов</span>
          </div>
        </div>
      </div>

      <!-- Audit Logs Table -->
      <div class="panel">
        <div class="panel-header">
          <h3>📋 Журнал активности и аудита</h3>
          <button @click="fetchData" class="btn-refresh" :disabled="loading">
            <span :class="{ 'spin-icon': loading }">🔄</span> Обновить логи
          </button>
        </div>

        <div class="table-container">
          <table v-if="!loading || auditLogs.length > 0" class="minimal-table">
            <thead>
              <tr>
                <th>Уровень</th>
                <th>Модуль</th>
                <th>Событие</th>
                <th>Инициатор / Пользователь</th>
                <th>Время</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(log, idx) in auditLogs" :key="idx">
                <td>
                  <span class="level-badge" :class="log.level.toLowerCase()">
                    {{ log.level }}
                  </span>
                </td>
                <td>
                  <span class="source-tag">{{ log.source }}</span>
                </td>
                <td>
                  <span class="event-text">{{ log.event }}</span>
                </td>
                <td>
                  <span class="actor-text">{{ log.actor }}</span>
                </td>
                <td>
                  <span class="time-text">{{ formatDate(log.timestamp) }}</span>
                </td>
              </tr>
              <tr v-if="auditLogs.length === 0 && !loading">
                <td colspan="5" class="empty-state">Журнал событий пуст</td>
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
import { ref, onMounted } from 'vue'
import AdminNav from '../components/AdminNav.vue'
import { logsApi } from '../services/api'

const loading = ref(false)
const health = ref({})
const auditLogs = ref([])

const fetchData = async () => {
  loading.value = true
  try {
    const [hRes, aRes] = await Promise.all([
      logsApi.getHealth(),
      logsApi.getAudit(),
    ])
    health.value = hRes.data || {}
    auditLogs.value = aRes.data?.items || []
  } catch (err) {
    console.warn('Failed to load logs and health:', err)
  } finally {
    loading.value = false
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

.health-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.health-card {
  background: #11141e;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 1rem 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.health-card.up {
  border-left: 3px solid #22c55e;
}

.health-card.down {
  border-left: 3px solid #ef4444;
}

.health-icon {
  font-size: 1.6rem;
  background: rgba(255, 255, 255, 0.04);
  width: 44px;
  height: 44px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.health-info {
  display: flex;
  flex-direction: column;
}

.health-name {
  font-size: 0.82rem;
  font-weight: 600;
  color: #f1f5f9;
}

.health-status {
  font-size: 0.76rem;
  margin: 0.15rem 0;
}

.health-detail {
  font-size: 0.7rem;
  color: #64748b;
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
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-header h3 {
  margin: 0;
  font-size: 0.95rem;
  color: #f1f5f9;
}

.btn-refresh {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  padding: 0.4rem 0.85rem;
  border-radius: 6px;
  font-size: 0.8rem;
  cursor: pointer;
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
  padding: 0.75rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  vertical-align: middle;
}

.level-badge {
  font-size: 0.68rem;
  font-weight: 700;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
}

.level-badge.success {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.level-badge.info {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.level-badge.warn {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.source-tag {
  font-size: 0.74rem;
  font-weight: 600;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.05);
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
}

.event-text {
  color: #f1f5f9;
}

.actor-text {
  color: #94a3b8;
  font-size: 0.8rem;
}

.time-text {
  font-size: 0.75rem;
  color: #64748b;
}

.empty-state {
  text-align: center;
  padding: 3rem 1rem;
  color: #64748b;
}
</style>
