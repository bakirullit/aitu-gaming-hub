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
          <router-link to="/admin" class="tab-link active">👥 Members</router-link>
          <router-link to="/admin/disciplines" class="tab-link">🎮 Disciplines</router-link>
        </nav>
      </div>
      <div class="user-menu">
        <span class="username">{{ currentUser?.first_name || 'Admin' }}</span>
        <button @click="logout" class="btn-logout">Logout</button>
      </div>
    </div>

    <div class="glass-panel main-content">
      <div class="toolbar">
        <h2>Members Management</h2>
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input 
            v-model="searchQuery" 
            @input="debounceSearch"
            type="text" 
            placeholder="Search by Barcode, Name, Group..." 
          />
        </div>
      </div>

      <div class="table-wrapper">
        <table v-if="!loading || users.length > 0">
          <thead>
            <tr>
              <th>Barcode</th>
              <th>Name</th>
              <th>Group</th>
              <th>Contact</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.telegram_id">
              <td class="mono">{{ user.barcode || 'N/A' }}</td>
              <td>{{ user.first_name }} {{ user.last_name }}</td>
              <td>{{ user.academic_group || 'N/A' }}</td>
              <td>
                <div class="contact-col">
                  <span>{{ user.phone_number }}</span>
                  <span class="sub-text">{{ user.username ? '@' + user.username : '' }}</span>
                </div>
              </td>
              <td>
                <select 
                  v-model="user.role" 
                  @change="updateRole(user, $event.target.value)"
                  class="role-select"
                  :class="user.role.toLowerCase()"
                >
                  <option value="STUDENT">Student</option>
                  <option value="DISCIPLINE_ADMIN">Discipline Admin</option>
                  <option value="HEAD_ADMIN">Head Admin</option>
                </select>
              </td>
              <td>
                <span class="status-badge" :class="user.is_verified ? 'verified' : 'pending'">
                  {{ user.is_verified ? 'Verified' : 'Pending' }}
                </span>
              </td>
              <td class="actions">
                <button 
                  @click="deleteUser(user)" 
                  class="btn-icon btn-danger"
                  title="Delete User"
                >
                  🗑️
                </button>
              </td>
            </tr>
            <tr v-if="users.length === 0 && !loading">
              <td colspan="7" class="empty-state">No members found matching your search.</td>
            </tr>
          </tbody>
        </table>
        
        <div v-if="loading" class="loading-overlay">
          <div class="spinner"></div>
        </div>
      </div>

      <div class="pagination">
        <span class="page-info">Showing {{ users.length }} of {{ total }} members</span>
        <div class="page-controls">
          <button @click="prevPage" :disabled="offset === 0">◀ Prev</button>
          <button @click="nextPage" :disabled="offset + limit >= total">Next ▶</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
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

const isSelf = (user) => {
  return currentUser.value && currentUser.value.telegram_id === user.telegram_id
}

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
  }, 400)
}

const prevPage = () => {
  if (offset.value >= limit.value) {
    offset.value -= limit.value
    fetchUsers()
  }
}

const nextPage = () => {
  if (offset.value + limit.value < total.value) {
    offset.value += limit.value
    fetchUsers()
  }
}

const updateRole = async (user, newRole) => {
  const originalRole = user.role
  try {
    await api.patch(`/admin/users/${user.telegram_id}/role`, { role: newRole })
    // Assume success, state is already updated via v-model
  } catch (err) {
    alert(err.response?.data?.detail || "Failed to update role")
    user.role = originalRole // revert on failure
  }
}

const deleteUser = async (user) => {
  if (!confirm(`Are you sure you want to delete ${user.first_name || 'this user'}? This will also remove their Minecraft whitelist and Helpdesk tickets.`)) {
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
  background: radial-gradient(circle at top right, #16213e, #0f3460, #1a1a2e);
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.glass-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.logo {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.logo .icon {
  font-size: 2rem;
}

.logo h1 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #fff;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.badge {
  font-size: 0.7rem;
  background: #e84393;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  text-transform: uppercase;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 2.5rem;
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
  color: #a29bfe;
  font-weight: 500;
}

.btn-logout {
  background: rgba(255, 118, 117, 0.2);
  color: #ff7675;
  border: 1px solid rgba(255, 118, 117, 0.5);
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-logout:hover {
  background: #ff7675;
  color: #fff;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 2rem;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(16px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.toolbar h2 {
  color: #fff;
  font-size: 1.25rem;
}

.search-box {
  position: relative;
  width: 300px;
}

.search-icon {
  position: absolute;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  color: #a0a0b0;
}

.search-box input {
  width: 100%;
  padding: 0.75rem 1rem 0.75rem 2.5rem;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  box-sizing: border-box;
}

.search-box input:focus {
  outline: none;
  border-color: #6c5ce7;
  background: rgba(255, 255, 255, 0.1);
}

.table-wrapper {
  flex: 1;
  position: relative;
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

th {
  background: rgba(255, 255, 255, 0.05);
  color: #a0a0b0;
  padding: 1rem;
  font-weight: 600;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

td {
  padding: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  color: #ecf0f1;
  vertical-align: middle;
}

tr:hover td {
  background: rgba(255, 255, 255, 0.02);
}

.mono {
  font-family: monospace;
  color: #74b9ff;
}

.contact-col {
  display: flex;
  flex-direction: column;
}

.sub-text {
  font-size: 0.8rem;
  color: #a0a0b0;
}

.status-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 600;
}

.status-badge.verified {
  background: rgba(0, 184, 148, 0.2);
  color: #00b894;
}

.status-badge.pending {
  background: rgba(253, 203, 110, 0.2);
  color: #fdcb6e;
}

.role-select {
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.2);
  padding: 0.4rem;
  border-radius: 4px;
  font-size: 0.9rem;
  outline: none;
}

.role-select.student { color: #a29bfe; }
.role-select.discipline_admin { color: #00cec9; }
.role-select.head_admin { color: #fd79a8; font-weight: bold; }

.role-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.actions {
  display: flex;
  gap: 0.5rem;
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.1rem;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.btn-icon:hover:not(:disabled) {
  opacity: 1;
}

.btn-icon:disabled {
  cursor: not-allowed;
  opacity: 0.3;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: #a0a0b0;
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

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 1.5rem;
}

.page-info {
  color: #a0a0b0;
  font-size: 0.9rem;
}

.page-controls {
  display: flex;
  gap: 0.5rem;
}

.page-controls button {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #fff;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.page-controls button:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
}

.page-controls button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
