<template>
  <div class="admin-container">
    <div class="glass-header">
      <div class="header-left">
        <div class="logo">
          <span class="icon">🕹️</span>
          <h1>AITU Gaming Hub <span class="badge">Admin</span></h1>
        </div>
        <nav class="nav-tabs">
          <router-link to="/tournaments" class="tab-link">🏆 Tournaments</router-link>
          <router-link to="/admin" class="tab-link">👥 Members</router-link>
          <router-link to="/admin/disciplines" class="tab-link active">🎮 Disciplines</router-link>
        </nav>
      </div>
      <div class="user-menu">
        <span class="username">{{ currentUser?.first_name || 'Admin' }}</span>
        <button @click="logout" class="btn-logout">Logout</button>
      </div>
    </div>

    <!-- Toast Notification Banner -->
    <transition name="fade">
      <div v-if="toast.message" class="toast-banner" :class="toast.type">
        <span>{{ toast.message }}</span>
        <button @click="toast.message = ''" class="toast-close">×</button>
      </div>
    </transition>

    <div class="glass-panel main-content">
      <div class="toolbar">
        <div class="toolbar-title">
          <h2>Disciplines Management</h2>
          <span class="counter-badge">{{ disciplines.length }} Directions</span>
        </div>
        <div class="toolbar-actions">
          <div class="search-box">
            <span class="search-icon">🔍</span>
            <input 
              v-model="searchQuery" 
              type="text" 
              placeholder="Filter disciplines..." 
            />
          </div>
          <button @click="openCreateModal" class="btn-primary">
            ➕ New Discipline
          </button>
        </div>
      </div>

      <div class="table-wrapper">
        <table v-if="!loading || disciplines.length > 0">
          <thead>
            <tr>
              <th>Slug</th>
              <th>Discipline</th>
              <th>Tier</th>
              <th>Curator (Admin)</th>
              <th>Community Chat</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in filteredDisciplines" :key="item.slug">
              <td class="mono font-bold">{{ item.slug }}</td>
              <td>
                <div class="name-cell">
                  <strong>{{ item.name }}</strong>
                  <span class="sub-text">{{ truncate(item.description, 45) }}</span>
                </div>
              </td>
              <td>
                <span class="tier-badge" :class="item.tier">
                  {{ item.tier === 'major' ? '🔥 Major' : '⚡ Medium' }}
                </span>
              </td>
              <td>
                <div v-if="item.admin" class="curator-info">
                  <span class="curator-name">
                    {{ item.admin.first_name }} {{ item.admin.last_name || '' }}
                  </span>
                  <span class="sub-text">
                    {{ item.admin.username ? '@' + item.admin.username : 'ID: ' + item.admin.telegram_id }}
                  </span>
                </div>
                <span v-else class="curator-unassigned">Unassigned</span>
              </td>
              <td>
                <a :href="item.chat_url" target="_blank" rel="noopener" class="chat-link">
                  💬 Open Chat ↗
                </a>
              </td>
              <td>
                <span class="status-badge" :class="item.is_active ? 'verified' : 'pending'">
                  {{ item.is_active ? 'Active' : 'Inactive' }}
                </span>
              </td>
              <td class="actions">
                <button 
                  @click="openEditModal(item)" 
                  class="btn-icon btn-edit"
                  title="Edit Discipline & Curator"
                >
                  ✏️
                </button>
                <button 
                  @click="deactivateDiscipline(item)" 
                  class="btn-icon btn-danger"
                  title="Deactivate Discipline"
                  :disabled="!item.is_active"
                >
                  🛑
                </button>
              </td>
            </tr>
            <tr v-if="filteredDisciplines.length === 0 && !loading">
              <td colspan="7" class="empty-state">No disciplines found.</td>
            </tr>
          </tbody>
        </table>

        <div v-if="loading" class="loading-overlay">
          <div class="spinner"></div>
        </div>
      </div>
    </div>

    <!-- Modal Dialog: Create / Edit Discipline -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content glass-panel">
        <div class="modal-header">
          <h3>{{ isEditing ? 'Edit Discipline: ' + form.name : 'Create New Discipline' }}</h3>
          <button @click="closeModal" class="modal-close">×</button>
        </div>

        <form @submit.prevent="saveDiscipline" class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>Slug (URL key):</label>
              <input 
                v-model="form.slug" 
                type="text" 
                required 
                placeholder="e.g. cs2, valorant, pubg"
                :disabled="isEditing"
                class="form-input mono"
              />
            </div>
            <div class="form-group">
              <label>Display Name:</label>
              <input 
                v-model="form.name" 
                type="text" 
                required 
                placeholder="e.g. Counter-Strike 2"
                class="form-input"
              />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>Tier (Community scale):</label>
              <select v-model="form.tier" class="form-input">
                <option value="major">Major (>200 players)</option>
                <option value="medium">Medium (50-200 players)</option>
              </select>
            </div>
            <div class="form-group">
              <label>Telegram Chat / Community URL:</label>
              <input 
                v-model="form.chat_url" 
                type="url" 
                required 
                placeholder="https://t.me/aitu_..."
                class="form-input"
              />
            </div>
          </div>

          <div class="form-group">
            <label>Description:</label>
            <textarea 
              v-model="form.description" 
              rows="3" 
              required 
              placeholder="Short description displayed in Telegram Bot card..."
              class="form-input"
            ></textarea>
          </div>

          <!-- Curator Search & Assignment -->
          <div class="form-group">
            <label>Assigned Curator (Discipline Admin):</label>
            <div class="curator-picker">
              <select v-model="form.admin_id" class="form-input">
                <option :value="null">-- No Curator (Unassigned) --</option>
                <option 
                  v-for="u in eligibleUsers" 
                  :key="u.telegram_id" 
                  :value="u.telegram_id"
                >
                  {{ u.first_name }} {{ u.last_name || '' }} ({{ u.username ? '@' + u.username : u.telegram_id }}) - [{{ u.role }}]
                </option>
              </select>
            </div>
            <span class="sub-hint">
              💡 Selecting a Student automatically promotes them to DISCIPLINE_ADMIN and resets their session cache.
            </span>
          </div>

          <div v-if="isEditing" class="form-group checkbox-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="form.is_active" />
              <span>Active in Telegram Bot Catalog</span>
            </label>
          </div>

          <div class="modal-footer">
            <button type="button" @click="closeModal" class="btn-secondary">Cancel</button>
            <button type="submit" :disabled="modalSaving" class="btn-primary">
              {{ modalSaving ? 'Saving...' : (isEditing ? 'Save Changes' : 'Create Discipline') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { disciplineApi, userApi } from '../services/api'

const router = useRouter()
const currentUser = ref(null)
const disciplines = ref([])
const eligibleUsers = ref([])
const loading = ref(false)
const modalSaving = ref(false)
const searchQuery = ref('')
const showModal = ref(false)
const isEditing = ref(false)

const toast = ref({
  message: '',
  type: 'success',
})

const form = ref({
  slug: '',
  name: '',
  tier: 'medium',
  description: '',
  chat_url: '',
  admin_id: null,
  is_active: true,
})

const filteredDisciplines = computed(() => {
  if (!searchQuery.value.trim()) return disciplines.value
  const q = searchQuery.value.toLowerCase()
  return disciplines.value.filter(d => 
    d.slug.toLowerCase().includes(q) ||
    d.name.toLowerCase().includes(q) ||
    d.description.toLowerCase().includes(q) ||
    (d.admin?.first_name && d.admin.first_name.toLowerCase().includes(q)) ||
    (d.admin?.username && d.admin.username.toLowerCase().includes(q))
  )
})

function showToast(message, type = 'success') {
  toast.value = { message, type }
  setTimeout(() => {
    if (toast.value.message === message) toast.value.message = ''
  }, 5000)
}

function truncate(text, len) {
  if (!text) return ''
  return text.length > len ? text.slice(0, len) + '...' : text
}

async function fetchDisciplines() {
  loading.value = true
  try {
    const res = await disciplineApi.getAll()
    disciplines.value = res.data
  } catch (err) {
    showToast(err.response?.data?.detail || 'Failed to fetch disciplines', 'error')
  } finally {
    loading.value = false
  }
}

async function fetchEligibleUsers() {
  try {
    const res = await userApi.getUsers({ limit: 100 })
    eligibleUsers.value = res.data.items
  } catch (err) {
    console.error('Failed to fetch user list:', err)
  }
}

function openCreateModal() {
  isEditing.value = false
  form.value = {
    slug: '',
    name: '',
    tier: 'medium',
    description: '',
    chat_url: '',
    admin_id: null,
    is_active: true,
  }
  showModal.value = true
}

function openEditModal(item) {
  isEditing.value = true
  form.value = {
    slug: item.slug,
    name: item.name,
    tier: item.tier,
    description: item.description,
    chat_url: item.chat_url,
    admin_id: item.admin_id || null,
    is_active: item.is_active,
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function saveDiscipline() {
  modalSaving.value = true
  try {
    if (isEditing.value) {
      await disciplineApi.update(form.value.slug, {
        name: form.value.name,
        tier: form.value.tier,
        description: form.value.description,
        chat_url: form.value.chat_url,
        admin_id: form.value.admin_id,
        is_active: form.value.is_active,
      })
      showToast(`Discipline "${form.value.name}" updated successfully! Role synchronization applied.`)
    } else {
      await disciplineApi.create({
        slug: form.value.slug,
        name: form.value.name,
        tier: form.value.tier,
        description: form.value.description,
        chat_url: form.value.chat_url,
        admin_id: form.value.admin_id,
      })
      showToast(`Discipline "${form.value.name}" created!`)
    }
    closeModal()
    await fetchDisciplines()
    await fetchEligibleUsers()
  } catch (err) {
    showToast(err.response?.data?.detail || 'Error saving discipline', 'error')
  } finally {
    modalSaving.value = false
  }
}

async function deactivateDiscipline(item) {
  if (!confirm(`Are you sure you want to deactivate ${item.name}? Curator will be released.`)) return
  try {
    await disciplineApi.delete(item.slug)
    showToast(`Discipline "${item.name}" deactivated.`)
    await fetchDisciplines()
    await fetchEligibleUsers()
  } catch (err) {
    showToast(err.response?.data?.detail || 'Failed to deactivate', 'error')
  }
}

function logout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user')
  router.push('/login')
}

onMounted(() => {
  const userStr = localStorage.getItem('user')
  if (userStr) {
    try {
      currentUser.value = JSON.parse(userStr)
    } catch (_) {}
  }
  fetchDisciplines()
  fetchEligibleUsers()
})
</script>

<style scoped>
.admin-container {
  min-height: 100vh;
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.glass-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding: 1rem 1.5rem;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 2.5rem;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.logo h1 {
  font-size: 1.5rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.badge {
  font-size: 0.8rem;
  background: #6c5ce7;
  padding: 0.2rem 0.5rem;
  border-radius: 6px;
}

.nav-tabs {
  display: flex;
  gap: 0.75rem;
}

.tab-link {
  color: #a0a0b0;
  text-decoration: none;
  font-weight: 500;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  transition: all 0.2s;
}

.tab-link:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.05);
}

.tab-link.active {
  color: #fff;
  background: rgba(108, 92, 231, 0.25);
  border: 1px solid rgba(108, 92, 231, 0.5);
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.username {
  font-weight: 500;
}

.btn-logout {
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: #ff7675;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-logout:hover {
  background: rgba(255, 118, 117, 0.2);
}

.toast-banner {
  margin-bottom: 1.5rem;
  padding: 1rem 1.5rem;
  border-radius: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 500;
}

.toast-banner.success {
  background: rgba(46, 204, 113, 0.2);
  border: 1px solid rgba(46, 204, 113, 0.4);
  color: #2ecc71;
}

.toast-banner.error {
  background: rgba(231, 76, 60, 0.2);
  border: 1px solid rgba(231, 76, 60, 0.4);
  color: #e74c3c;
}

.toast-close {
  background: none;
  border: none;
  color: inherit;
  font-size: 1.2rem;
  cursor: pointer;
}

.glass-panel {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 1.5rem;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.toolbar-title {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.counter-badge {
  font-size: 0.8rem;
  background: rgba(255, 255, 255, 0.1);
  padding: 0.3rem 0.6rem;
  border-radius: 12px;
  color: #a0a0b0;
}

.toolbar-actions {
  display: flex;
  gap: 1rem;
}

.search-box {
  display: flex;
  align-items: center;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 0.5rem 1rem;
  width: 280px;
}

.search-box input {
  background: transparent;
  border: none;
  color: #fff;
  margin-left: 0.5rem;
  outline: none;
  width: 100%;
}

.btn-primary {
  background: #6c5ce7;
  color: white;
  border: none;
  padding: 0.6rem 1.2rem;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover {
  background: #5b4bc4;
  transform: translateY(-1px);
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.2);
  padding: 0.6rem 1.2rem;
  border-radius: 8px;
  cursor: pointer;
}

.table-wrapper {
  overflow-x: auto;
  position: relative;
  min-height: 250px;
}

table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

th {
  padding: 1rem;
  color: #a0a0b0;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

td {
  padding: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  vertical-align: middle;
}

.name-cell {
  display: flex;
  flex-direction: column;
}

.sub-text {
  font-size: 0.8rem;
  color: #a0a0b0;
  margin-top: 0.2rem;
}

.tier-badge {
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
}

.tier-badge.major {
  background: rgba(230, 126, 34, 0.2);
  color: #e67e22;
  border: 1px solid rgba(230, 126, 34, 0.4);
}

.tier-badge.medium {
  background: rgba(52, 152, 219, 0.2);
  color: #3498db;
  border: 1px solid rgba(52, 152, 219, 0.4);
}

.curator-info {
  display: flex;
  flex-direction: column;
}

.curator-name {
  font-weight: 600;
  color: #a29bfe;
}

.curator-unassigned {
  color: #7f8c8d;
  font-style: italic;
  font-size: 0.85rem;
}

.chat-link {
  color: #00cec9;
  text-decoration: none;
  font-size: 0.85rem;
}

.chat-link:hover {
  text-decoration: underline;
}

.status-badge {
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
}

.status-badge.verified {
  background: rgba(46, 204, 113, 0.2);
  color: #2ecc71;
}

.status-badge.pending {
  background: rgba(149, 165, 166, 0.2);
  color: #95a5a6;
}

.actions {
  display: flex;
  gap: 0.5rem;
}

.btn-icon {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 0.4rem 0.6rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-icon:hover {
  background: rgba(255, 255, 255, 0.15);
}

.btn-icon:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: #a0a0b0;
}

.mono {
  font-family: monospace;
}

.font-bold {
  font-weight: 700;
}

/* Modal Styling */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(5px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  width: 90%;
  max-width: 650px;
  background: #1e1e2f;
  border: 1px solid rgba(255, 255, 255, 0.15);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 1rem;
  margin-bottom: 1.5rem;
}

.modal-header h3 {
  font-size: 1.25rem;
}

.modal-close {
  background: none;
  border: none;
  color: #a0a0b0;
  font-size: 1.5rem;
  cursor: pointer;
}

.form-row {
  display: flex;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1.2rem;
  flex: 1;
}

.form-group label {
  font-size: 0.85rem;
  color: #a0a0b0;
  font-weight: 500;
}

.form-input {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.15);
  padding: 0.6rem 0.8rem;
  border-radius: 8px;
  color: #fff;
  outline: none;
}

.form-input:focus {
  border-color: #6c5ce7;
}

.sub-hint {
  font-size: 0.75rem;
  color: #fdcb6e;
  line-height: 1.3;
}

.checkbox-group {
  flex-direction: row;
  align-items: center;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #fff;
  cursor: pointer;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1.5rem;
}

.loading-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(2px);
  display: flex;
  justify-content: center;
  align-items: center;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(108, 92, 231, 0.3);
  border-radius: 50%;
  border-top-color: #6c5ce7;
  animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
