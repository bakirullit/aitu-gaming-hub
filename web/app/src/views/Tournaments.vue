<template>
  <div class="tournaments-page">
    <!-- Top Navigation Header (Esports Charts Style with Red Accents) -->
    <header class="header">
      <div class="header-inner">
        <div class="header-left">
          <router-link to="/tournaments" class="logo">
            <img src="/logo.png" alt="AITU Gaming" class="brand-logo" />
            <span class="logo-pill">Hub</span>
          </router-link>
          <nav class="nav">
            <router-link to="/tournaments" class="nav-item active">Tournaments</router-link>
            <router-link v-if="isAuthenticated" to="/admin" class="nav-item">Members</router-link>
            <router-link v-if="isAuthenticated" to="/admin/disciplines" class="nav-item">Disciplines</router-link>
          </nav>
        </div>

        <div class="header-right">
          <a 
            :href="`https://t.me/${botUsername}`" 
            target="_blank" 
            rel="noopener noreferrer" 
            class="btn-tg"
          >
            <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.75-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
            </svg>
            <span>Telegram Bot</span>
          </a>

          <div v-if="isAuthenticated" class="auth-box">
            <router-link to="/admin" class="btn-ghost">Admin Panel</router-link>
            <button @click="logout" class="btn-ghost text-danger">Logout</button>
          </div>
          <div v-else>
            <router-link to="/login" class="btn-ghost">Sign In</router-link>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Container -->
    <main class="page-container">
      <!-- Breadcrumb & Page Title -->
      <section class="page-head">
        <div class="breadcrumb">
          <span>AITU Gaming Hub</span>
          <span class="sep">›</span>
          <span class="curr">Upcoming esports events</span>
        </div>

        <div class="title-row">
          <h1 class="main-title">Upcoming Esports Events</h1>
          <div class="title-actions">
            <a 
              :href="`https://t.me/${botUsername}`" 
              target="_blank" 
              rel="noopener noreferrer" 
              class="btn-red-action"
            >
              <span>+ Register Team</span>
            </a>
          </div>
        </div>
      </section>

      <!-- Filter Controls (Esports Charts Design) -->
      <section class="filter-panel">
        <!-- Top filter row -->
        <div class="filter-top">
          <!-- Game / Discipline Dropdown -->
          <div class="filter-select-wrap">
            <select v-model="selectedDiscipline" @change="fetchTournaments" class="filter-select">
              <option value="ALL">All Games / Categories</option>
              <option v-for="d in availableDisciplines" :key="d.slug" :value="d.slug">
                {{ d.name }}
              </option>
            </select>
          </div>

          <!-- Status Dropdown / Chips -->
          <div class="filter-chips">
            <button 
              v-for="st in statusOptions" 
              :key="st.key" 
              :class="['filter-btn', { active: selectedStatus === st.key }]"
              @click="selectStatus(st.key)"
            >
              {{ st.label }}
            </button>
          </div>
        </div>

        <!-- Popular Filters Row with Official Game Logos -->
        <div class="popular-row">
          <span class="popular-label">Popular games:</span>
          <div class="popular-chips">
            <button 
              :class="['popular-chip', { active: selectedDiscipline === 'ALL' }]"
              @click="selectDiscipline('ALL')"
            >
              All
            </button>
            <button 
              v-for="disc in availableDisciplines" 
              :key="disc.slug"
              :class="['popular-chip', { active: selectedDiscipline === disc.slug }]"
              @click="selectDiscipline(disc.slug)"
            >
              <GameLogo :discipline="disc.slug" :size="16" />
              <span>{{ disc.name }}</span>
            </button>
          </div>
        </div>

        <!-- Search & View Bar -->
        <div class="search-bar-row">
          <div class="search-box">
            <svg class="search-svg" viewBox="0 0 20 20" width="15" height="15" fill="currentColor">
              <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd"/>
            </svg>
            <input 
              v-model="searchQuery" 
              @input="onSearchInput"
              type="text" 
              placeholder="Search tournament by name..." 
              class="search-field"
            />
            <button v-if="searchQuery" @click="searchQuery = ''; fetchTournaments()" class="clear-search">✕</button>
          </div>

          <div class="bar-right">
            <!-- Sort dropdown -->
            <div class="sort-wrap">
              <span class="sort-lbl">Sort by:</span>
              <select v-model="sortBy" class="sort-select">
                <option value="date_asc">Event Date</option>
                <option value="date_desc">Newest First</option>
              </select>
            </div>

            <!-- View switch -->
            <div class="view-toggle">
              <button 
                :class="['toggle-btn', { active: currentView === 'table' }]"
                @click="currentView = 'table'"
                title="Table View"
              >
                Table
              </button>
              <button 
                :class="['toggle-btn', { active: currentView === 'grid' }]"
                @click="currentView = 'grid'"
                title="Cards View"
              >
                Cards
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- 2-Column Esports Charts Layout -->
      <div class="layout-grid">
        <!-- Left / Primary Column -->
        <div class="main-column">
          <!-- Loading State -->
          <div v-if="loading" class="state-container">
            <div class="red-spinner"></div>
            <span>Loading esports events...</span>
          </div>

          <!-- Empty State -->
          <div v-else-if="filteredTournaments.length === 0" class="state-container">
            <h4>No tournaments found</h4>
            <p>No events match your current filter criteria.</p>
            <button @click="resetFilters" class="btn-reset">Reset Filters</button>
          </div>

          <!-- TABLE VIEW (Esports Charts Main Table) -->
          <div v-else-if="currentView === 'table'" class="table-card">
            <table class="esports-table">
              <thead>
                <tr>
                  <th class="col-game">Game</th>
                  <th class="col-name">Tournament</th>
                  <th class="col-format">Format</th>
                  <th class="col-date">Event Date</th>
                  <th class="col-status">Status</th>
                  <th class="col-action text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                <tr 
                  v-for="t in sortedTournaments" 
                  :key="t.id"
                  :class="{ 'row-past': t.is_past }"
                >
                  <td class="col-game">
                    <GameLogo :discipline="t.discipline" :size="24" />
                  </td>
                  <td class="col-name">
                    <div class="event-title-wrap">
                      <span class="event-title" @click="openModal(t)">{{ t.title }}</span>
                      <span class="event-sub">
                        {{ t.discipline }} • Hosted by {{ t.creator_name || 'AITU Esports' }}
                      </span>
                    </div>
                  </td>
                  <td class="col-format">
                    <span class="format-badge">{{ t.format_label }}</span>
                  </td>
                  <td class="col-date">
                    <div class="date-val">{{ formatDate(t.booking_date) }}</div>
                    <span class="date-rel" :class="getDaysClass(t.days_until)">
                      {{ formatDaysUntil(t.days_until) }}
                    </span>
                  </td>
                  <td class="col-status">
                    <div class="status-wrap">
                      <span class="status-indicator-dot" :class="t.status.toLowerCase()"></span>
                      <span class="status-label">{{ formatStatus(t.status) }}</span>
                    </div>
                  </td>
                  <td class="col-action text-right">
                    <div class="action-cell-btns">
                      <button @click="openModal(t)" class="btn-subtle" title="Event Details">
                        Details
                      </button>
                      <a 
                        :href="t.bot_registration_url" 
                        target="_blank" 
                        rel="noopener noreferrer" 
                        class="btn-row-register"
                        :class="{ disabled: t.is_past }"
                      >
                        {{ t.is_past ? 'Ended' : 'Register ↗' }}
                      </a>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- CARDS VIEW -->
          <div v-else-if="currentView === 'grid'" class="cards-grid">
            <article 
              v-for="t in sortedTournaments" 
              :key="t.id"
              class="event-card"
              :class="{ 'card-past': t.is_past }"
            >
              <div class="event-card-top">
                <div class="card-game-info">
                  <GameLogo :discipline="t.discipline" :size="28" />
                  <div>
                    <span class="card-disc-name">{{ t.discipline }}</span>
                    <span class="card-host">Host: {{ t.creator_name || 'AITU' }}</span>
                  </div>
                </div>
                <div class="status-wrap">
                  <span class="status-indicator-dot" :class="t.status.toLowerCase()"></span>
                  <span class="status-label">{{ formatStatus(t.status) }}</span>
                </div>
              </div>

              <h3 class="event-card-title" @click="openModal(t)">{{ t.title }}</h3>

              <div class="event-card-date">
                <span class="date-val">{{ formatDate(t.booking_date) }}</span>
                <span class="date-rel" :class="getDaysClass(t.days_until)">
                  {{ formatDaysUntil(t.days_until) }}
                </span>
              </div>

              <div class="format-tags">
                <span class="tag">{{ getLocationFromFormat(t.event_format) }}</span>
                <span class="tag">{{ getBracketFromFormat(t.event_format) }}</span>
                <span class="tag">{{ getRosterFromFormat(t.event_format) }}</span>
              </div>

              <div class="event-card-bottom">
                <button @click="openModal(t)" class="btn-subtle">
                  Details
                </button>
                <a 
                  :href="t.bot_registration_url" 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  class="btn-row-register"
                  :class="{ disabled: t.is_past }"
                >
                  {{ t.is_past ? 'Ended' : 'Register in Bot ↗' }}
                </a>
              </div>
            </article>
          </div>
        </div>

        <!-- Right / Sidebar Column (Esports Charts Widget Bar) -->
        <aside class="sidebar-column">
          <!-- Live & Upcoming Featured Widget -->
          <div class="widget-box">
            <div class="widget-header">
              <span class="live-dot-pulse"></span>
              <h3 class="widget-title">Featured Events</h3>
            </div>

            <div v-if="featuredTournaments.length === 0" class="widget-empty">
              <span>No upcoming featured tournaments right now.</span>
            </div>

            <div v-else class="widget-list">
              <div 
                v-for="t in featuredTournaments" 
                :key="t.id"
                class="featured-item"
              >
                <div class="featured-top">
                  <GameLogo :discipline="t.discipline" :size="20" />
                  <span class="featured-disc">{{ t.discipline }}</span>
                  <span class="featured-date">{{ formatDate(t.booking_date) }}</span>
                </div>
                <div class="featured-title" @click="openModal(t)">{{ t.title }}</div>
                <div class="featured-footer">
                  <span class="format-mini">{{ t.format_label }}</span>
                  <a 
                    :href="t.bot_registration_url" 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    class="btn-mini-register"
                  >
                    Register ↗
                  </a>
                </div>
              </div>
            </div>
          </div>

          <!-- Official Disciplines Directory Widget -->
          <div class="widget-box">
            <div class="widget-header">
              <h3 class="widget-title">Official Disciplines</h3>
            </div>
            <div class="disciplines-list">
              <div 
                v-for="disc in availableDisciplines" 
                :key="disc.slug"
                class="disc-row"
                @click="selectDiscipline(disc.slug)"
              >
                <div class="disc-row-left">
                  <GameLogo :discipline="disc.slug" :size="20" />
                  <span class="disc-name">{{ disc.name }}</span>
                </div>
                <span class="disc-count">
                  {{ countByDiscipline(disc.slug) }} events
                </span>
              </div>
            </div>
          </div>

          <!-- University Verification Notice -->
          <div class="widget-box info-box">
            <h4 class="info-title">AITU Esports Portal</h4>
            <p class="info-desc">
              All tournaments are officially sanctioned for Astana IT University students. 
              Registration is verified directly via our Telegram Bot.
            </p>
            <a 
              :href="`https://t.me/${botUsername}`" 
              target="_blank" 
              rel="noopener noreferrer" 
              class="btn-outline-tg"
            >
              Open Bot Gateway ↗
            </a>
          </div>
        </aside>
      </div>

      <!-- Modal Dialog -->
      <transition name="fade">
        <div v-if="activeModalTournament" class="modal-overlay" @click.self="closeModal">
          <div class="modal">
            <div class="modal-top">
              <div class="modal-game-info">
                <GameLogo :discipline="activeModalTournament.discipline" :size="28" />
                <span class="modal-disc-label">{{ activeModalTournament.discipline }}</span>
              </div>
              <button @click="closeModal" class="btn-close">✕</button>
            </div>

            <div class="modal-content">
              <h2 class="modal-heading">{{ activeModalTournament.title }}</h2>

              <div class="meta-grid">
                <div class="meta-cell">
                  <span class="meta-k">Date</span>
                  <span class="meta-v">{{ formatDate(activeModalTournament.booking_date) }}</span>
                  <span class="meta-s" :class="getDaysClass(activeModalTournament.days_until)">
                    {{ formatDaysUntil(activeModalTournament.days_until) }}
                  </span>
                </div>
                <div class="meta-cell">
                  <span class="meta-k">Match Format</span>
                  <span class="meta-v">{{ activeModalTournament.format_label }}</span>
                </div>
                <div class="meta-cell">
                  <span class="meta-k">Organizer</span>
                  <span class="meta-v">{{ activeModalTournament.creator_name || 'AITU Esports' }}</span>
                </div>
                <div class="meta-cell">
                  <span class="meta-k">Status</span>
                  <span class="meta-v text-red">{{ formatStatus(activeModalTournament.status) }}</span>
                </div>
              </div>

              <!-- Rules Link -->
              <div class="modal-block">
                <h4 class="block-title">Tournament Rules</h4>
                <div v-if="activeModalTournament.rulebook_url" class="rules-box">
                  <a 
                    :href="activeModalTournament.rulebook_url" 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    class="rules-link"
                  >
                    View Official Regulations Document ↗
                  </a>
                </div>
                <div v-else class="rules-box">
                  <p class="rules-text">Rules and match lobbies are managed via the Telegram Bot.</p>
                </div>
              </div>

              <!-- Instructions -->
              <div class="modal-block">
                <h4 class="block-title">How to Enter</h4>
                <div class="steps-list">
                  <div class="step-item">
                    <span class="step-num">1</span>
                    <div class="step-desc">
                      <strong>Open Telegram Bot</strong>
                      <span>Launch the registration wizard in the official club bot.</span>
                    </div>
                  </div>
                  <div class="step-item">
                    <span class="step-num">2</span>
                    <div class="step-desc">
                      <strong>Verify Student ID</strong>
                      <span>Ensure your AITU student credentials are verified.</span>
                    </div>
                  </div>
                  <div class="step-item">
                    <span class="step-num">3</span>
                    <div class="step-desc">
                      <strong>Submit Roster</strong>
                      <span>Enter player nicknames or captain contacts.</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="modal-actions">
              <button @click="closeModal" class="btn-subtle">Close</button>
              <a 
                :href="activeModalTournament.bot_registration_url" 
                target="_blank" 
                rel="noopener noreferrer" 
                class="btn-modal-register"
                :class="{ disabled: activeModalTournament.is_past }"
              >
                {{ activeModalTournament.is_past ? 'Tournament Ended' : 'Register in Telegram Bot ↗' }}
              </a>
            </div>
          </div>
        </div>
      </transition>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import GameLogo from '../components/GameLogo.vue'

const router = useRouter()

const tournaments = ref([])
const total = ref(0)
const loading = ref(true)
const botUsername = ref('aitu_gaming_bot')
const stats = ref({
  total_tournaments: 0,
  upcoming_tournaments: 0,
  active_disciplines: 0,
  disciplines: []
})

const currentView = ref('table')
const searchQuery = ref('')
const selectedDiscipline = ref('ALL')
const selectedStatus = ref('UPCOMING')
const sortBy = ref('date_asc')

const activeModalTournament = ref(null)

const isAuthenticated = computed(() => !!localStorage.getItem('access_token'))

const availableDisciplines = [
  { slug: 'CS2', name: 'Counter-Strike 2' },
  { slug: 'DOTA2', name: 'Dota 2' },
  { slug: 'VALORANT', name: 'Valorant' },
  { slug: 'FIFA', name: 'EA Sports FC' },
  { slug: 'PUBG', name: 'PUBG Mobile' },
  { slug: 'MLBB', name: 'Mobile Legends' },
  { slug: 'OTHER', name: 'Other Games' },
]

const statusOptions = [
  { key: 'UPCOMING', label: 'Upcoming' },
  { key: 'ALL', label: 'All Events' },
  { key: 'PAST', label: 'Past Events' },
]

const fetchTournaments = async () => {
  loading.value = true
  try {
    const params = { limit: 100, offset: 0 }
    if (selectedDiscipline.value && selectedDiscipline.value !== 'ALL') {
      params.discipline = selectedDiscipline.value
    }
    if (selectedStatus.value && selectedStatus.value !== 'ALL') {
      params.status = selectedStatus.value
    }
    if (searchQuery.value.trim()) {
      params.query = searchQuery.value.trim()
    }

    const response = await axios.get('/api/tournaments', { params })
    tournaments.value = response.data.items || []
    total.value = response.data.total || 0
    if (response.data.bot_username) {
      botUsername.value = response.data.bot_username
    }
    if (response.data.stats) {
      stats.value = response.data.stats
    }
  } catch (error) {
    console.error('Failed to load tournaments:', error)
  } finally {
    loading.value = false
  }
}

const filteredTournaments = computed(() => {
  let list = tournaments.value
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase().trim()
    list = list.filter(t => 
      t.title.toLowerCase().includes(q) ||
      t.discipline.toLowerCase().includes(q) ||
      (t.format_label && t.format_label.toLowerCase().includes(q))
    )
  }
  return list
})

const sortedTournaments = computed(() => {
  const list = [...filteredTournaments.value]
  if (sortBy.value === 'date_asc') {
    return list.sort((a, b) => new Date(a.booking_date) - new Date(b.booking_date))
  } else {
    return list.sort((a, b) => new Date(b.booking_date) - new Date(a.booking_date))
  }
})

const featuredTournaments = computed(() => {
  return tournaments.value.filter(t => !t.is_past && t.status === 'APPROVED').slice(0, 4)
})

const countByDiscipline = (slug) => {
  return tournaments.value.filter(t => t.discipline.toUpperCase() === slug.toUpperCase()).length
}

const selectDiscipline = (disc) => {
  selectedDiscipline.value = disc
  fetchTournaments()
}

const selectStatus = (st) => {
  selectedStatus.value = st
  fetchTournaments()
}

let searchTimer = null
const onSearchInput = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    fetchTournaments()
  }, 300)
}

const resetFilters = () => {
  searchQuery.value = ''
  selectedDiscipline.value = 'ALL'
  selectedStatus.value = 'ALL'
  fetchTournaments()
}

const openModal = (t) => { activeModalTournament.value = t }
const closeModal = () => { activeModalTournament.value = null }

const logout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user')
  router.push('/login')
}

const formatDate = (dateStr) => {
  if (!dateStr) return 'TBA'
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return dateStr
  }
}

const formatDaysUntil = (days) => {
  if (days === undefined || days === null) return ''
  if (days < 0) return 'Ended'
  if (days === 0) return 'Today'
  if (days === 1) return 'Tomorrow'
  return `In ${days}d`
}

const getDaysClass = (days) => {
  if (days === undefined || days === null) return ''
  if (days < 0) return 'text-muted'
  if (days === 0 || days === 1) return 'text-red'
  return ''
}

const formatStatus = (status) => {
  const map = {
    APPROVED: 'Registration Open',
    PENDING: 'Under Review',
    REJECTED: 'Closed',
    CANCELLED: 'Cancelled',
  }
  return map[status] || status
}

const getLocationFromFormat = (fmt) => {
  if (!fmt) return 'Online'
  if (fmt.toLowerCase().includes('lan')) return 'LAN'
  return 'Online'
}

const getBracketFromFormat = (fmt) => {
  if (!fmt) return 'Single Elim'
  if (fmt.toLowerCase().includes('double_elim')) return 'Double Elim'
  if (fmt.toLowerCase().includes('round_robin')) return 'Round Robin'
  return 'Single Elim'
}

const getRosterFromFormat = (fmt) => {
  if (!fmt) return '5v5'
  if (fmt.toLowerCase().includes('1x1')) return '1v1'
  if (fmt.toLowerCase().includes('2x2')) return '2v2'
  if (fmt.toLowerCase().includes('5x5')) return '5v5'
  return 'Squad'
}

onMounted(() => {
  fetchTournaments()
})
</script>

<style scoped>
.tournaments-page {
  min-height: 100vh;
  background-color: var(--bg-color, #0a0d14);
  color: var(--text-primary, #f8fafc);
  padding-bottom: 5rem;
}

/* Header */
.header {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(10, 13, 20, 0.95);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--surface-border);
}

.header-inner {
  max-width: 1360px;
  margin: 0 auto;
  padding: 0.85rem 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 2.5rem;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
}

.brand-logo {
  height: 28px;
  width: auto;
  object-fit: contain;
  display: block;
}

.logo-pill {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-subtle);
  border: 1px solid var(--accent-border);
  padding: 0.1rem 0.5rem;
  border-radius: 9999px;
}

.nav {
  display: flex;
  gap: 0.5rem;
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
  gap: 0.85rem;
}

.btn-tg {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.82rem;
  font-weight: 600;
  color: #fff;
  background: var(--accent);
  padding: 0.4rem 0.85rem;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.btn-tg:hover {
  background: var(--accent-hover);
  box-shadow: 0 0 12px var(--accent-glow);
}

.auth-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
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
.text-red { color: var(--accent) !important; font-weight: 600; }

/* Page Container */
.page-container {
  max-width: 1360px;
  margin: 0 auto;
  padding: 1.75rem 1.5rem 4rem 1.5rem;
}

/* Page Head */
.page-head {
  margin-bottom: 1.5rem;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}

.breadcrumb .sep { opacity: 0.5; }
.breadcrumb .curr { color: var(--text-secondary); }

.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.main-title {
  font-size: 1.85rem;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.btn-red-action {
  background: var(--accent);
  color: #fff;
  font-size: 0.85rem;
  font-weight: 600;
  padding: 0.5rem 1.1rem;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.btn-red-action:hover {
  background: var(--accent-hover);
  box-shadow: 0 0 12px var(--accent-glow);
}

/* Filter Panel (Esports Charts Design) */
.filter-panel {
  background: var(--surface-bg);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  padding: 1.1rem 1.25rem;
  margin-bottom: 1.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.filter-top {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.filter-select-wrap {
  width: 220px;
}

.filter-select {
  width: 100%;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-sm);
  color: #fff;
  padding: 0.45rem 0.75rem;
  font-size: 0.82rem;
}

.filter-select:focus {
  border-color: var(--accent);
}

.filter-chips {
  display: flex;
  gap: 0.4rem;
}

.filter-btn {
  font-size: 0.8rem;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--surface-border);
  padding: 0.4rem 0.8rem;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.filter-btn:hover {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.2);
}

.filter-btn.active {
  background: var(--accent-subtle);
  border-color: var(--accent);
  color: #fff;
}

/* Popular Filters with Official Logos */
.popular-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding-top: 0.6rem;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
}

.popular-label {
  font-size: 0.78rem;
  color: var(--text-muted);
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.popular-chips {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.popular-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.8rem;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--surface-border);
  padding: 0.25rem 0.65rem;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.popular-chip:hover {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.2);
}

.popular-chip.active {
  background: var(--accent-subtle);
  border-color: var(--accent);
  color: #fff;
}

/* Search Bar Row */
.search-bar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding-top: 0.6rem;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
}

.search-box {
  position: relative;
  flex: 1;
  max-width: 400px;
}

.search-svg {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
}

.search-field {
  width: 100%;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-sm);
  color: #fff;
  padding: 0.45rem 2rem 0.45rem 2.2rem;
  font-size: 0.85rem;
}

.search-field:focus {
  border-color: var(--accent);
}

.clear-search {
  position: absolute;
  right: 0.65rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  font-size: 0.75rem;
}

.bar-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.sort-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.sort-lbl {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.sort-select {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-sm);
  color: #fff;
  padding: 0.35rem 0.65rem;
  font-size: 0.8rem;
}

.view-toggle {
  display: flex;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--surface-border);
  padding: 2px;
  border-radius: var(--radius-sm);
}

.toggle-btn {
  font-size: 0.8rem;
  color: var(--text-secondary);
  padding: 0.3rem 0.65rem;
  border-radius: 4px;
}

.toggle-btn.active {
  background: var(--accent);
  color: #fff;
}

/* 2-Column Layout */
.layout-grid {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 1.75rem;
  align-items: start;
}

/* Table Card (Esports Charts Main Table) */
.table-card {
  background: var(--surface-bg);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.esports-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.esports-table th {
  padding: 0.75rem 1.1rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  border-bottom: 1px solid var(--surface-border);
  background: rgba(0, 0, 0, 0.15);
}

.esports-table td {
  padding: 0.85rem 1.1rem;
  font-size: 0.88rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  vertical-align: middle;
}

.esports-table tbody tr {
  transition: all 0.15s;
  position: relative;
}

.esports-table tbody tr:hover {
  background: var(--surface-hover);
}

.esports-table tbody tr.row-past {
  opacity: 0.45;
}

.col-game { width: 44px; text-align: center; }

.event-title-wrap {
  display: flex;
  flex-direction: column;
}

.event-title {
  font-weight: 600;
  color: #fff;
  cursor: pointer;
  line-height: 1.3;
}

.event-title:hover {
  color: var(--accent);
}

.event-sub {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.format-badge {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.date-val {
  font-weight: 600;
  font-size: 0.85rem;
}

.date-rel {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.status-wrap {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.status-indicator-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
}

.status-indicator-dot.approved {
  background: var(--accent);
  box-shadow: 0 0 6px var(--accent);
}

.status-indicator-dot.pending {
  background: var(--warning);
}

.status-label {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.text-right { text-align: right; }

.action-cell-btns {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.btn-subtle {
  font-size: 0.8rem;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--surface-border);
  padding: 0.35rem 0.65rem;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.btn-subtle:hover {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.2);
}

.btn-row-register {
  font-size: 0.8rem;
  font-weight: 600;
  color: #fff;
  background: var(--accent);
  padding: 0.35rem 0.75rem;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.btn-row-register:hover {
  background: var(--accent-hover);
  box-shadow: 0 0 10px var(--accent-glow);
}

.btn-row-register.disabled {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-muted);
  pointer-events: none;
}

/* Cards Grid */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

.event-card {
  background: var(--surface-bg);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  padding: 1.1rem;
  display: flex;
  flex-direction: column;
}

.event-card.card-past { opacity: 0.5; }

.event-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.card-game-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.card-disc-name {
  display: block;
  font-size: 0.82rem;
  font-weight: 700;
}

.card-host {
  display: block;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.event-card-title {
  font-size: 1.05rem;
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 0.5rem;
  line-height: 1.35;
}

.event-card-title:hover {
  color: var(--accent);
}

.event-card-date {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.format-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-bottom: 1rem;
}

.tag {
  font-size: 0.75rem;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--surface-border);
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
}

.event-card-bottom {
  display: flex;
  gap: 0.5rem;
  margin-top: auto;
  padding-top: 0.75rem;
  border-top: 1px solid var(--surface-border);
}

.event-card-bottom .btn-row-register {
  flex: 1;
  text-align: center;
}

/* Sidebar Column Widgets */
.sidebar-column {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.widget-box {
  background: var(--surface-bg);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  padding: 1.1rem;
}

.widget-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  padding-bottom: 0.6rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.live-dot-pulse {
  width: 8px;
  height: 8px;
  background: var(--accent);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--accent);
  animation: pulse-red 2s infinite;
}

@keyframes pulse-red {
  0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
  70% { transform: scale(1.1); box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }
  100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

.widget-title {
  font-size: 0.95rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.widget-empty {
  font-size: 0.82rem;
  color: var(--text-muted);
  padding: 1rem 0;
  text-align: center;
}

.widget-list {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.featured-item {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-sm);
  padding: 0.75rem;
  transition: border-color 0.15s;
}

.featured-item:hover {
  border-color: var(--accent);
}

.featured-top {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.35rem;
}

.featured-disc {
  font-size: 0.75rem;
  font-weight: 700;
  color: #fff;
}

.featured-date {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-left: auto;
}

.featured-title {
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 0.5rem;
  line-height: 1.3;
}

.featured-title:hover {
  color: var(--accent);
}

.featured-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.format-mini {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.btn-mini-register {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--accent);
  border: 1px solid var(--accent-border);
  padding: 0.2rem 0.55rem;
  border-radius: 4px;
  transition: all 0.15s;
}

.btn-mini-register:hover {
  background: var(--accent);
  color: #fff;
}

/* Disciplines Directory */
.disciplines-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.disc-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.45rem 0.6rem;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s;
}

.disc-row:hover {
  background: rgba(255, 255, 255, 0.04);
}

.disc-row-left {
  display: flex;
  align-items: center;
  gap: 0.55rem;
}

.disc-name {
  font-size: 0.85rem;
  font-weight: 500;
}

.disc-count {
  font-size: 0.78rem;
  color: var(--text-muted);
}

/* Info Box */
.info-box {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.06) 0%, rgba(16, 20, 31, 1) 100%);
  border-color: var(--accent-border);
}

.info-title {
  font-size: 0.92rem;
  font-weight: 700;
  margin-bottom: 0.35rem;
  color: #fff;
}

.info-desc {
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.45;
  margin-bottom: 0.85rem;
}

.btn-outline-tg {
  display: inline-block;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--accent);
  border: 1px solid var(--accent-border);
  padding: 0.35rem 0.75rem;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.btn-outline-tg:hover {
  background: var(--accent);
  color: #fff;
}

/* States */
.state-container {
  padding: 3.5rem 1.5rem;
  text-align: center;
  background: var(--surface-bg);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
}

.state-container h4 {
  font-size: 1.15rem;
  color: #fff;
  margin-bottom: 0.4rem;
}

.state-container p {
  font-size: 0.88rem;
  margin-bottom: 1.25rem;
}

.red-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  margin: 0 auto 1rem auto;
}

@keyframes spin { to { transform: rotate(360deg); } }

.btn-reset {
  background: var(--accent);
  color: #fff;
  font-size: 0.85rem;
  font-weight: 600;
  padding: 0.45rem 1rem;
  border-radius: var(--radius-sm);
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 1rem;
}

.modal {
  width: 100%;
  max-width: 580px;
  background: #0d1017;
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.7);
}

.modal-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.1rem 1.5rem;
  border-bottom: 1px solid var(--surface-border);
  background: rgba(239, 68, 68, 0.05);
}

.modal-game-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.modal-disc-label {
  font-size: 0.88rem;
  font-weight: 700;
}

.btn-close {
  color: var(--text-muted);
  font-size: 0.95rem;
}

.btn-close:hover { color: #fff; }

.modal-content {
  padding: 1.5rem;
}

.modal-heading {
  font-size: 1.4rem;
  font-weight: 700;
  margin-bottom: 1.25rem;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-sm);
  padding: 0.85rem;
  margin-bottom: 1.25rem;
}

.meta-cell {
  display: flex;
  flex-direction: column;
}

.meta-k {
  font-size: 0.72rem;
  text-transform: uppercase;
  color: var(--text-muted);
}

.meta-v {
  font-size: 0.92rem;
  font-weight: 600;
}

.meta-s {
  font-size: 0.75rem;
}

.modal-block {
  margin-bottom: 1.25rem;
}

.block-title {
  font-size: 0.88rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}

.rules-link {
  font-size: 0.85rem;
  color: var(--accent);
  font-weight: 600;
}

.rules-link:hover { text-decoration: underline; }

.rules-text {
  font-size: 0.82rem;
  color: var(--text-secondary);
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.step-item {
  display: flex;
  gap: 0.65rem;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-sm);
  padding: 0.6rem 0.75rem;
}

.step-num {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--accent);
}

.step-desc strong {
  display: block;
  font-size: 0.82rem;
}

.step-desc span {
  display: block;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.modal-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.65rem;
  padding: 1.1rem 1.5rem;
  border-top: 1px solid var(--surface-border);
  background: rgba(0, 0, 0, 0.25);
}

.btn-modal-register {
  font-size: 0.88rem;
  font-weight: 600;
  color: #fff;
  background: var(--accent);
  padding: 0.55rem 1.2rem;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.btn-modal-register:hover {
  background: var(--accent-hover);
  box-shadow: 0 0 12px var(--accent-glow);
}

.btn-modal-register.disabled {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-muted);
  pointer-events: none;
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@media (max-width: 1024px) {
  .layout-grid { grid-template-columns: 1fr; }
  .sidebar-column { order: 2; }
}

@media (max-width: 768px) {
  .header-left { gap: 1rem; }
  .main-title { font-size: 1.5rem; }
  .filter-panel { padding: 1rem; }
  .search-bar-row { flex-direction: column; align-items: stretch; }
  .search-box { max-width: 100%; }
}
</style>
