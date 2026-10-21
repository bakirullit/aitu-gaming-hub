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
      <!-- Top Metrics & Server Status Card -->
      <div class="server-status-card">
        <div class="status-main">
          <div class="server-icon">⛏️</div>
          <div class="server-info">
            <div class="server-title-row">
              <h2>AITU Minecraft Network</h2>
              <span class="status-indicator" :class="serverStatus?.rcon_online ? 'online' : 'offline'">
                {{ serverStatus?.rcon_online ? '🟢 RCON Online' : '🔴 RCON Offline' }}
              </span>
            </div>
            <p class="server-host">
              <code>{{ serverStatus?.server_host }}</code> · Версия: <strong>{{ serverStatus?.server_version }}</strong>
            </p>
          </div>
        </div>

        <div class="status-stats">
          <div class="stat-box">
            <span class="stat-num">{{ serverStatus?.players_online || 0 }} / {{ serverStatus?.max_players || 50 }}</span>
            <span class="stat-lbl">Игроков онлайн</span>
          </div>
          <div class="stat-box">
            <span class="stat-num">{{ serverStatus?.whitelist_count || 0 }}</span>
            <span class="stat-lbl">В вайтлисте</span>
          </div>
          <div class="stat-box">
            <span class="stat-num">{{ serverStatus?.active_sessions_count || 0 }}</span>
            <span class="stat-lbl">Активных сессий</span>
          </div>
        </div>
      </div>

      <!-- Two-Panel Grid: Whitelist on Left, RCON Console on Right -->
      <div class="minecraft-grid">
        <!-- Left: Whitelist Table -->
        <div class="panel">
          <div class="panel-header">
            <div class="header-title-wrap">
              <h3>👥 Игровой вайтлист</h3>
              <span class="badge">{{ total }} игроков</span>
            </div>
            <div class="header-actions">
              <input 
                v-model="searchQuery" 
                @input="debounceSearch"
                type="text" 
                placeholder="Поиск ника / баркода..." 
                class="search-mini"
              />
              <button @click="showAddModal = true" class="btn-primary-mini">
                + Добавить ник
              </button>
            </div>
          </div>

          <div class="table-wrap">
            <table v-if="!loading || whitelist.length > 0" class="mini-table">
              <thead>
                <tr>
                  <th>Никнейм</th>
                  <th>Студент AITU</th>
                  <th>Группа</th>
                  <th class="text-right">Действия</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="w in whitelist" :key="w.id">
                  <td>
                    <span class="player-nick">{{ w.nickname }}</span>
                  </td>
                  <td>
                    <div class="student-col">
                      <span>{{ w.student_name || 'Не привязан' }}</span>
                      <span v-if="w.barcode" class="barcode-sub">{{ w.barcode }}</span>
                    </div>
                  </td>
                  <td>
                    <span class="group-tag">{{ w.academic_group || '—' }}</span>
                  </td>
                  <td class="text-right">
                    <button @click="deleteWhitelist(w)" class="btn-kick" title="Удалить из вайтлиста">
                      ✕ Исключить
                    </button>
                  </td>
                </tr>
                <tr v-if="whitelist.length === 0 && !loading">
                  <td colspan="4" class="empty-state">Игроков не найдено</td>
                </tr>
              </tbody>
            </table>

            <div v-if="loading" class="loading-overlay">
              <div class="spinner"></div>
            </div>
          </div>

          <div class="pagination">
            <span class="page-info">Всего: {{ total }}</span>
            <div class="page-controls">
              <button @click="prevPage" :disabled="offset === 0" class="btn-page">◀</button>
              <button @click="nextPage" :disabled="offset + limit >= total" class="btn-page">▶</button>
            </div>
          </div>
        </div>

        <!-- Right: Interactive RCON Terminal -->
        <div class="panel">
          <div class="panel-header">
            <h3>⚡ Веб-консоль RCON</h3>
            <div class="quick-rcon-btns">
              <button @click="runRcon('list')" class="btn-rcon-chip">list</button>
              <button @click="runRcon('whitelist reload')" class="btn-rcon-chip">whitelist reload</button>
              <button @click="runRcon('tps')" class="btn-rcon-chip">tps</button>
            </div>
          </div>

          <div class="terminal-body" ref="terminalBody">
            <div class="terminal-welcome">
              [SYSTEM] AITU Gaming Hub RCON CLI connected to {{ serverStatus?.server_host }}
              <br/>[READY] Введите команду Minecraft (например: whitelist list, say Внимание, kick Player)
            </div>
            <div v-for="(log, idx) in rconLogs" :key="idx" class="terminal-line" :class="log.type">
              <span class="term-time">[{{ log.time }}]</span>
              <span class="term-prefix">{{ log.type === 'cmd' ? '> /' : '< ' }}</span>
              <span class="term-text">{{ log.text }}</span>
            </div>
          </div>

          <form @submit.prevent="submitRcon" class="terminal-input-bar">
            <span class="prompt-symbol">/</span>
            <input 
              v-model="rconCommand" 
              type="text" 
              placeholder="Введите RCON команду..." 
              class="terminal-input"
              :disabled="executingRcon"
            />
            <button type="submit" :disabled="executingRcon || !rconCommand.trim()" class="btn-exec">
              {{ executingRcon ? '...' : 'Выполнить' }}
            </button>
          </form>
        </div>
      </div>
    </main>

    <!-- Add Whitelist Modal -->
    <div v-if="showAddModal" class="modal-backdrop" @click.self="showAddModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3>Добавить игрока в вайтлист</h3>
          <button @click="showAddModal = false" class="btn-close">✕</button>
        </div>
        <form @submit.prevent="addWhitelist" class="modal-form">
          <div class="form-group">
            <label>Игровой ник Minecraft (Java / Create) *</label>
            <input v-model="addForm.nickname" required placeholder="Notch" class="form-input" />
          </div>
          <div class="form-group">
            <label>Баркод студента AITU (опционально, 6 цифр)</label>
            <input v-model="addForm.barcode" placeholder="230101" class="form-input" />
          </div>
          <div class="modal-actions">
            <button type="button" @click="showAddModal = false" class="btn-cancel">Отмена</button>
            <button type="submit" :disabled="adding" class="btn-submit">
              {{ adding ? 'Добавление...' : 'Добавить в вайтлист' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import AdminNav from '../components/AdminNav.vue'
import { minecraftAdminApi } from '../services/api'

const loading = ref(false)
const serverStatus = ref(null)
const whitelist = ref([])
const total = ref(0)
const limit = ref(25)
const offset = ref(0)
const searchQuery = ref('')

const showAddModal = ref(false)
const adding = ref(false)
const addForm = ref({ nickname: '', barcode: '' })

const rconCommand = ref('')
const executingRcon = ref(false)
const rconLogs = ref([])
const terminalBody = ref(null)

const toast = ref({ message: '', type: 'info' })
const showToast = (message, type = 'info') => {
  toast.value = { message, type }
  setTimeout(() => { toast.value.message = '' }, 3500)
}

let searchTimeout = null

const fetchStatus = async () => {
  try {
    const res = await minecraftAdminApi.getStatus()
    serverStatus.value = res.data
  } catch (err) {
    console.warn('Could not fetch server status:', err)
  }
}

const fetchWhitelist = async () => {
  loading.value = true
  try {
    const res = await minecraftAdminApi.getWhitelist({
      query: searchQuery.value || undefined,
      limit: limit.value,
      offset: offset.value,
    })
    whitelist.value = res.data.items || []
    total.value = res.data.total || 0
  } catch (err) {
    showToast('Ошибка загрузки вайтлиста', 'error')
  } finally {
    loading.value = false
  }
}

const debounceSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    offset.value = 0
    fetchWhitelist()
  }, 300)
}

const prevPage = () => {
  if (offset.value >= limit.value) {
    offset.value -= limit.value
    fetchWhitelist()
  }
}

const nextPage = () => {
  if (offset.value + limit.value < total.value) {
    offset.value += limit.value
    fetchWhitelist()
  }
}

const addWhitelist = async () => {
  adding.value = true
  try {
    await minecraftAdminApi.addWhitelist(addForm.value)
    showToast(`Ник «${addForm.value.nickname}» добавлен в вайтлист!`, 'success')
    showAddModal.value = false
    addForm.value = { nickname: '', barcode: '' }
    fetchWhitelist()
    fetchStatus()
  } catch (err) {
    showToast(err.response?.data?.detail || 'Ошибка добавления в вайтлист', 'error')
  } finally {
    adding.value = false
  }
}

const deleteWhitelist = async (w) => {
  if (!confirm(`Удалить игрока «${w.nickname}» из вайтлиста?`)) return
  try {
    await minecraftAdminApi.removeWhitelist(w.id)
    showToast(`Игрок «${w.nickname}» исключен из вайтлиста`, 'info')
    fetchWhitelist()
    fetchStatus()
  } catch (err) {
    showToast(err.response?.data?.detail || 'Ошибка удаления из вайтлиста', 'error')
  }
}

const runRcon = async (cmd) => {
  rconCommand.value = cmd
  await submitRcon()
}

const submitRcon = async () => {
  const cmd = rconCommand.value.trim()
  if (!cmd) return

  const now = new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  rconLogs.value.push({ type: 'cmd', text: cmd, time: now })
  rconCommand.value = ''
  executingRcon.value = true

  try {
    const res = await minecraftAdminApi.executeRcon(cmd)
    rconLogs.value.push({ type: 'res', text: res.data.response, time: now })
  } catch (err) {
    rconLogs.value.push({
      type: 'err',
      text: err.response?.data?.detail || 'RCON ошибка выполнения',
      time: now,
    })
  } finally {
    executingRcon.value = false
    await nextTick()
    if (terminalBody.value) {
      terminalBody.value.scrollTop = terminalBody.value.scrollHeight
    }
  }
}

onMounted(() => {
  fetchStatus()
  fetchWhitelist()
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

.server-status-card {
  background: #11141e;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.status-main {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.server-icon {
  font-size: 2rem;
  background: rgba(34, 197, 94, 0.1);
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.server-info h2 {
  margin: 0;
  font-size: 1.15rem;
  color: #f1f5f9;
}

.server-title-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.status-indicator {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
}

.status-indicator.online {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.status-indicator.offline {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.server-host {
  margin: 0.25rem 0 0;
  font-size: 0.8rem;
  color: #94a3b8;
}

.server-host code {
  color: #22c55e;
}

.status-stats {
  display: flex;
  gap: 1.5rem;
}

.stat-box {
  display: flex;
  flex-direction: column;
  text-align: right;
}

.stat-num {
  font-size: 1.35rem;
  font-weight: 700;
  color: #ffffff;
}

.stat-lbl {
  font-size: 0.72rem;
  color: #64748b;
  text-transform: uppercase;
}

.minecraft-grid {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 1.5rem;
}

@media (max-width: 1024px) {
  .minecraft-grid {
    grid-template-columns: 1fr;
  }
}

.panel {
  background: #11141e;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.panel-header {
  padding: 0.85rem 1.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.header-title-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.header-title-wrap h3 {
  margin: 0;
  font-size: 0.95rem;
  color: #f1f5f9;
}

.badge {
  font-size: 0.72rem;
  background: rgba(255, 255, 255, 0.08);
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  color: #94a3b8;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.search-mini {
  background: #090a0f;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #f1f5f9;
  font-size: 0.78rem;
  padding: 0.35rem 0.65rem;
  border-radius: 6px;
  width: 170px;
}

.btn-primary-mini {
  background: #22c55e;
  border: none;
  color: #ffffff;
  font-weight: 600;
  font-size: 0.78rem;
  padding: 0.4rem 0.8rem;
  border-radius: 6px;
  cursor: pointer;
}

.table-wrap {
  position: relative;
  min-height: 250px;
  flex: 1;
}

.mini-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}

.mini-table th {
  background: rgba(255, 255, 255, 0.02);
  color: #64748b;
  font-size: 0.7rem;
  text-transform: uppercase;
  padding: 0.65rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  text-align: left;
}

.mini-table td {
  padding: 0.65rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  vertical-align: middle;
}

.player-nick {
  font-weight: 700;
  color: #22c55e;
  font-family: monospace;
}

.student-col {
  display: flex;
  flex-direction: column;
}

.barcode-sub {
  font-size: 0.7rem;
  color: #64748b;
  font-family: monospace;
}

.group-tag {
  font-size: 0.72rem;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.04);
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
}

.btn-kick {
  background: transparent;
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #ef4444;
  font-size: 0.72rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
}

.btn-kick:hover {
  background: rgba(239, 68, 68, 0.15);
}

.quick-rcon-btns {
  display: flex;
  gap: 0.35rem;
}

.btn-rcon-chip {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  font-size: 0.72rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
  font-family: monospace;
}

.btn-rcon-chip:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #22c55e;
}

.terminal-body {
  background: #06080d;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.78rem;
  padding: 1rem;
  height: 380px;
  overflow-y: auto;
  color: #cbd5e1;
}

.terminal-welcome {
  color: #64748b;
  margin-bottom: 0.75rem;
  line-height: 1.4;
}

.terminal-line {
  margin-bottom: 0.35rem;
  line-height: 1.4;
  word-break: break-all;
}

.terminal-line.cmd {
  color: #38bdf8;
}

.terminal-line.res {
  color: #22c55e;
}

.terminal-line.err {
  color: #ef4444;
}

.term-time {
  color: #475569;
  margin-right: 0.4rem;
}

.terminal-input-bar {
  display: flex;
  align-items: center;
  background: #0b0f17;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding: 0.5rem 0.75rem;
  gap: 0.4rem;
}

.prompt-symbol {
  color: #22c55e;
  font-family: monospace;
  font-weight: 700;
  font-size: 0.9rem;
}

.terminal-input {
  flex: 1;
  background: transparent;
  border: none;
  color: #ffffff;
  font-family: monospace;
  font-size: 0.82rem;
  outline: none;
}

.btn-exec {
  background: #22c55e;
  border: none;
  color: #ffffff;
  font-weight: 600;
  font-size: 0.76rem;
  padding: 0.35rem 0.85rem;
  border-radius: 4px;
  cursor: pointer;
}

.btn-exec:disabled {
  opacity: 0.4;
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
  max-width: 460px;
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

.modal-form {
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

.form-input {
  width: 100%;
  background: #090a0f;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #ffffff;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
  box-sizing: border-box;
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
  background: #22c55e;
  border: none;
  color: #ffffff;
  font-weight: 600;
  padding: 0.45rem 1rem;
  border-radius: 6px;
  cursor: pointer;
}

.pagination {
  padding: 0.65rem 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 0.78rem;
  color: #64748b;
}

.page-controls {
  display: flex;
  gap: 0.4rem;
}

.btn-page {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #cbd5e1;
  font-size: 0.72rem;
  padding: 0.25rem 0.55rem;
  border-radius: 4px;
  cursor: pointer;
}
</style>
