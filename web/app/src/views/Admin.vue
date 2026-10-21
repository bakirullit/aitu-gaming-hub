<template>
  <div class="admin-container">
    <AdminNav />

    <!-- Toast Notification Banner -->
    <transition name="fade">
      <div v-if="toast.message" class="toast-banner" :class="toast.type">
        <span>{{ toast.message }}</span>
        <button @click="toast.message = ''" class="toast-close">✕</button>
      </div>
    </transition>

    <main class="page-body">
      <!-- Toolbar & Action Controls -->
      <div class="toolbar">
        <div class="toolbar-left">
          <div class="tab-pills">
            <button 
              class="tab-pill" 
              :class="{ active: currentTab === 'members' }"
              @click="currentTab = 'members'"
            >
              Registered Members <span class="pill-count">{{ total }}</span>
            </button>
            <button 
              class="tab-pill" 
              :class="{ active: currentTab === 'pending' }"
              @click="switchTab('pending')"
            >
              Pending Staff <span class="pill-count warning">{{ pendingStaff.length }}</span>
            </button>
          </div>
        </div>

        <div class="toolbar-right">
          <div v-if="currentTab === 'members'" class="search-wrap">
            <input 
              v-model="searchQuery" 
              @input="debounceSearch"
              type="text" 
              placeholder="Search barcode, name, group..." 
              class="search-input"
            />
          </div>
          <button @click="showImportModal = true" class="btn-secondary">
            📥 Import CSV
          </button>
          <button @click="openPrecreateModal" class="btn-primary">
            + Pre-create Staff
          </button>
        </div>
      </div>

      <!-- Tab 1: Registered Members Table -->
      <div v-if="currentTab === 'members'" class="table-container">
        <table v-if="!loading || users.length > 0" class="minimal-table">
          <thead>
            <tr>
              <th>Barcode</th>
              <th>Name</th>
              <th>Group</th>
              <th>Contact</th>
              <th>Role</th>
              <th>Staff / Mystery Box</th>
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
                <div v-if="user.staff_role && user.staff_role !== 'none'" class="staff-role-badge">
                  <span class="badge-role">{{ user.staff_role }}</span>
                  <span class="badge-sub" :class="user.is_role_revealed ? 'opened' : 'sealed'">
                    {{ user.is_role_revealed ? '🎁 Revealed' : '🔒 Sealed Box' }}
                  </span>
                </div>
                <span v-else class="text-muted">—</span>
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
              <td colspan="8" class="empty-state">No members found matching your search.</td>
            </tr>
          </tbody>
        </table>
        
        <div v-if="loading" class="loading-overlay">
          <div class="minimal-spinner"></div>
        </div>

        <div class="pagination">
          <span class="page-info">Showing {{ users.length }} of {{ total }} members</span>
          <div class="page-controls">
            <button @click="prevPage" :disabled="offset === 0" class="btn-page">◀ Prev</button>
            <button @click="nextPage" :disabled="offset + limit >= total" class="btn-page">Next ▶</button>
          </div>
        </div>
      </div>

      <!-- Tab 2: Pending Staff Table -->
      <div v-else class="table-container">
        <table v-if="!loadingPending || pendingStaff.length > 0" class="minimal-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Username</th>
              <th>Group / Barcode</th>
              <th>Contact Emails</th>
              <th>Assigned Staff Role</th>
              <th>Discipline</th>
              <th>Pre-created</th>
              <th class="text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in pendingStaff" :key="p.id">
              <td><strong>{{ p.first_name }} {{ p.last_name }}</strong></td>
              <td class="mono">{{ p.username ? '@' + p.username : '—' }}</td>
              <td>
                <div class="contact-col">
                  <span>{{ p.academic_group || '—' }}</span>
                  <span class="sub-text mono">{{ p.barcode || 'No barcode' }}</span>
                </div>
              </td>
              <td>
                <div class="contact-col">
                  <span>{{ p.email || '—' }}</span>
                  <span v-if="p.corp_email" class="sub-text">{{ p.corp_email }}</span>
                </div>
              </td>
              <td>
                <span class="staff-tag">{{ p.staff_role }}</span>
              </td>
              <td>
                <span v-if="p.discipline_id" class="disc-pill">{{ p.discipline_id.toUpperCase() }}</span>
                <span v-else class="text-muted">Global / Any</span>
              </td>
              <td class="sub-text">{{ formatDate(p.created_at) }}</td>
              <td class="text-right">
                <button 
                  @click="deletePending(p)" 
                  class="btn-delete"
                  title="Remove invitation"
                >
                  Cancel
                </button>
              </td>
            </tr>
            <tr v-if="pendingStaff.length === 0 && !loadingPending">
              <td colspan="8" class="empty-state">No pending pre-created staff records. All staff have claimed roles!</td>
            </tr>
          </tbody>
        </table>

        <div v-if="loadingPending" class="loading-overlay">
          <div class="minimal-spinner"></div>
        </div>
      </div>

      <!-- Modal 1: Pre-create Staff -->
      <div v-if="showPrecreateModal" class="modal-backdrop" @click.self="showPrecreateModal = false">
        <div class="modal-card">
          <div class="modal-header">
            <h3>Pre-create Staff Member</h3>
            <button @click="showPrecreateModal = false" class="btn-close">✕</button>
          </div>
          <form @submit.prevent="submitPrecreate" class="modal-form">
            <div class="form-row">
              <div class="form-group">
                <label>First Name *</label>
                <input v-model="precreateForm.first_name" required placeholder="Алихан" class="form-input" />
              </div>
              <div class="form-group">
                <label>Last Name *</label>
                <input v-model="precreateForm.last_name" required placeholder="Сериков" class="form-input" />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Telegram Username (без @)</label>
                <input v-model="precreateForm.username" placeholder="alikhan_tg" class="form-input" />
              </div>
              <div class="form-group">
                <label>Academic Group</label>
                <input v-model="precreateForm.academic_group" placeholder="SE-2611" class="form-input" />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Personal Email</label>
                <input v-model="precreateForm.email" type="email" placeholder="student@example.com" class="form-input" />
              </div>
              <div class="form-group">
                <label>Corporate Email (@astanait.edu.kz)</label>
                <input v-model="precreateForm.corp_email" type="email" placeholder="231145@astanait.edu.kz" class="form-input" />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Student Barcode</label>
                <input v-model="precreateForm.barcode" placeholder="231145" class="form-input" />
              </div>
              <div class="form-group">
                <label>Phone Number</label>
                <input v-model="precreateForm.phone_number" placeholder="+77071234567" class="form-input" />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Staff Role *</label>
                <select v-model="precreateForm.staff_role" required class="form-select">
                  <option value="manager">Manager 📋</option>
                  <option value="discipline_admin">Discipline Admin ⚔️</option>
                  <option value="smm">SMM 📱</option>
                  <option value="designer">Designer 🎨</option>
                  <option value="commentator">Commentator 🎙️</option>
                  <option value="streamer">Streamer 🎥</option>
                  <option value="discord_admin">Discord Admin 💬</option>
                  <option value="head_admin">Head Admin 🛡️</option>
                </select>
              </div>
              <div class="form-group">
                <label>Assigned Discipline</label>
                <select v-model="precreateForm.discipline_id" class="form-select">
                  <option :value="null">— None (General Staff) —</option>
                  <option v-for="d in availableDisciplines" :key="d.slug" :value="d.slug">
                    {{ d.name }} ({{ d.slug }})
                  </option>
                </select>
              </div>
            </div>

            <div class="modal-actions">
              <button type="button" @click="showPrecreateModal = false" class="btn-ghost">Cancel</button>
              <button type="submit" :disabled="savingPrecreate" class="btn-primary">
                {{ savingPrecreate ? 'Saving...' : 'Pre-create Member' }}
              </button>
            </div>
          </form>
        </div>
      </div>

      <!-- Modal 2: Import CSV / Text -->
      <div v-if="showImportModal" class="modal-backdrop" @click.self="showImportModal = false">
        <div class="modal-card">
          <div class="modal-header">
            <h3>Import Staff Table (CSV / Excel / Text)</h3>
            <button @click="showImportModal = false" class="btn-close">✕</button>
          </div>
          <div class="modal-form">
            <div class="import-subtabs">
              <button 
                type="button" 
                :class="['subtab-btn', { active: importMode === 'file' }]" 
                @click="importMode = 'file'"
              >
                📁 Загрузить файл (.csv / .tsv)
              </button>
              <button 
                type="button" 
                :class="['subtab-btn', { active: importMode === 'text' }]" 
                @click="importMode = 'text'"
              >
                📋 Вставить текст (Таблица)
              </button>
            </div>

            <p class="import-hint">
              Ожидаемые столбцы (Tab, запятая или точка с запятой):<br>
              <code>Имя, Фамилия, Группа, Barcode, Телефон, Почта, Никнейм, Роль, Дисциплина</code>
            </p>

            <div v-if="importMode === 'file'" class="file-upload-box">
              <input type="file" ref="fileInput" accept=".csv,.tsv,.txt" @change="onFileSelected" />
              <div v-if="selectedFile" class="file-name">Выбран файл: <b>{{ selectedFile.name }}</b></div>
              <div v-else class="file-placeholder">Нажмите для выбора файла .csv или .tsv</div>
            </div>

            <div v-else class="text-upload-box">
              <textarea 
                v-model="importTextContent" 
                rows="7" 
                class="form-input import-textarea mono"
                placeholder="Вставьте скопированные строки таблицы сюда..."
              ></textarea>
            </div>

            <div v-if="importResult" class="import-result" :class="{ 'has-errors': importResult.errors?.length }">
              <p>Успешно создано: <b>{{ importResult.created }}</b> из {{ importResult.total_rows }} строк.</p>
              <div v-if="importResult.errors?.length" class="error-list">
                <small v-for="(err, idx) in importResult.errors" :key="idx">{{ err }}</small>
              </div>
            </div>

            <div class="modal-actions">
              <button type="button" @click="showImportModal = false" class="btn-ghost">Close</button>
              <button 
                v-if="importMode === 'file'"
                type="button" 
                :disabled="!selectedFile || importing" 
                @click="uploadCsv" 
                class="btn-primary"
              >
                {{ importing ? 'Importing...' : 'Upload & Import' }}
              </button>
              <button 
                v-else
                type="button" 
                :disabled="!importTextContent.trim() || importing" 
                @click="uploadText" 
                class="btn-primary"
              >
                {{ importing ? 'Importing...' : 'Import Text' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Modal 3: Confirmation Dialog (In-DOM, no QtWebEngine crash) -->
      <div v-if="confirmDialog.show" class="modal-backdrop" @click.self="confirmDialog.show = false">
        <div class="modal-card confirm-modal-card">
          <div class="modal-header">
            <h3>{{ confirmDialog.title }}</h3>
            <button @click="confirmDialog.show = false" class="btn-close">✕</button>
          </div>
          <div class="confirm-body">
            <p class="confirm-message">{{ confirmDialog.message }}</p>
          </div>
          <div class="modal-actions">
            <button type="button" @click="confirmDialog.show = false" class="btn-ghost">Cancel</button>
            <button type="button" @click="executeConfirm" class="btn-delete">
              {{ confirmDialog.confirmText || 'Confirm' }}
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>


<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AdminNav from '../components/AdminNav.vue'
import api, { staffApi, disciplineApi } from '../services/api'

const router = useRouter()
const users = ref([])
const total = ref(0)
const limit = ref(50)
const offset = ref(0)
const searchQuery = ref('')
const loading = ref(false)
const currentUser = ref(null)

// Staff Pre-registration & Tabs State
const currentTab = ref('members')
const pendingStaff = ref([])
const loadingPending = ref(false)
const availableDisciplines = ref([])

const showPrecreateModal = ref(false)
const showImportModal = ref(false)
const savingPrecreate = ref(false)
const importing = ref(false)
const selectedFile = ref(null)
const fileInput = ref(null)
const importResult = ref(null)
const importMode = ref('file')
const importTextContent = ref('')

const precreateForm = ref({
  first_name: '',
  last_name: '',
  username: '',
  academic_group: '',
  email: '',
  corp_email: '',
  barcode: '',
  phone_number: '',
  staff_role: 'manager',
  discipline_id: null,
})

// Toast notification state
const toast = ref({ message: '', type: 'info' })
let toastTimer = null

const showToast = (message, type = 'info') => {
  toast.value = { message, type }
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toast.value.message = ''
  }, 4000)
}

// In-app confirm modal state (replaces crashy QtWebEngine native confirm)
const confirmDialog = ref({
  show: false,
  title: '',
  message: '',
  confirmText: 'Confirm',
  action: null,
})

const executeConfirm = async () => {
  const action = confirmDialog.value.action
  confirmDialog.value.show = false
  if (action) {
    await action()
  }
}

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

const fetchPendingStaff = async () => {
  loadingPending.value = true
  try {
    const res = await staffApi.getPending()
    pendingStaff.value = res.data || []
  } catch (err) {
    console.error("Failed to fetch pending staff", err)
  } finally {
    loadingPending.value = false
  }
}

const fetchDisciplines = async () => {
  try {
    const res = await disciplineApi.getAll()
    availableDisciplines.value = res.data || []
  } catch (err) {
    console.error("Failed to fetch disciplines", err)
  }
}

const switchTab = (tab) => {
  currentTab.value = tab
  if (tab === 'pending') {
    fetchPendingStaff()
  } else {
    fetchUsers()
  }
}

const openPrecreateModal = () => {
  if (availableDisciplines.value.length === 0) {
    fetchDisciplines()
  }
  showPrecreateModal.value = true
}

const submitPrecreate = async () => {
  savingPrecreate.value = true
  try {
    const payload = {
      ...precreateForm.value,
      username: precreateForm.value.username ? precreateForm.value.username.replace('@', '').trim() : null,
      email: precreateForm.value.email || null,
      corp_email: precreateForm.value.corp_email || null,
      barcode: precreateForm.value.barcode || null,
      phone_number: precreateForm.value.phone_number || null,
      academic_group: precreateForm.value.academic_group || null,
    }
    await staffApi.createPending(payload)
    showPrecreateModal.value = false
    // Reset form
    precreateForm.value = {
      first_name: '',
      last_name: '',
      username: '',
      academic_group: '',
      email: '',
      corp_email: '',
      barcode: '',
      phone_number: '',
      staff_role: 'manager',
      discipline_id: null,
    }
    fetchPendingStaff()
    fetchUsers()
    showToast('Сотрудник успешно предсоздан! При входе в бота он сможет забрать роль.', 'success')
  } catch (err) {
    showToast(err.response?.data?.detail || 'Ошибка создания сотрудника', 'error')
  } finally {
    savingPrecreate.value = false
  }
}

const deletePending = (p) => {
  confirmDialog.value = {
    show: true,
    title: 'Отменить приглашение',
    message: `Отменить приглашение для ${p.first_name} ${p.last_name}?`,
    confirmText: 'Отменить приглашение',
    action: async () => {
      try {
        await staffApi.deletePending(p.id)
        showToast(`Приглашение для ${p.first_name} ${p.last_name} отменено`, 'info')
        fetchPendingStaff()
      } catch (err) {
        showToast(err.response?.data?.detail || 'Ошибка удаления записи', 'error')
      }
    }
  }
}

const onFileSelected = (e) => {
  const file = e.target.files?.[0]
  if (file) {
    selectedFile.value = file
    importResult.value = null
  }
}

const uploadCsv = async () => {
  if (!selectedFile.value) return
  importing.value = true
  importResult.value = null
  const formData = new FormData()
  formData.append('file', selectedFile.value)
  try {
    const res = await staffApi.importCsv(formData)
    importResult.value = res.data
    fetchPendingStaff()
    fetchUsers()
    showToast(`Импорт завершен: создано ${res.data.created} сотрудников`, 'success')
  } catch (err) {
    showToast(err.response?.data?.detail || 'Ошибка импорта файла', 'error')
  } finally {
    importing.value = false
  }
}

const uploadText = async () => {
  if (!importTextContent.value.trim()) return
  importing.value = true
  importResult.value = null
  try {
    const res = await staffApi.importText(importTextContent.value)
    importResult.value = res.data
    fetchPendingStaff()
    fetchUsers()
    showToast(`Импорт завершен: создано ${res.data.created} сотрудников`, 'success')
  } catch (err) {
    showToast(err.response?.data?.detail || 'Ошибка импорта текста', 'error')
  } finally {
    importing.value = false
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
    showToast(`Роль для ${user.first_name} обновлена на ${newRole}`, 'success')
  } catch (err) {
    showToast(err.response?.data?.detail || "Failed to update role", 'error')
    fetchUsers()
  }
}

const deleteUser = (user) => {
  confirmDialog.value = {
    show: true,
    title: 'Удалить пользователя',
    message: `Вы уверены, что хотите удалить ${user.first_name} ${user.last_name || ''}?`,
    confirmText: 'Удалить',
    action: async () => {
      try {
        await api.delete(`/admin/users/${user.telegram_id}`)
        showToast('Пользователь успешно удален', 'info')
        fetchUsers()
      } catch (err) {
        showToast(err.response?.data?.detail || "Failed to delete user", 'error')
      }
    }
  }
}

const formatDate = (isoString) => {
  if (!isoString) return '—'
  try {
    const d = new Date(isoString)
    return d.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' })
  } catch {
    return '—'
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
  fetchPendingStaff()
  fetchDisciplines()
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

/* Mobile responsive rules */
@media (max-width: 768px) {
  .header-inner {
    padding: 0.65rem 1rem;
    padding-top: max(0.65rem, var(--sat));
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .header-left {
    width: 100%;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .nav {
    display: flex;
    overflow-x: auto;
    width: 100%;
    padding-bottom: 0.35rem;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
  }
  .nav::-webkit-scrollbar {
    display: none;
  }
  .nav-item {
    padding: 0.4rem 0.65rem;
    font-size: 0.82rem;
    white-space: nowrap;
  }
  .page-body {
    padding: 1rem 0.85rem;
  }
  .toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: 0.75rem;
  }
  .search-wrap {
    width: 100%;
  }
  .search-input {
    width: 100%;
  }
  .table-container {
    -webkit-overflow-scrolling: touch;
    border-radius: var(--radius-md);
  }
  .minimal-table {
    min-width: 680px;
  }
  .pagination {
    flex-direction: column;
    gap: 0.75rem;
    align-items: center;
  }
}

/* Tabs & Action Controls */
.toolbar-left, .toolbar-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.tab-pills {
  display: flex;
  background: rgba(255, 255, 255, 0.04);
  padding: 4px;
  border-radius: 10px;
  border: 1px solid var(--surface-border);
}

.tab-pill {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 0.82rem;
  font-weight: 600;
  padding: 6px 14px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}

.tab-pill.active {
  background: var(--surface-hover);
  color: var(--text-primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.pill-count {
  font-size: 0.7rem;
  background: rgba(255, 255, 255, 0.1);
  padding: 1px 6px;
  border-radius: 9999px;
}

.pill-count.warning {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.btn-primary {
  background: var(--accent, #ef4444);
  color: #fff;
  border: none;
  font-size: 0.82rem;
  font-weight: 700;
  padding: 7px 14px;
  border-radius: 8px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-primary:hover {
  opacity: 0.9;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.07);
  color: var(--text-primary);
  border: 1px solid var(--surface-border);
  font-size: 0.82rem;
  font-weight: 600;
  padding: 7px 14px;
  border-radius: 8px;
  cursor: pointer;
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.12);
}

/* Badges */
.staff-role-badge {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.badge-role {
  font-weight: 700;
  font-size: 0.8rem;
  color: #f59e0b;
}

.badge-sub {
  font-size: 0.68rem;
  padding: 1px 6px;
  border-radius: 4px;
  display: inline-block;
  width: fit-content;
}

.badge-sub.opened {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.badge-sub.sealed {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.staff-tag {
  background: rgba(245, 158, 11, 0.12);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.3);
  font-size: 0.75rem;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 6px;
  text-transform: uppercase;
}

.disc-pill {
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
  font-size: 0.72rem;
  font-weight: 800;
  padding: 2px 7px;
  border-radius: 6px;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

/* Modals */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(6px);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.modal-card {
  background: #111522;
  border: 1px solid var(--surface-border-hover);
  border-radius: 16px;
  width: 100%;
  max-width: 520px;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.8);
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--surface-border);
}

.modal-header h3 {
  font-size: 1.1rem;
  font-weight: 700;
  margin: 0;
}

.btn-close {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 1.1rem;
  cursor: pointer;
}

.modal-form {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-row {
  display: flex;
  gap: 1rem;
}

.form-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.form-group label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.form-input, .form-select {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--surface-border);
  color: var(--text-primary);
  padding: 0.55rem 0.75rem;
  border-radius: 8px;
  font-size: 0.85rem;
  outline: none;
}

.form-input:focus, .form-select:focus {
  border-color: var(--accent);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.btn-ghost {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0.5rem 1rem;
}

.import-hint {
  font-size: 0.82rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

.import-hint code {
  display: inline-block;
  background: rgba(255, 255, 255, 0.07);
  padding: 3px 6px;
  border-radius: 4px;
  font-size: 0.75rem;
  margin-top: 4px;
}

.import-subtabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  background: rgba(255, 255, 255, 0.04);
  padding: 4px;
  border-radius: 8px;
}

.subtab-btn {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 0.82rem;
  font-weight: 500;
  padding: 0.45rem 0.75rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.subtab-btn.active {
  background: var(--surface-card);
  color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.text-upload-box {
  width: 100%;
}

.import-textarea {
  width: 100%;
  font-size: 0.78rem;
  line-height: 1.4;
  white-space: pre;
  overflow-x: auto;
  resize: vertical;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  padding: 0.75rem;
  color: #fff;
}

.file-upload-box {
  border: 2px dashed var(--surface-border-hover);
  border-radius: 12px;
  padding: 1.5rem;
  text-align: center;
  cursor: pointer;
  position: relative;
  background: rgba(255, 255, 255, 0.02);
}

.file-upload-box input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.file-placeholder {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.file-name {
  color: #10b981;
  font-size: 0.9rem;
}

.import-result {
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
  padding: 0.75rem;
  border-radius: 8px;
  font-size: 0.85rem;
  color: #10b981;
}

.import-result.has-errors {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

.error-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 6px;
  max-height: 100px;
  overflow-y: auto;
}

/* Toast Banner */
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
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
  animation: slideDown 0.2s ease-out;
}

.toast-banner.success {
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #34d399;
}

.toast-banner.error {
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #f87171;
}

.toast-banner.info {
  background: rgba(59, 130, 246, 0.12);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: #60a5fa;
}

.toast-close {
  color: inherit;
  font-size: 0.85rem;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0 0.5rem;
}

/* Confirm Modal */
.confirm-modal-card {
  max-width: 440px !important;
  width: 95vw;
}

.confirm-body {
  padding: 1.25rem 0 0.5rem 0;
}

.confirm-message {
  font-size: 0.95rem;
  color: var(--text-primary);
  line-height: 1.5;
}

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>

