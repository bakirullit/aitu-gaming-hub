<template>
  <div class="admin-shell">
    <!-- LEFT SIDEBAR -->
    <aside class="admin-sidebar" :class="{ 'collapsed': isCollapsed, 'mobile-open': isMobileOpen }">
      <!-- Sidebar Header / Brand -->
      <div class="sidebar-header">
        <router-link to="/admin/dashboard" class="brand">
          <img src="/logo.png" alt="AITU Gaming" class="brand-logo" />
          <div class="brand-info" v-show="!isCollapsed">
            <span class="brand-title">AITU GAMING</span>
            <span class="brand-badge">ADMIN PANEL</span>
          </div>
        </router-link>
        <button 
          class="btn-collapse" 
          @click="toggleCollapse" 
          :title="isCollapsed ? 'Развернуть меню' : 'Свернуть меню'"
        >
          <span class="collapse-arrow">{{ isCollapsed ? '›' : '‹' }}</span>
        </button>
      </div>

      <!-- Navigation Sections -->
      <nav class="sidebar-nav custom-scroll">
        <!-- 1. ОБЗОР -->
        <div class="nav-section">
          <div class="section-heading" v-show="!isCollapsed">ОБЗОР</div>
          <router-link 
            to="/admin/dashboard" 
            class="nav-link" 
            active-class="active"
            :title="isCollapsed ? 'Дашборд и Аналитика' : ''"
            @click="closeMobile"
          >
            <span class="nav-icon">📊</span>
            <span class="nav-text" v-show="!isCollapsed">Дашборд</span>
          </router-link>
        </div>

        <!-- 2. КИБЕРСПОРТ -->
        <div class="nav-section">
          <div class="section-heading" v-show="!isCollapsed">КИБЕРСПОРТ</div>
          
          <router-link 
            to="/admin/tournaments" 
            class="nav-link" 
            active-class="active"
            :title="isCollapsed ? 'Турниры & Заявки' : ''"
            @click="closeMobile"
          >
            <span class="nav-icon">🏆</span>
            <span class="nav-text" v-show="!isCollapsed">Турниры & Заявки</span>
          </router-link>

          <router-link 
            to="/admin/disciplines" 
            class="nav-link" 
            active-class="active"
            :title="isCollapsed ? 'Дисциплины' : ''"
            @click="closeMobile"
          >
            <span class="nav-icon">🎮</span>
            <span class="nav-text" v-show="!isCollapsed">Дисциплины</span>
          </router-link>

          <router-link 
            to="/admin" 
            class="nav-link" 
            :class="{ active: $route.path === '/admin' }"
            :title="isCollapsed ? 'Участники & Роли' : ''"
            @click="closeMobile"
          >
            <span class="nav-icon">👥</span>
            <span class="nav-text" v-show="!isCollapsed">Участники & Staff</span>
          </router-link>

          <router-link 
            to="/admin/chats" 
            class="nav-link" 
            active-class="active"
            :title="isCollapsed ? 'Telegram Чаты' : ''"
            @click="closeMobile"
          >
            <span class="nav-icon">💬</span>
            <span class="nav-text" v-show="!isCollapsed">Telegram Чаты</span>
          </router-link>
        </div>

        <!-- 3. СЕРВИСЫ -->
        <div class="nav-section">
          <div class="section-heading" v-show="!isCollapsed">СЕРВИСЫ ХАБА</div>

          <router-link 
            to="/admin/helpdesk" 
            class="nav-link" 
            active-class="active"
            :title="isCollapsed ? 'Тикеты поддержки' : ''"
            @click="closeMobile"
          >
            <span class="nav-icon">🎫</span>
            <span class="nav-text" v-show="!isCollapsed">Тикеты поддержки</span>
          </router-link>

          <router-link 
            to="/admin/minecraft" 
            class="nav-link" 
            active-class="active"
            :title="isCollapsed ? 'Сервер Minecraft' : ''"
            @click="closeMobile"
          >
            <span class="nav-icon">⛏️</span>
            <span class="nav-text" v-show="!isCollapsed">Minecraft Сервер</span>
          </router-link>

          <router-link 
            to="/admin/broadcast" 
            class="nav-link" 
            active-class="active"
            :title="isCollapsed ? 'Массовая Рассылка' : ''"
            @click="closeMobile"
          >
            <span class="nav-icon">📢</span>
            <span class="nav-text" v-show="!isCollapsed">Рассылка анонсов</span>
          </router-link>

          <router-link 
            to="/admin/lootbox" 
            class="nav-link" 
            active-class="active"
            :title="isCollapsed ? 'Mystery Box / Staff' : ''"
            @click="closeMobile"
          >
            <span class="nav-icon">🎁</span>
            <span class="nav-text" v-show="!isCollapsed">Mystery Box Staff</span>
          </router-link>
        </div>

        <!-- 4. СИСТЕМА -->
        <div class="nav-section">
          <div class="section-heading" v-show="!isCollapsed">СИСТЕМА</div>

          <router-link 
            to="/admin/logs" 
            class="nav-link" 
            active-class="active"
            :title="isCollapsed ? 'Логи & Здоровье' : ''"
            @click="closeMobile"
          >
            <span class="nav-icon">🛡️</span>
            <span class="nav-text" v-show="!isCollapsed">Аудит & Здоровье</span>
          </router-link>

          <router-link 
            to="/admin/settings" 
            class="nav-link" 
            active-class="active"
            :title="isCollapsed ? 'Настройки клуба' : ''"
            @click="closeMobile"
          >
            <span class="nav-icon">⚙️</span>
            <span class="nav-text" v-show="!isCollapsed">Настройки хаба</span>
          </router-link>
        </div>
      </nav>

      <!-- Sidebar Footer -->
      <div class="sidebar-footer">
        <a 
          href="/tournaments" 
          target="_blank" 
          class="btn-public-link"
          :title="isCollapsed ? 'Публичная витрина' : ''"
        >
          <span class="public-icon">🌐</span>
          <span class="public-text" v-show="!isCollapsed">Публичный сайт</span>
          <span class="public-arrow" v-show="!isCollapsed">↗</span>
        </a>

        <!-- User profile snippet -->
        <div class="user-snippet">
          <div class="user-avatar">{{ userInitial }}</div>
          <div class="user-meta" v-show="!isCollapsed">
            <span class="user-name">{{ userName }}</span>
            <span class="user-role">{{ roleName }}</span>
          </div>
          <button 
            @click="logout" 
            class="btn-logout" 
            :title="`Выйти (${userName})`"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
              <polyline points="16 17 21 12 16 7"></polyline>
              <line x1="21" y1="12" x2="9" y2="12"></line>
            </svg>
          </button>
        </div>
      </div>
    </aside>

    <!-- MOBILE OVERLAY BACKDROP -->
    <div 
      v-if="isMobileOpen" 
      class="sidebar-backdrop" 
      @click="isMobileOpen = false"
    ></div>

    <!-- MAIN APP CANVAS -->
    <div class="admin-main-wrap" :class="{ 'expanded': isCollapsed }">
      <!-- Minimalist Top Bar -->
      <header class="admin-topbar">
        <div class="topbar-left">
          <button class="mobile-menu-btn" @click="isMobileOpen = !isMobileOpen">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
          </button>
          
          <div class="breadcrumb">
            <span class="bc-root">Admin</span>
            <span class="bc-sep">/</span>
            <span class="bc-current">{{ currentRouteTitle }}</span>
          </div>
        </div>

        <div class="topbar-right">
          <div class="health-pill" title="Система подключена">
            <span class="pulse-indicator"></span>
            <span class="health-label">System Active</span>
          </div>

          <div class="admin-profile-pill">
            <div class="pill-dot"></div>
            <span class="pill-name">{{ userName }}</span>
            <span class="pill-tag">{{ roleBadge }}</span>
          </div>
        </div>
      </header>

      <!-- Routed Content -->
      <main class="admin-body">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const isCollapsed = ref(false)
const isMobileOpen = ref(false)
const currentUser = ref(null)

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

const closeMobile = () => {
  isMobileOpen.value = false
}

onMounted(() => {
  try {
    const raw = localStorage.getItem('user')
    if (raw) currentUser.value = JSON.parse(raw)
  } catch (err) {
    currentUser.value = null
  }
})

const userName = computed(() => {
  if (!currentUser.value) return 'Admin'
  return currentUser.value.first_name || currentUser.value.username || 'Admin'
})

const userInitial = computed(() => {
  const name = userName.value
  return name ? name.charAt(0).toUpperCase() : 'A'
})

const roleName = computed(() => {
  const role = currentUser.value?.role || 'head_admin'
  const mapping = {
    head_admin: 'Head Admin',
    discipline_admin: 'Discipline Curator',
    admin: 'Administrator',
    staff: 'Club Staff',
  }
  return mapping[role] || 'Administrator'
})

const roleBadge = computed(() => {
  const role = currentUser.value?.role || 'head_admin'
  if (role === 'head_admin') return 'LEAD'
  if (role === 'discipline_admin') return 'CURATOR'
  return 'STAFF'
})

const currentRouteTitle = computed(() => {
  const path = route.path
  if (path.includes('/admin/dashboard')) return 'Дашборд & Аналитика'
  if (path.includes('/admin/tournaments')) return 'Турниры & Модерация'
  if (path.includes('/admin/disciplines')) return 'Дисциплины клуба'
  if (path.includes('/admin/helpdesk')) return 'Служба поддержки'
  if (path.includes('/admin/minecraft')) return 'Сервер Minecraft'
  if (path.includes('/admin/chats')) return 'Telegram Чаты'
  if (path.includes('/admin/broadcast')) return 'Рассылка анонсов'
  if (path.includes('/admin/lootbox')) return 'Mystery Box / Staff'
  if (path.includes('/admin/logs')) return 'Логи & Здоровье'
  if (path.includes('/admin/settings')) return 'Настройки клуба'
  if (path === '/admin') return 'Участники & Роли'
  return 'Панель управления'
})

const logout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user')
  router.push('/login')
}
</script>

<style scoped>
.admin-shell {
  display: flex;
  min-height: 100vh;
  background-color: #08090d;
  color: #f1f3f9;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  overflow-x: hidden;
}

/* =========================================================
   SIDEBAR
   ========================================================= */
.admin-sidebar {
  width: 260px;
  min-width: 260px;
  height: 100vh;
  position: sticky;
  top: 0;
  background: #0d0f18;
  border-right: 1px solid rgba(255, 255, 255, 0.07);
  display: flex;
  flex-direction: column;
  z-index: 90;
  transition: width 0.22s cubic-bezier(0.4, 0, 0.2, 1), min-width 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.admin-sidebar.collapsed {
  width: 76px;
  min-width: 76px;
}

/* Header */
.sidebar-header {
  height: 64px;
  padding: 0 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(13, 15, 24, 0.95);
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  text-decoration: none;
  color: inherit;
  overflow: hidden;
}

.brand-logo {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  object-fit: contain;
  flex-shrink: 0;
}

.brand-info {
  display: flex;
  flex-direction: column;
  white-space: nowrap;
}

.brand-title {
  font-size: 0.88rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: #ffffff;
}

.brand-badge {
  font-size: 0.65rem;
  font-weight: 700;
  color: #ef4444;
  letter-spacing: 0.08em;
}

.btn-collapse {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #94a3b8;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}

.btn-collapse:hover {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.3);
}

.collapse-arrow {
  font-size: 1.1rem;
  line-height: 1;
}

/* Navigation Scroll */
.sidebar-nav {
  flex: 1;
  padding: 1rem 0.65rem;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.custom-scroll::-webkit-scrollbar {
  width: 4px;
}
.custom-scroll::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

.nav-section {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.section-heading {
  font-size: 0.68rem;
  font-weight: 700;
  color: #64748b;
  letter-spacing: 0.08em;
  padding: 0 0.65rem 0.4rem;
  text-transform: uppercase;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  padding: 0.55rem 0.75rem;
  border-radius: 8px;
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.86rem;
  font-weight: 500;
  transition: all 0.15s ease;
  white-space: nowrap;
  border-left: 3px solid transparent;
}

.nav-link:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.05);
}

.nav-link.active {
  color: #ffffff;
  background: linear-gradient(90deg, rgba(239, 68, 68, 0.14) 0%, rgba(239, 68, 68, 0.03) 100%);
  border-left-color: #ef4444;
  font-weight: 600;
}

.nav-icon {
  font-size: 1.05rem;
  width: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* Footer */
.sidebar-footer {
  padding: 0.85rem 0.65rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(13, 15, 24, 0.98);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.btn-public-link {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: #94a3b8;
  font-size: 0.8rem;
  text-decoration: none;
  transition: all 0.15s;
}

.btn-public-link:hover {
  color: #38bdf8;
  border-color: rgba(56, 189, 248, 0.3);
  background: rgba(56, 189, 248, 0.08);
}

.public-arrow {
  margin-left: auto;
  font-size: 0.85rem;
  opacity: 0.7;
}

.user-snippet {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.45rem 0.5rem;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.02);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.85rem;
  flex-shrink: 0;
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.3);
}

.user-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.user-name {
  font-size: 0.82rem;
  font-weight: 600;
  color: #f1f3f9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-role {
  font-size: 0.68rem;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.btn-logout {
  background: transparent;
  border: none;
  color: #64748b;
  padding: 0.35rem;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  flex-shrink: 0;
}

.btn-logout:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.12);
}

/* =========================================================
   MAIN APP CANVAS & TOPBAR
   ========================================================= */
.admin-main-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #090a10;
}

.admin-topbar {
  height: 64px;
  padding: 0 1.75rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(10, 12, 18, 0.85);
  backdrop-filter: blur(12px);
  position: sticky;
  top: 0;
  z-index: 40;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.mobile-menu-btn {
  display: none;
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.88rem;
}

.bc-root {
  color: #64748b;
  font-weight: 500;
}

.bc-sep {
  color: #334155;
}

.bc-current {
  color: #ffffff;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.health-pill {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.3rem 0.75rem;
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.2);
  border-radius: 9999px;
  font-size: 0.72rem;
  color: #10b981;
  font-weight: 600;
}

.pulse-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
  animation: pulse-ring 2s infinite;
}

@keyframes pulse-ring {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.6); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.admin-profile-pill {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.8rem;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 8px;
}

.pill-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #ef4444;
}

.pill-name {
  font-size: 0.82rem;
  font-weight: 600;
  color: #f1f3f9;
}

.pill-tag {
  font-size: 0.65rem;
  font-weight: 800;
  padding: 0.15rem 0.4rem;
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  border-radius: 4px;
}

.admin-body {
  flex: 1;
  min-height: calc(100vh - 64px);
  overflow-y: auto;
}

/* =========================================================
   RESPONSIVE DESIGN (TABLETS / MOBILE)
   ========================================================= */
@media (max-width: 1024px) {
  .mobile-menu-btn {
    display: block;
  }

  .admin-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    transform: translateX(-100%);
    transition: transform 0.25s ease;
  }

  .admin-sidebar.mobile-open {
    transform: translateX(0);
  }

  .sidebar-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(4px);
    z-index: 85;
  }

  .btn-collapse {
    display: none;
  }
}
</style>
