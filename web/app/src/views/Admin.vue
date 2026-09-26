<template>
  <div class="admin-container">
    <!-- Minimalist Header -->
    <header class="header">
      <div class="header-inner">
        <div class="header-left">
          <router-link to="/admin" class="logo">
            <img src="/logo.png" alt="AITU Gaming" class="brand-logo" />
            <span class="logo-pill">Admin</span>
          </router-link>
          <nav class="nav">
            <router-link to="/tournaments" class="nav-item">Tournaments</router-link>
            <router-link to="/admin" class="nav-item active">Members</router-link>
            <router-link to="/admin/disciplines" class="nav-item">Disciplines</router-link>
          </nav>
        </div>
        <div class="header-right">
          <span class="admin-user">{{ currentUser?.first_name || 'Admin' }}</span>
          <button @click="logout" class="btn-ghost text-danger">Logout</button>
        </div>
      </div>
    </header>

    <main class="page-body">
      <div class="toolbar">
        <div class="toolbar-title">
          <h2>Members</h2>
          <span class="count-badge">{{ total }} registered</span>
        </div>
        <div class="search-wrap">
          <input 
            v-model="searchQuery" 
            @input="debounceSearch"
            type="text" 
            placeholder="Search barcode, name, group..." 
            class="search-input"
          />
        </div>
      </div>

      <div class="table-container">
        <table v-if="!loading || users.length > 0" class="minimal-table">
          <thead>
            <tr>
              <th>Barcode</th>
              <th>Name</th>
              <th>Group</th>
              <th>Contact</th>
              <th>Role</th>
              <th>Status</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.telegram_id">
              <td class="mono">{{ user.barcode || '—' }}</td>
              <td>{{ user.first_name }} {{ user.last_name || '' }}</td>
              <td>{{ user.academic_group || '—' }}</td>
              <td>
                <div class="contact-col">
                  <span>{{ user.phone_number || '—' }}</span>
                  <span class="sub-text">{{ user.username ? '@' + user.username : '' }}</span>
                </div>
              </td>
              <td>
                <select 
                  v-model="user.role" 
                  @change="updateRole(user, $event.target.value)"
                  class="role-select"
                >
                  <option value="STUDENT">Student</option>
                  <option value="DISCIPLINE_ADMIN">Discipline Admin</option>
                  <option value="HEAD_ADMIN">Head Admin</option>
                </select>
              </td>
              <td>
                <div class="status-dot-wrap">
                  <span class="status-dot" :class="user.is_verified ? 'verified' : 'pending'"></span>
                  <span class="status-text">{{ user.is_verified ? 'Verified' : 'Pending' }}</span>
                </div>
              </td>
              <td class="text-right">
                <button 
                  @click="deleteUser(user)" 
                  class="btn-delete"
                  title="Delete User"
                >
                  Delete
                </button>
              </td>
            </tr>
            <tr v-if="users.length === 0 && !loading">
              <td colspan="7" class="empty-state">No members found matching your search.</td>
            </tr>
          </tbody>
        </table>
        
        <div v-if="loading" class="loading-overlay">
          <div class="minimal-spinner"></div>
        </div>
      </div>

      <div class="pagination">
        <span class="page-info">Showing {{ users.length }} of {{ total }} members</span>
        <div class="page-controls">
          <button @click="prevPage" :disabled="offset === 0" class="btn-page">◀ Prev</button>
          <button @click="nextPage" :disabled="offset + limit >= total" class="btn-page">Next ▶</button>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'

const router = useRouter()
const users = ref([])
const total = ref(0)
const limit = ref(50)
const offset = ref(0)
const searchQuery = ref('')
const loading = ref(false)
const currentUser = ref(null)

let searchTimeout = null

const loadCurrentUser = () => {
  try {
    currentUser.value = JSON.parse(localStorage.getItem('user'))
  } catch (e) {
    currentUser.value = null
  }
}

const fetchUsers = async () => {
  loading.value = true
  try {
    const res = await api.get('/admin/users', {
      params: {
        limit: limit.value,
        offset: offset.value,
        query: searchQuery.value || undefined
      }
    })
    users.value = res.data.items
    total.value = res.data.total
  } catch (err) {
    console.error("Failed to fetch users", err)
  } finally {
    loading.value = false
  }
}

const debounceSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    offset.value = 0
    fetchUsers()
  }, 300)
}

const nextPage = () => {
  if (offset.value + limit.value < total.value) {
    offset.value += limit.value
    fetchUsers()
  }
}

const prevPage = () => {
  if (offset.value >= limit.value) {
    offset.value -= limit.value
    fetchUsers()
  }
}

const updateRole = async (user, newRole) => {
  try {
    await api.patch(`/admin/users/${user.telegram_id}/role`, { role: newRole })
  } catch (err) {
    alert(err.response?.data?.detail || "Failed to update role")
    fetchUsers()
  }
}

const deleteUser = async (user) => {
  if (!confirm(`Are you sure you want to delete ${user.first_name} ${user.last_name || ''}?`)) {
    return
  }
  try {
    await api.delete(`/admin/users/${user.telegram_id}`)
    fetchUsers()
  } catch (err) {
    alert(err.response?.data?.detail || "Failed to delete user")
  }
}

const logout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user')
  router.push('/login')
}

onMounted(() => {
  loadCurrentUser()
  fetchUsers()
})
</script>

<style scoped>
.admin-container {
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

.brand-logo {
  height: 28px;
  width: auto;
  object-fit: contain;
  display: block;
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
  color: var(--text-secondary);
  font-size: 0.88rem;
  font-weight: 500;
  padding: 0.5rem 0.85rem;
  position: relative;
  transition: color 0.15s;
}

.nav-item:hover {
  color: #fff;
}

.nav-item.active {
  color: #fff;
}

.nav-item.active::after {
  content: '';
  position: absolute;
  bottom: -0.85rem;
  left: 0.5rem;
  right: 0.5rem;
  height: 2px;
  background-color: var(--accent);
  box-shadow: 0 0 8px var(--accent);
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

/* Body */
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

.search-wrap {
  width: 280px;
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

.contact-col {
  display: flex;
  flex-direction: column;
}

.sub-text {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.role-select {
  background: rgba(255, 255, 255, 0.04);
  color: #fff;
  border: 1px solid var(--surface-border);
  padding: 0.35rem 0.55rem;
  border-radius: var(--radius-sm);
  font-size: 0.82rem;
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

.status-dot.verified { background: var(--success, #10b981); }
.status-dot.pending { background: var(--warning, #f59e0b); }

.status-text {
  font-size: 0.82rem;
  color: var(--text-secondary);
}

.text-right { text-align: right; }

.btn-delete {
  font-size: 0.8rem;
  color: #f87171;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  padding: 0.25rem 0.6rem;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.btn-delete:hover {
  background: rgba(239, 68, 68, 0.2);
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

/* Pagination */
.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 1.25rem;
}

.page-info {
  font-size: 0.82rem;
  color: var(--text-muted);
}

.page-controls {
  display: flex;
  gap: 0.4rem;
}

.btn-page {
  font-size: 0.82rem;
  color: var(--text-secondary);
  background: var(--surface-bg);
  border: 1px solid var(--surface-border);
  padding: 0.35rem 0.75rem;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.btn-page:hover:not(:disabled) {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.2);
}

.btn-page:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
</style>
