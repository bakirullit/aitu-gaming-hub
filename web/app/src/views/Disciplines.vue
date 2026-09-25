<template>
  <div class="disciplines-page">
    <!-- Minimalist Header -->
    <header class="header">
      <div class="header-inner">
        <div class="header-left">
          <router-link to="/admin" class="logo">
            <span class="logo-mark">AITU</span>
            <span class="logo-text">Gaming Hub</span>
            <span class="logo-pill">Disciplines</span>
          </router-link>
          <nav class="nav">
            <router-link to="/tournaments" class="nav-item">Tournaments</router-link>
            <router-link to="/admin" class="nav-item">Members</router-link>
            <router-link to="/admin/disciplines" class="nav-item active">Disciplines</router-link>
          </nav>
        </div>
        <div class="header-right">
          <span class="admin-user">{{ currentUser?.first_name || 'Admin' }}</span>
          <button @click="logout" class="btn-ghost text-danger">Logout</button>
        </div>
      </div>
    </header>

    <!-- Toast Notification Banner -->
    <transition name="fade">
      <div v-if="toast.message" class="toast-banner" :class="toast.type">
        <span>{{ toast.message }}</span>
        <button @click="toast.message = ''" class="toast-close">✕</button>
      </div>
    </transition>

    <main class="page-body">
      <div class="toolbar">
        <div class="toolbar-title">
          <h2>Disciplines</h2>
          <span class="count-badge">{{ disciplines.length }} active</span>
        </div>
        <div class="toolbar-actions">
          <div class="search-wrap">
            <input 
              v-model="searchQuery" 
              type="text" 
              placeholder="Filter disciplines..." 
              class="search-input"
            />
          </div>
          <button @click="openCreateModal" class="btn-primary-action">
            + New Discipline
          </button>
        </div>
      </div>

      <div class="table-container">
        <table v-if="!loading || disciplines.length > 0" class="minimal-table">
          <thead>
            <tr>
              <th>Slug</th>
              <th>Discipline</th>
              <th>Tier</th>
              <th>Curator</th>
              <th>Chat</th>
              <th>Status</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in filteredDisciplines" :key="item.slug">
              <td class="mono">{{ item.slug }}</td>
              <td>
                <div class="name-cell">
                  <strong>{{ item.name }}</strong>
                  <span class="sub-text">{{ truncate(item.description, 50) }}</span>
                </div>
              </td>
              <td>
                <span class="tier-pill" :class="item.tier">
                  {{ item.tier === 'major' ? 'Major' : 'Medium' }}
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
                  Open Chat ↗
                </a>
              </td>
              <td>
                <div class="status-dot-wrap">
                  <span class="status-dot" :class="item.is_active ? 'active' : 'inactive'"></span>
                  <span class="status-text">{{ item.is_active ? 'Active' : 'Inactive' }}</span>
                </div>
              </td>
              <td class="text-right">
                <div class="actions">
                  <button 
                    @click="openEditModal(item)" 
                    class="btn-subtle small"
                    title="Edit"
                  >
                    Edit
                  </button>
                  <button 
                    @click="deactivateDiscipline(item)" 
                    class="btn-delete small"
                    title="Deactivate"
                    :disabled="!item.is_active"
                  >
                    Deactivate
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="filteredDisciplines.length === 0 && !loading">
              <td colspan="7" class="empty-state">No disciplines found.</td>
            </tr>
          </tbody>
        </table>

        <div v-if="loading" class="loading-overlay">
          <div class="minimal-spinner"></div>
        </div>
      </div>
    </main>

    <!-- Modal Dialog: Create / Edit Discipline -->
    <transition name="fade">
      <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
        <div class="modal">
          <div class="modal-top">
            <h3 class="modal-heading">{{ isEditing ? 'Edit Discipline' : 'New Discipline' }}</h3>
            <button @click="closeModal" class="btn-close">✕</button>
          </div>

          <form @submit.prevent="saveDiscipline" class="modal-body">
            <div class="form-row">
              <div class="form-group">
                <label>Slug</label>
                <input 
                  v-model="form.slug" 
                  type="text" 
                  required 
                  placeholder="e.g. cs2, valorant"
                  :disabled="isEditing"
                  class="form-input mono"
                />
              </div>
              <div class="form-group">
                <label>Display Name</label>
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
                <label>Tier</label>
                <select v-model="form.tier" class="form-input">
                  <option value="major">Major</option>
                  <option value="medium">Medium</option>
                </select>
              </div>
              <div class="form-group">
                <label>Telegram Chat Link</label>
                <input 
                  v-model="form.chat_url" 
                  type="url" 
                  required 
                  placeholder="https://t.me/..."
                  class="form-input"
                />
              </div>
            </div>

            <div class="form-group">
              <label>Curator</label>
              <select v-model="form.admin_id" class="form-input">
                <option :value="null">— None (Unassigned) —</option>
                <option 
                  v-for="user in eligibleUsers" 
                  :key="user.telegram_id" 
                  :value="user.telegram_id"
                >
                  {{ user.first_name }} {{ user.last_name || '' }} ({{ user.username ? '@' + user.username : 'ID: ' + user.telegram_id }})
                </option>
              </select>
            </div>

            <div class="form-group">
              <label>Description</label>
              <textarea 
                v-model="form.description" 
                rows="3" 
                required 
                placeholder="Brief summary of this discipline direction..."
                class="form-input"
              ></textarea>
            </div>

            <div v-if="isEditing" class="form-group checkbox-group">
              <label class="checkbox-label">
                <input type="checkbox" v-model="form.is_active" />
                <span>Active</span>
              </label>
            </div>

            <div class="modal-actions">
              <button type="button" @click="closeModal" class="btn-subtle">Cancel</button>
              <button type="submit" :disabled="modalSaving" class="btn-primary-action">
                {{ modalSaving ? 'Saving...' : (isEditing ? 'Save Changes' : 'Create') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </transition>
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
  }, 4000)
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
      showToast(`Discipline "${form.value.name}" updated successfully.`)
    } else {
      await disciplineApi.create({
        slug: form.value.slug,
        name: form.value.name,
        tier: form.value.tier,
        description: form.value.description,
        chat_url: form.value.chat_url,
        admin_id: form.value.admin_id,
      })
      showToast(`Discipline "${form.value.name}" created.`)
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
.disciplines-page {
  min-height: 100vh;
  background-color: var(--bg-color, #090a0f);
  color: var(--text-primary, #f8fafc);
  padding-bottom: 5rem;
}

/* Header */
.header {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(9, 10, 15, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--surface-border, rgba(255, 255, 255, 0.07));
}

.header-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0.85rem 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 2rem;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
  color: inherit;
}

.logo-mark {
  font-weight: 700;
  font-size: 0.95rem;
  letter-spacing: 0.5px;
  background: rgba(255, 255, 255, 0.1);
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
}

.logo-text {
  font-weight: 600;
  font-size: 0.95rem;
}

.logo-pill {
  font-size: 0.72rem;
  color: var(--text-secondary);
  background: var(--surface-bg);
  border: 1px solid var(--surface-border);
  padding: 0.1rem 0.45rem;
  border-radius: 9999px;
  margin-left: 0.25rem;
}

.nav {
  display: flex;
  gap: 0.25rem;
}

.nav-item {
  color: var(--text-secondary, #94a3b8);
  font-size: 0.88rem;
  font-weight: 500;
  padding: 0.4rem 0.75rem;
  border-radius: var(--radius-sm, 6px);
  transition: all 0.15s ease;
}

.nav-item:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.04);
}

.nav-item.active {
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.admin-user {
  font-size: 0.88rem;
  color: var(--text-secondary);
}

.btn-ghost {
  font-size: 0.82rem;
  color: var(--text-secondary);
  padding: 0.35rem 0.65rem;
  border-radius: var(--radius-sm);
  transition: color 0.15s;
}

.btn-ghost:hover {
  color: #fff;
}

.text-danger { color: #f87171 !important; }

/* Toast */
.toast-banner {
  max-width: 1200px;
  margin: 1rem auto 0 auto;
  padding: 0.75rem 1.25rem;
  border-radius: var(--radius-sm);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
  font-weight: 500;
}

.toast-banner.success {
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.25);
  color: #34d399;
}

.toast-banner.error {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.25);
  color: #f87171;
}

.toast-close {
  color: inherit;
  font-size: 0.85rem;
}

/* Page Body */
.page-body {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2.5rem 1.5rem;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.toolbar-title {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
}

.toolbar-title h2 {
  font-size: 1.5rem;
  font-weight: 700;
}

.count-badge {
  font-size: 0.82rem;
  color: var(--text-muted);
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.search-wrap {
  width: 240px;
}

.search-input {
  width: 100%;
  background: var(--surface-bg);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-sm);
  color: #fff;
  padding: 0.45rem 0.75rem;
  font-size: 0.85rem;
}

.search-input:focus {
  border-color: rgba(255, 255, 255, 0.25);
}

.btn-primary-action {
  font-size: 0.85rem;
  font-weight: 500;
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.15);
  padding: 0.45rem 0.85rem;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.btn-primary-action:hover {
  background: rgba(255, 255, 255, 0.16);
}

/* Table */
.table-container {
  position: relative;
  background: var(--surface-bg);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  overflow-x: auto;
}

.minimal-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.minimal-table th {
  padding: 0.85rem 1.25rem;
  font-size: 0.78rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  border-bottom: 1px solid var(--surface-border);
}

.minimal-table td {
  padding: 0.85rem 1.25rem;
  font-size: 0.88rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.minimal-table tbody tr:hover {
  background: rgba(255, 255, 255, 0.02);
}

.mono {
  font-family: monospace;
  color: #cbd5e1;
}

.name-cell {
  display: flex;
  flex-direction: column;
}

.sub-text {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.tier-pill {
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-secondary);
}

.tier-pill.major {
  color: #fbbf24;
  background: rgba(245, 158, 11, 0.1);
}

.curator-info {
  display: flex;
  flex-direction: column;
}

.curator-name {
  font-size: 0.88rem;
  font-weight: 500;
}

.curator-unassigned {
  font-size: 0.82rem;
  color: var(--text-muted);
}

.chat-link {
  font-size: 0.82rem;
  color: var(--accent);
}

.chat-link:hover {
  text-decoration: underline;
}

.status-dot-wrap {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-dot.active { background: var(--success, #10b981); }
.status-dot.inactive { background: var(--text-muted); }

.status-text {
  font-size: 0.82rem;
  color: var(--text-secondary);
}

.text-right { text-align: right; }

.actions {
  display: inline-flex;
  gap: 0.4rem;
}

.btn-subtle {
  font-size: 0.82rem;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--surface-border);
  padding: 0.35rem 0.65rem;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.btn-subtle:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
}

.btn-subtle.small, .btn-delete.small {
  padding: 0.25rem 0.55rem;
  font-size: 0.78rem;
}

.btn-delete {
  font-size: 0.8rem;
  color: #f87171;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  padding: 0.25rem 0.6rem;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.btn-delete:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.2);
}

.btn-delete:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: var(--text-muted);
}

.loading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(9, 10, 15, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
}

.minimal-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 1rem;
}

.modal {
  width: 100%;
  max-width: 520px;
  background: #0f1117;
  border: 1px solid var(--surface-border-hover);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.modal-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--surface-border);
}

.modal-heading {
  font-size: 1.15rem;
  font-weight: 600;
}

.btn-close {
  color: var(--text-muted);
  font-size: 0.95rem;
}

.btn-close:hover { color: #fff; }

.modal-body {
  padding: 1.5rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.85rem;
  margin-bottom: 0.85rem;
}

.form-group {
  margin-bottom: 0.85rem;
}

.form-group label {
  display: block;
  font-size: 0.78rem;
  color: var(--text-secondary);
  margin-bottom: 0.35rem;
}

.form-input {
  width: 100%;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-sm);
  color: #fff;
  padding: 0.5rem 0.75rem;
  font-size: 0.85rem;
}

.form-input:focus {
  border-color: rgba(255, 255, 255, 0.25);
}

.form-input:disabled {
  opacity: 0.5;
}

.checkbox-group {
  margin-top: 0.5rem;
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  cursor: pointer;
}

.modal-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.65rem;
  padding-top: 1rem;
  border-top: 1px solid var(--surface-border);
  margin-top: 1rem;
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .form-row { grid-template-columns: 1fr; }
  .header-left { gap: 1rem; }
}
</style>
