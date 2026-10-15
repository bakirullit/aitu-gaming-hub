<template>
  <div class="admin-container">
    <!-- Header -->
    <header class="header">
      <div class="header-inner">
        <div class="header-left">
          <router-link to="/admin" class="logo">
            <img src="/logo.png" alt="AITU Gaming" class="brand-logo" />
            <span class="logo-pill">Admin</span>
          </router-link>
          <nav class="nav">
            <router-link to="/tournaments" class="nav-item">Tournaments</router-link>
            <router-link to="/admin" class="nav-item">Members</router-link>
            <router-link to="/admin/disciplines" class="nav-item">Disciplines</router-link>
            <router-link to="/admin/chats" class="nav-item active">Telegram Chats</router-link>
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
      <div v-if="toast.show" class="toast" :class="toast.type">
        <span>{{ toast.message }}</span>
        <button @click="toast.show = false" class="toast-close">✕</button>
      </div>
    </transition>

    <main class="page-body">
      <!-- Toolbar -->
      <div class="toolbar">
        <div class="toolbar-title">
          <h2>Telegram Chats</h2>
          <span class="count-badge">{{ filteredChats.length }} identified</span>
        </div>

        <div class="toolbar-controls">
          <div class="search-wrap">
            <input 
              v-model="searchQuery" 
              type="text" 
              placeholder="Search chat title, @username, or ID..." 
              class="search-input"
            />
          </div>

          <label class="filter-toggle">
            <input type="checkbox" v-model="activeOnly" @change="fetchChats" />
            <span>Active only</span>
          </label>

          <button @click="fetchChats" :disabled="loading" class="btn-subtle" title="Refresh list">
            <span :class="{ 'spin-icon': loading }">🔄</span> Refresh
          </button>
        </div>
      </div>

      <!-- Chats Table -->
      <div class="table-container">
        <table v-if="!loading || chats.length > 0" class="minimal-table">
          <thead>
            <tr>
              <th>Chat / Community</th>
              <th>Chat ID</th>
              <th>Type</th>
              <th>Members</th>
              <th>Permissions</th>
              <th>Status</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="chat in filteredChats" :key="chat.chat_id">
              <td>
                <div class="chat-info-col">
                  <span class="chat-type-icon">{{ getChatIcon(chat.chat_type) }}</span>
                  <div class="chat-text">
                    <span class="chat-title">{{ chat.title }}</span>
                    <a 
                      v-if="chat.username" 
                      :href="'https://t.me/' + chat.username" 
                      target="_blank" 
                      rel="noopener" 
                      class="chat-username"
                    >
                      @{{ chat.username }} ↗
                    </a>
                  </div>
                </div>
              </td>
              <td>
                <div class="id-copy-wrap">
                  <code class="mono id-badge">{{ chat.chat_id }}</code>
                  <button 
                    @click="copyToClipboard(chat.chat_id, 'Chat ID copied!')" 
                    class="btn-copy" 
                    title="Copy Chat ID"
                  >
                    📋
                  </button>
                </div>
              </td>
              <td>
                <span class="pill-badge" :class="chat.chat_type">
                  {{ formatChatType(chat.chat_type) }}
                </span>
              </td>
              <td>
                <span class="member-count mono">
                  {{ chat.member_count != null ? chat.member_count.toLocaleString() : '—' }}
                </span>
              </td>
              <td>
                <span 
                  class="badge-permission" 
                  :class="chat.can_invite_users ? 'perm-yes' : 'perm-no'"
                >
                  {{ chat.can_invite_users ? '🔑 Invites Allowed' : '🔒 No Invite Rights' }}
                </span>
              </td>
              <td>
                <div class="status-dot-wrap">
                  <span class="status-dot" :class="chat.is_active ? 'active' : 'inactive'"></span>
                  <span class="status-text">{{ chat.is_active ? 'Active' : 'Bot Removed' }}</span>
                </div>
              </td>
              <td class="text-right">
                <div class="actions">
                  <button 
                    @click="syncChat(chat)" 
                    :disabled="syncingId === chat.chat_id" 
                    class="btn-subtle small" 
                    title="Sync metadata from Telegram"
                  >
                    {{ syncingId === chat.chat_id ? 'Syncing...' : '🔄 Sync' }}
                  </button>
                  <button 
                    @click="openInviteModal(chat)" 
                    :disabled="!chat.is_active || !chat.can_invite_users" 
                    class="btn-invite small" 
                    :title="chat.can_invite_users ? 'Create invite link' : 'Bot needs admin rights with invite users permission'"
                  >
                    🔗 Invite Link
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="filteredChats.length === 0 && !loading">
              <td colspan="7" class="empty-state">
                <div class="empty-wrap">
                  <p class="empty-title">No Telegram chats found</p>
                  <p class="empty-sub">
                    Add the bot to a Telegram group or channel and make it an admin to see it appear here automatically.
                  </p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="loading" class="loading-overlay">
          <div class="minimal-spinner"></div>
        </div>
      </div>
    </main>

    <!-- Modal: Generate Invite Link -->
    <transition name="fade">
      <div v-if="showInviteModal" class="modal-overlay" @click.self="closeInviteModal">
        <div class="modal">
          <div class="modal-top">
            <h3 class="modal-heading">Create Invite Link</h3>
            <button @click="closeInviteModal" class="btn-close">✕</button>
          </div>

          <div class="modal-body">
            <p class="modal-chat-meta">
              Target: <b>{{ selectedChat?.title }}</b> (<code>{{ selectedChat?.chat_id }}</code>)
            </p>

            <form @submit.prevent="generateInviteLink">
              <div class="form-group">
                <label>Link Name (Optional)</label>
                <input 
                  v-model="inviteForm.name" 
                  type="text" 
                  maxlength="32" 
                  placeholder="e.g. CS2 Tournament Players" 
                  class="form-input"
                />
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label>Expiration</label>
                  <select v-model="inviteForm.duration" class="form-input">
                    <option value="none">No expiration (Permanent)</option>
                    <option value="1h">1 Hour</option>
                    <option value="1d">1 Day (24 hours)</option>
                    <option value="7d">7 Days (1 week)</option>
                    <option value="30d">30 Days</option>
                  </select>
                </div>

                <div class="form-group">
                  <label>Member Limit (Optional)</label>
                  <input 
                    v-model.number="inviteForm.member_limit" 
                    type="number" 
                    min="1" 
                    max="99999" 
                    placeholder="Unlimited" 
                    class="form-input"
                  />
                </div>
              </div>

              <!-- Generated Link Display -->
              <div v-if="generatedLink" class="generated-link-box">
                <label class="generated-label">Generated Link:</label>
                <div class="link-copy-row">
                  <input 
                    :value="generatedLink" 
                    readonly 
                    class="form-input mono link-text" 
                  />
                  <button 
                    type="button" 
                    @click="copyToClipboard(generatedLink, 'Invite link copied!')" 
                    class="btn-primary-action"
                  >
                    Copy
                  </button>
                </div>
              </div>

              <div class="modal-actions">
                <button type="button" @click="closeInviteModal" class="btn-subtle">
                  {{ generatedLink ? 'Close' : 'Cancel' }}
                </button>
                <button 
                  type="submit" 
                  :disabled="generatingLink" 
                  class="btn-primary-action"
                >
                  {{ generatingLink ? 'Generating...' : (generatedLink ? 'Generate Another' : 'Generate Link') }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { chatApi } from '../services/api'

const router = useRouter()

const chats = ref([])
const loading = ref(false)
const searchQuery = ref('')
const activeOnly = ref(true)
const syncingId = ref(null)

const currentUser = ref(null)

const toast = ref({
  show: false,
  message: '',
  type: 'info',
})

const showToast = (message, type = 'info') => {
  toast.value = { show: true, message, type }
  setTimeout(() => {
    toast.value.show = false
  }, 4000)
}

const loadCurrentUser = () => {
  try {
    const raw = localStorage.getItem('user')
    if (raw) currentUser.value = JSON.parse(raw)
  } catch (e) {
    currentUser.value = null
  }
}

const logout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user')
  router.push('/login')
}

// Fetch chats
const fetchChats = async () => {
  loading.value = true
  try {
    const res = await chatApi.getChats({ active_only: activeOnly.value })
    chats.value = res.data || []
  } catch (err) {
    showToast(err.response?.data?.detail || 'Failed to fetch chats', 'error')
  } finally {
    loading.value = false
  }
}

// Filtered chats list
const filteredChats = computed(() => {
  if (!searchQuery.value.trim()) return chats.value
  const q = searchQuery.value.toLowerCase().trim()
  return chats.value.filter(c => {
    const title = (c.title || '').toLowerCase()
    const username = (c.username || '').toLowerCase()
    const idStr = String(c.chat_id)
    return title.includes(q) || username.includes(q) || idStr.includes(q)
  })
})

// Sync chat
const syncChat = async (chat) => {
  syncingId.value = chat.chat_id
  try {
    const res = await chatApi.syncChat(chat.chat_id)
    const updated = res.data
    const idx = chats.value.findIndex(c => c.chat_id === chat.chat_id)
    if (idx !== -1) {
      chats.value[idx] = updated
    }
    showToast(`Chat '${updated.title}' metadata synchronized!`, 'success')
  } catch (err) {
    showToast(err.response?.data?.detail || 'Failed to sync chat', 'error')
  } finally {
    syncingId.value = null
  }
}

// Invite link modal state
const showInviteModal = ref(false)
const selectedChat = ref(null)
const generatingLink = ref(false)
const generatedLink = ref('')

const inviteForm = ref({
  name: '',
  duration: 'none',
  member_limit: null,
})

const openInviteModal = (chat) => {
  selectedChat.value = chat
  generatedLink.value = ''
  inviteForm.value = {
    name: '',
    duration: 'none',
    member_limit: null,
  }
  showInviteModal.value = true
}

const closeInviteModal = () => {
  showInviteModal.value = false
  selectedChat.value = null
  generatedLink.value = ''
}

const generateInviteLink = async () => {
  if (!selectedChat.value) return
  generatingLink.value = true

  let expireDate = null
  const nowSec = Math.floor(Date.now() / 1000)
  if (inviteForm.value.duration === '1h') expireDate = nowSec + 3600
  else if (inviteForm.value.duration === '1d') expireDate = nowSec + 86400
  else if (inviteForm.value.duration === '7d') expireDate = nowSec + 604800
  else if (inviteForm.value.duration === '30d') expireDate = nowSec + 2592000

  try {
    const payload = {
      name: inviteForm.value.name.trim() || null,
      expire_date: expireDate,
      member_limit: inviteForm.value.member_limit || null,
    }
    const res = await chatApi.createInviteLink(selectedChat.value.chat_id, payload)
    generatedLink.value = res.data.invite_link
    showToast('Invite link generated successfully!', 'success')
  } catch (err) {
    showToast(err.response?.data?.detail || 'Failed to create invite link', 'error')
  } finally {
    generatingLink.value = false
  }
}

const copyToClipboard = async (text, successMsg = 'Copied!') => {
  try {
    await navigator.clipboard.writeText(String(text))
    showToast(successMsg, 'success')
  } catch (err) {
    showToast('Failed to copy', 'error')
  }
}

const getChatIcon = (type) => {
  switch (type) {
    case 'channel': return '📢'
    case 'supergroup': return '👥'
    case 'group': return '💬'
    default: return '💬'
  }
}

const formatChatType = (type) => {
  switch (type) {
    case 'channel': return 'Channel'
    case 'supergroup': return 'Supergroup'
    case 'group': return 'Group'
    default: return type
  }
}

onMounted(() => {
  loadCurrentUser()
  fetchChats()
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
}

.logo-pill {
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  background: rgba(99, 102, 241, 0.2);
  color: #818cf8;
  padding: 2px 6px;
  border-radius: 4px;
}

.nav {
  display: flex;
  gap: 0.5rem;
}

.nav-item {
  color: var(--text-muted, #94a3b8);
  text-decoration: none;
  font-size: 0.875rem;
  padding: 0.4rem 0.75rem;
  border-radius: 6px;
  transition: all 0.2s;
}

.nav-item:hover, .nav-item.active {
  color: #fff;
  background: rgba(255, 255, 255, 0.06);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.admin-user {
  font-size: 0.875rem;
  color: var(--text-muted, #94a3b8);
}

.btn-ghost {
  background: none;
  border: none;
  color: var(--text-muted, #94a3b8);
  font-size: 0.875rem;
  cursor: pointer;
  padding: 0.35rem 0.6rem;
  border-radius: 6px;
}

.btn-ghost:hover {
  background: rgba(255, 255, 255, 0.06);
}

.text-danger {
  color: #ef4444 !important;
}

/* Page Body */
.page-body {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
}

/* Toolbar */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.toolbar-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.toolbar-title h2 {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0;
}

.count-badge {
  font-size: 0.75rem;
  background: rgba(255, 255, 255, 0.07);
  padding: 2px 8px;
  border-radius: 999px;
  color: #94a3b8;
}

.toolbar-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.search-wrap {
  min-width: 260px;
}

.search-input {
  width: 100%;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 0.45rem 0.85rem;
  color: #fff;
  font-size: 0.875rem;
}

.search-input:focus {
  outline: none;
  border-color: #6366f1;
}

.filter-toggle {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.85rem;
  color: #94a3b8;
  cursor: pointer;
  user-select: none;
}

/* Buttons */
.btn-subtle {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #e2e8f0;
  padding: 0.45rem 0.85rem;
  border-radius: 8px;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-subtle:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
}

.btn-subtle.small {
  padding: 0.3rem 0.6rem;
  font-size: 0.775rem;
}

.btn-invite {
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.35);
  color: #a5b4fc;
  padding: 0.3rem 0.65rem;
  border-radius: 6px;
  font-size: 0.775rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-invite:hover:not(:disabled) {
  background: rgba(99, 102, 241, 0.28);
  color: #fff;
}

.btn-invite:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-primary-action {
  background: #6366f1;
  color: #fff;
  border: none;
  padding: 0.5rem 1.1rem;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary-action:hover:not(:disabled) {
  background: #4f46e5;
}

.spin-icon {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Table */
.table-container {
  background: rgba(15, 17, 23, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
  overflow-x: auto;
  position: relative;
}

.minimal-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.minimal-table th {
  text-align: left;
  padding: 0.85rem 1.25rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.minimal-table td {
  padding: 0.95rem 1.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  vertical-align: middle;
}

.minimal-table tr:hover td {
  background: rgba(255, 255, 255, 0.02);
}

.text-right {
  text-align: right;
}

/* Chat Columns */
.chat-info-col {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.chat-type-icon {
  font-size: 1.2rem;
}

.chat-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.chat-title {
  font-weight: 600;
  color: #f1f5f9;
}

.chat-username {
  font-size: 0.775rem;
  color: #6366f1;
  text-decoration: none;
}

.chat-username:hover {
  text-decoration: underline;
}

.id-copy-wrap {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.id-badge {
  font-size: 0.8rem;
  background: rgba(255, 255, 255, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  color: #94a3b8;
}

.btn-copy {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.85rem;
  opacity: 0.6;
  padding: 2px;
  transition: opacity 0.2s;
}

.btn-copy:hover {
  opacity: 1;
}

/* Badges */
.pill-badge {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 999px;
  text-transform: capitalize;
}

.pill-badge.supergroup {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.pill-badge.channel {
  background: rgba(168, 85, 247, 0.15);
  color: #c084fc;
}

.pill-badge.group {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
}

.badge-permission {
  font-size: 0.75rem;
  font-weight: 500;
  padding: 3px 8px;
  border-radius: 6px;
}

.perm-yes {
  background: rgba(16, 185, 129, 0.12);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.25);
}

.perm-no {
  background: rgba(255, 255, 255, 0.05);
  color: #94a3b8;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.status-dot-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.active {
  background: #10b981;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
}

.status-dot.inactive {
  background: #ef4444;
}

.status-text {
  font-size: 0.8rem;
  color: #cbd5e1;
}

.actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
}

/* Modals */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
}

.modal {
  width: 100%;
  max-width: 480px;
  background: #0f1117;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  padding: 1.75rem;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
}

.modal-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
}

.modal-heading {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0;
}

.btn-close {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 1.1rem;
  cursor: pointer;
}

.modal-chat-meta {
  font-size: 0.85rem;
  color: #94a3b8;
  margin-bottom: 1.25rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  font-size: 0.775rem;
  font-weight: 600;
  color: #94a3b8;
  margin-bottom: 0.35rem;
  text-transform: uppercase;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-input {
  width: 100%;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 0.55rem 0.85rem;
  color: #fff;
  font-size: 0.875rem;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: #6366f1;
}

.generated-link-box {
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.25);
  border-radius: 8px;
  padding: 0.85rem;
  margin-bottom: 1.25rem;
}

.generated-label {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  color: #818cf8;
  margin-bottom: 0.4rem;
}

.link-copy-row {
  display: flex;
  gap: 0.5rem;
}

.link-text {
  flex: 1;
  background: rgba(0, 0, 0, 0.4);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

/* Toast */
.toast {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  z-index: 200;
  padding: 0.85rem 1.25rem;
  border-radius: 8px;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
}

.toast.success {
  background: #065f46;
  border: 1px solid #10b981;
  color: #ecfdf5;
}

.toast.error {
  background: #7f1d1d;
  border: 1px solid #ef4444;
  color: #fef2f2;
}

.toast.info {
  background: #1e1b4b;
  border: 1px solid #6366f1;
  color: #e0e7ff;
}

.toast-close {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
}

.empty-state {
  text-align: center;
  padding: 3rem 1.5rem;
}

.empty-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #cbd5e1;
  margin-bottom: 0.5rem;
}

.empty-sub {
  font-size: 0.85rem;
  color: #64748b;
  max-width: 420px;
  margin: 0 auto;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
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
  .toolbar-actions {
    flex-direction: column;
    width: 100%;
    gap: 0.5rem;
  }
  .search-wrap {
    width: 100%;
  }
  .search-input {
    width: 100%;
  }
  .btn-sync-all {
    width: 100%;
    justify-content: center;
  }
  .table-container {
    -webkit-overflow-scrolling: touch;
    border-radius: var(--radius-md);
  }
  .minimal-table {
    min-width: 650px;
  }
  .modal-box {
    width: 95vw;
    max-width: 95vw;
    margin: 1rem auto;
    padding: 1.25rem;
  }
  .form-row {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }
}
</style>

