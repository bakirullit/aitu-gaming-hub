<template>
  <div class="tournaments-page">
    <!-- Minimalist Header -->
    <header class="header">
      <div class="header-inner">
        <div class="header-left">
          <router-link to="/tournaments" class="logo">
            <span class="logo-mark">AITU</span>
            <span class="logo-text">Gaming Hub</span>
            <span class="logo-pill">Tournaments</span>
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
            <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.75-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
            </svg>
            <span>Telegram Bot</span>
          </a>

          <div v-if="isAuthenticated" class="auth-box">
            <router-link to="/admin" class="btn-ghost">Admin Panel</router-link>
            <button @click="logout" class="btn-ghost text-danger">Logout</button>
          </div>
          <div v-else>
            <router-link to="/login" class="btn-ghost">Login</router-link>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="container">
      <!-- Minimal Hero -->
      <section class="hero">
        <h1 class="hero-title">Tournaments</h1>
        <p class="hero-desc">
          Astana IT University esports championships, official match schedules, and bot registration.
        </p>

        <!-- Compact Minimal Metrics -->
        <div class="metrics-row">
          <div class="metric">
            <span class="metric-num">{{ stats.total_tournaments }}</span>
            <span class="metric-label">Total Events</span>
          </div>
          <span class="metric-divider">/</span>
          <div class="metric">
            <span class="metric-num text-accent">{{ stats.upcoming_tournaments }}</span>
            <span class="metric-label">Active & Upcoming</span>
          </div>
          <span class="metric-divider">/</span>
          <div class="metric">
            <span class="metric-num">{{ stats.active_disciplines }}</span>
            <span class="metric-label">Disciplines</span>
          </div>
        </div>
      </section>

      <!-- Filter Controls Toolbar -->
      <section class="toolbar">
        <div class="toolbar-top">
          <!-- Search -->
          <div class="search-input-wrap">
            <svg class="search-svg" viewBox="0 0 20 20" width="16" height="16" fill="currentColor">
              <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd"/>
            </svg>
            <input 
              v-model="searchQuery" 
              @input="onSearchInput"
              type="text" 
              placeholder="Search tournaments..." 
              class="search-input"
            />
            <button v-if="searchQuery" @click="searchQuery = ''; fetchTournaments()" class="search-clear">✕</button>
          </div>

          <!-- Status Segmented Control -->
          <div class="segmented">
            <button 
              v-for="st in statusOptions" 
              :key="st.key" 
              :class="['segmented-item', { active: selectedStatus === st.key }]"
              @click="selectStatus(st.key)"
            >
              {{ st.label }}
            </button>
          </div>

          <!-- View Mode Switcher -->
          <div class="view-switch">
            <button 
              :class="['view-switch-btn', { active: currentView === 'grid' }]"
              @click="currentView = 'grid'"
              title="Cards"
            >
              Cards
            </button>
            <button 
              :class="['view-switch-btn', { active: currentView === 'table' }]"
              @click="currentView = 'table'"
              title="Table"
            >
              Table
            </button>
            <button 
              :class="['view-switch-btn', { active: currentView === 'timeline' }]"
              @click="currentView = 'timeline'"
              title="Timeline"
            >
              Timeline
            </button>
          </div>
        </div>

        <!-- Discipline Filter Chips -->
        <div class="disciplines-filter">
          <button 
            :class="['filter-pill', { active: selectedDiscipline === 'ALL' }]"
            @click="selectDiscipline('ALL')"
          >
            All
          </button>
          <button 
            v-for="disc in availableDisciplines" 
            :key="disc.slug"
            :class="['filter-pill', { active: selectedDiscipline === disc.slug }]"
            @click="selectDiscipline(disc.slug)"
          >
            {{ disc.name }}
          </button>
        </div>
      </section>

      <!-- Loading State -->
      <div v-if="loading" class="state-box">
        <div class="minimal-spinner"></div>
        <span class="state-text">Loading tournaments...</span>
      </div>

      <!-- Empty State -->
      <div v-else-if="filteredTournaments.length === 0" class="state-box">
        <p class="state-title">No tournaments found</p>
        <p class="state-desc">There are no tournaments matching your filters.</p>
        <button @click="resetFilters" class="btn-outline">Reset filters</button>
      </div>

      <!-- 1. GRID CARDS VIEW -->
      <section v-else-if="currentView === 'grid'" class="grid-view">
        <article 
          v-for="t in filteredTournaments" 
          :key="t.id" 
          class="card"
          :class="{ 'card-past': t.is_past }"
        >
          <!-- Top row -->
          <div class="card-meta">
            <span class="disc-tag">{{ t.discipline }}</span>
            <div class="status-dot-wrap">
              <span class="status-dot" :class="t.status.toLowerCase()"></span>
              <span class="status-name">{{ formatStatus(t.status) }}</span>
            </div>
          </div>

          <!-- Card Content -->
          <div class="card-main">
            <h3 class="card-title" @click="openModal(t)">{{ t.title }}</h3>
            
            <div class="card-date-row">
              <span class="card-date">{{ formatDate(t.booking_date) }}</span>
              <span class="card-relative" :class="getDaysClass(t.days_until)">
                {{ formatDaysUntil(t.days_until) }}
              </span>
            </div>

            <!-- Minimal Format Specs -->
            <div class="spec-pills">
              <span class="spec-pill">{{ getLocationFromFormat(t.event_format) }}</span>
              <span class="spec-pill">{{ getBracketFromFormat(t.event_format) }}</span>
              <span class="spec-pill">{{ getRosterFromFormat(t.event_format) }}</span>
            </div>

            <!-- Rulebook reference -->
            <div class="card-extra">
              <span class="extra-label">Rules:</span>
              <a 
                v-if="t.rulebook_url" 
                :href="t.rulebook_url" 
                target="_blank" 
                rel="noopener noreferrer" 
                class="rules-link"
              >
                Official Regulations ↗
              </a>
              <span v-else-if="t.rulebook_file_id" class="rules-muted">In Telegram Bot</span>
              <span v-else class="rules-muted">Standard</span>
            </div>
          </div>

          <!-- Card Actions -->
          <div class="card-bottom">
            <button @click="openModal(t)" class="btn-subtle">
              Details
            </button>
            <a 
              :href="t.bot_registration_url" 
              target="_blank" 
              rel="noopener noreferrer" 
              class="btn-primary-action"
              :class="{ disabled: t.is_past }"
            >
              {{ t.is_past ? 'Ended' : 'Register in Bot ↗' }}
            </a>
          </div>
        </article>
      </section>

      <!-- 2. TABLE VIEW -->
      <section v-else-if="currentView === 'table'" class="table-view">
        <div class="table-container">
          <table class="minimal-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Discipline</th>
                <th>Tournament</th>
                <th>Format</th>
                <th>Status</th>
                <th>Rules</th>
                <th class="text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="t in filteredTournaments" 
                :key="t.id"
                :class="{ 'row-past': t.is_past }"
              >
                <td class="date-col">
                  <div class="date-main">{{ formatDate(t.booking_date) }}</div>
                  <span class="date-sub" :class="getDaysClass(t.days_until)">
                    {{ formatDaysUntil(t.days_until) }}
                  </span>
                </td>
                <td>
                  <span class="table-disc">{{ t.discipline }}</span>
                </td>
                <td class="title-col">
                  <span class="table-title" @click="openModal(t)">{{ t.title }}</span>
                  <span class="table-host">{{ t.creator_name || 'AITU Esports' }}</span>
                </td>
                <td class="format-col">
                  <span class="format-text">{{ t.format_label }}</span>
                </td>
                <td>
                  <div class="status-dot-wrap">
                    <span class="status-dot" :class="t.status.toLowerCase()"></span>
                    <span class="status-name">{{ formatStatus(t.status) }}</span>
                  </div>
                </td>
                <td>
                  <a 
                    v-if="t.rulebook_url" 
                    :href="t.rulebook_url" 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    class="rules-link"
                  >
                    Link ↗
                  </a>
                  <span v-else-if="t.rulebook_file_id" class="rules-muted">Bot</span>
                  <span v-else class="rules-muted">—</span>
                </td>
                <td class="text-right">
                  <div class="table-action-wrap">
                    <button @click="openModal(t)" class="btn-icon" title="View details">
                      ℹ️
                    </button>
                    <a 
                      :href="t.bot_registration_url" 
                      target="_blank" 
                      rel="noopener noreferrer" 
                      class="btn-table"
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
      </section>

      <!-- 3. TIMELINE VIEW -->
      <section v-else-if="currentView === 'timeline'" class="timeline-view">
        <!-- Upcoming Section -->
        <div class="timeline-section">
          <div class="timeline-heading">
            <h3>Upcoming ({{ upcomingTournaments.length }})</h3>
          </div>

          <div v-if="upcomingTournaments.length === 0" class="state-box minimal-box">
            <span class="state-desc">No upcoming tournaments scheduled.</span>
          </div>

          <div v-else class="timeline-list">
            <div 
              v-for="t in upcomingTournaments" 
              :key="t.id"
              class="timeline-row"
            >
              <div class="timeline-date">
                <span class="t-day">{{ getDayNumber(t.booking_date) }}</span>
                <span class="t-month">{{ getMonthAbbr(t.booking_date) }}</span>
              </div>
              <div class="timeline-body">
                <div class="timeline-top">
                  <span class="disc-tag">{{ t.discipline }}</span>
                  <span class="card-relative" :class="getDaysClass(t.days_until)">
                    {{ formatDaysUntil(t.days_until) }}
                  </span>
                </div>
                <h4 class="timeline-item-title" @click="openModal(t)">{{ t.title }}</h4>
                <p class="timeline-item-format">{{ t.format_label }}</p>
                <div class="timeline-actions">
                  <span class="extra-label">Host: {{ t.creator_name || 'AITU Esports' }}</span>
                  <a 
                    :href="t.bot_registration_url" 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    class="btn-primary-action small"
                  >
                    Register in Bot ↗
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Past Section -->
        <div v-if="pastTournaments.length > 0" class="timeline-section past-section">
          <div class="timeline-heading">
            <h3>Concluded Events ({{ pastTournaments.length }})</h3>
          </div>

          <div class="timeline-list">
            <div 
              v-for="t in pastTournaments" 
              :key="t.id"
              class="timeline-row row-past"
            >
              <div class="timeline-date">
                <span class="t-day">{{ getDayNumber(t.booking_date) }}</span>
                <span class="t-month">{{ getMonthAbbr(t.booking_date) }}</span>
              </div>
              <div class="timeline-body">
                <div class="timeline-top">
                  <span class="disc-tag">{{ t.discipline }}</span>
                  <span class="status-name">Concluded</span>
                </div>
                <h4 class="timeline-item-title" @click="openModal(t)">{{ t.title }}</h4>
                <p class="timeline-item-format">{{ t.format_label }}</p>
                <div class="timeline-actions">
                  <button @click="openModal(t)" class="btn-subtle">
                    View Archive
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Minimal Modal -->
      <transition name="fade">
        <div v-if="activeModalTournament" class="modal-overlay" @click.self="closeModal">
          <div class="modal">
            <div class="modal-top">
              <div class="modal-disc">
                <span class="disc-tag">{{ activeModalTournament.discipline }}</span>
                <span class="status-name">{{ formatStatus(activeModalTournament.status) }}</span>
              </div>
              <button @click="closeModal" class="btn-close">✕</button>
            </div>

            <div class="modal-content">
              <h2 class="modal-heading">{{ activeModalTournament.title }}</h2>

              <div class="meta-grid">
                <div class="meta-cell">
                  <span class="meta-k">Date</span>
                  <span class="meta-v">{{ formatDate(activeModalTournament.booking_date) }}</span>
                  <span class="meta-s">{{ formatDaysUntil(activeModalTournament.days_until) }}</span>
                </div>
                <div class="meta-cell">
                  <span class="meta-k">Format</span>
                  <span class="meta-v">{{ activeModalTournament.format_label }}</span>
                </div>
                <div class="meta-cell">
                  <span class="meta-k">Host</span>
                  <span class="meta-v">{{ activeModalTournament.creator_name || 'AITU Esports' }}</span>
                </div>
                <div class="meta-cell">
                  <span class="meta-k">Platform</span>
                  <span class="meta-v">Telegram Bot</span>
                </div>
              </div>

              <!-- Rules -->
              <div class="modal-block">
                <h4 class="block-title">Rules & Regulations</h4>
                <div v-if="activeModalTournament.rulebook_url" class="rules-box">
                  <p>Official document available online:</p>
                  <a 
                    :href="activeModalTournament.rulebook_url" 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    class="btn-outline small"
                  >
                    Open Rulebook ↗
                  </a>
                </div>
                <div v-else class="rules-box">
                  <p>Official rules are distributed via the Telegram Bot upon registration.</p>
                </div>
              </div>

              <!-- Registration Steps -->
              <div class="modal-block">
                <h4 class="block-title">Registration Instructions</h4>
                <div class="steps-list">
                  <div class="step-item">
                    <span class="step-index">1</span>
                    <div class="step-desc">
                      <strong>Launch the Bot</strong>
                      <span>Open AITU Gaming Hub in Telegram with the direct registration link.</span>
                    </div>
                  </div>
                  <div class="step-item">
                    <span class="step-index">2</span>
                    <div class="step-desc">
                      <strong>Verify Student Status</strong>
                      <span>Confirm your AITU Student ID or Barcode (one-time verification).</span>
                    </div>
                  </div>
                  <div class="step-item">
                    <span class="step-index">3</span>
                    <div class="step-desc">
                      <strong>Submit Roster</strong>
                      <span>Enter player gamertag or full squad roster into the wizard.</span>
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
                class="btn-primary-action"
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

const currentView = ref('grid')
const searchQuery = ref('')
const selectedDiscipline = ref('ALL')
const selectedStatus = ref('UPCOMING')

const activeModalTournament = ref(null)

const isAuthenticated = computed(() => !!localStorage.getItem('access_token'))

const availableDisciplines = [
  { slug: 'CS2', name: 'CS2' },
  { slug: 'DOTA2', name: 'Dota 2' },
  { slug: 'VALORANT', name: 'Valorant' },
  { slug: 'FIFA', name: 'FIFA / FC' },
  { slug: 'PUBG', name: 'PUBG Mobile' },
  { slug: 'MLBB', name: 'MLBB' },
  { slug: 'OTHER', name: 'Other' },
]

const statusOptions = [
  { key: 'UPCOMING', label: 'Upcoming' },
  { key: 'ALL', label: 'All' },
  { key: 'PAST', label: 'Past' },
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

const upcomingTournaments = computed(() => filteredTournaments.value.filter(t => !t.is_past))
const pastTournaments = computed(() => filteredTournaments.value.filter(t => t.is_past))

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

const getDayNumber = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).getDate()
}

const getMonthAbbr = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('en-GB', { month: 'short' }).toUpperCase()
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
  if (days === 0 || days === 1) return 'text-accent'
  return ''
}

const formatStatus = (status) => {
  const map = {
    APPROVED: 'Open',
    PENDING: 'Review',
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
  gap: 0.75rem;
}

.btn-tg {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.82rem;
  font-weight: 500;
  color: #cbd5e1;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--surface-border);
  padding: 0.35rem 0.75rem;
  border-radius: var(--radius-sm);
  transition: all 0.15s ease;
}

.btn-tg:hover {
  background: rgba(255, 255, 255, 0.09);
  color: #fff;
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

/* Container */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2.5rem 1.5rem;
}

/* Minimal Hero */
.hero {
  margin-bottom: 2.5rem;
}

.hero-title {
  font-size: 2rem;
  font-weight: 700;
  letter-spacing: -0.5px;
  margin-bottom: 0.4rem;
}

.hero-desc {
  font-size: 0.95rem;
  color: var(--text-secondary, #94a3b8);
  margin-bottom: 1.25rem;
  max-width: 600px;
}

.metrics-row {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.metric {
  display: flex;
  align-items: baseline;
  gap: 0.4rem;
}

.metric-num {
  font-size: 1.1rem;
  font-weight: 700;
}

.metric-label {
  font-size: 0.82rem;
  color: var(--text-muted);
}

.metric-divider {
  color: var(--surface-border);
  font-size: 0.9rem;
}

.text-accent {
  color: var(--accent, #3b82f6);
}

/* Toolbar */
.toolbar {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 2rem;
}

.toolbar-top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}

.search-input-wrap {
  position: relative;
  flex: 1;
  min-width: 240px;
  max-width: 360px;
}

.search-svg {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
}

.search-input {
  width: 100%;
  background: var(--surface-bg);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-sm);
  color: #fff;
  padding: 0.5rem 2rem 0.5rem 2.2rem;
  font-size: 0.88rem;
  transition: border-color 0.15s;
}

.search-input:focus {
  border-color: rgba(255, 255, 255, 0.25);
}

.search-clear {
  position: absolute;
  right: 0.65rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  font-size: 0.8rem;
}

.segmented {
  display: flex;
  background: var(--surface-bg);
  border: 1px solid var(--surface-border);
  padding: 2px;
  border-radius: var(--radius-sm);
}

.segmented-item {
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--text-secondary);
  padding: 0.35rem 0.75rem;
  border-radius: 4px;
  transition: all 0.15s;
}

.segmented-item.active {
  background: rgba(255, 255, 255, 0.09);
  color: #fff;
}

.view-switch {
  display: flex;
  background: var(--surface-bg);
  border: 1px solid var(--surface-border);
  padding: 2px;
  border-radius: var(--radius-sm);
  margin-left: auto;
}

.view-switch-btn {
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--text-secondary);
  padding: 0.35rem 0.65rem;
  border-radius: 4px;
}

.view-switch-btn.active {
  background: rgba(255, 255, 255, 0.09);
  color: #fff;
}

.disciplines-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.filter-pill {
  font-size: 0.82rem;
  color: var(--text-secondary);
  background: var(--surface-bg);
  border: 1px solid var(--surface-border);
  padding: 0.3rem 0.7rem;
  border-radius: 9999px;
  transition: all 0.15s;
}

.filter-pill:hover {
  border-color: rgba(255, 255, 255, 0.18);
  color: #fff;
}

.filter-pill.active {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.25);
  color: #fff;
}

/* State Box */
.state-box {
  padding: 4rem 1.5rem;
  text-align: center;
  background: var(--surface-bg);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-lg);
}

.minimal-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  margin: 0 auto 1rem auto;
}

@keyframes spin { to { transform: rotate(360deg); } }

.state-title {
  font-size: 1.05rem;
  font-weight: 600;
  margin-bottom: 0.35rem;
}

.state-desc {
  font-size: 0.88rem;
  color: var(--text-secondary);
  margin-bottom: 1.25rem;
}

.btn-outline {
  display: inline-block;
  font-size: 0.85rem;
  font-weight: 500;
  color: #fff;
  border: 1px solid var(--surface-border);
  padding: 0.45rem 1rem;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.btn-outline:hover {
  background: rgba(255, 255, 255, 0.05);
}

.btn-outline.small {
  padding: 0.35rem 0.75rem;
  font-size: 0.8rem;
}

/* 1. GRID VIEW */
.grid-view {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 1rem;
}

.card {
  background: var(--surface-bg);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  transition: border-color 0.15s;
}

.card:hover {
  border-color: var(--surface-border-hover);
}

.card.card-past {
  opacity: 0.55;
}

.card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.disc-tag {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.5px;
  color: #cbd5e1;
  background: rgba(255, 255, 255, 0.06);
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.status-dot-wrap {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-dot.approved { background: var(--success, #10b981); }
.status-dot.pending { background: var(--warning, #f59e0b); }
.status-dot.closed, .status-dot.rejected { background: var(--text-muted); }

.status-name {
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.card-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.card-title {
  font-size: 1.15rem;
  font-weight: 600;
  line-height: 1.35;
  margin-bottom: 0.5rem;
  cursor: pointer;
}

.card-title:hover {
  color: #fff;
  text-decoration: underline;
}

.card-date-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.85rem;
}

.card-date {
  font-size: 0.85rem;
  color: #e2e8f0;
}

.card-relative {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.spec-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-bottom: 1rem;
}

.spec-pill {
  font-size: 0.75rem;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
}

.card-extra {
  font-size: 0.8rem;
  margin-top: auto;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.extra-label {
  color: var(--text-muted);
}

.rules-link {
  color: var(--accent);
}

.rules-link:hover {
  text-decoration: underline;
}

.rules-muted {
  color: var(--text-muted);
}

.card-bottom {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding-top: 0.85rem;
  border-top: 1px solid var(--surface-border);
}

.btn-subtle {
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--surface-border);
  padding: 0.45rem 0.85rem;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.btn-subtle:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
}

.btn-primary-action {
  flex: 1;
  text-align: center;
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

.btn-primary-action.small {
  flex: initial;
  padding: 0.35rem 0.75rem;
  font-size: 0.8rem;
}

.btn-primary-action.disabled {
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-muted);
  border-color: transparent;
  pointer-events: none;
}

/* 2. TABLE VIEW */
.table-view {
  background: var(--surface-bg);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.table-container {
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

.minimal-table tbody tr.row-past {
  opacity: 0.5;
}

.date-main {
  font-weight: 500;
}

.date-sub {
  font-size: 0.75rem;
}

.table-disc {
  font-size: 0.78rem;
  font-weight: 600;
  color: #cbd5e1;
}

.table-title {
  display: block;
  font-weight: 500;
  cursor: pointer;
}

.table-title:hover {
  color: #fff;
  text-decoration: underline;
}

.table-host {
  display: block;
  font-size: 0.78rem;
  color: var(--text-muted);
}

.format-text {
  font-size: 0.82rem;
  color: var(--text-secondary);
}

.text-right { text-align: right; }

.table-action-wrap {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.btn-icon {
  padding: 0.35rem 0.55rem;
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
}

.btn-table {
  font-size: 0.8rem;
  font-weight: 500;
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  padding: 0.35rem 0.65rem;
  border-radius: var(--radius-sm);
}

.btn-table.disabled {
  opacity: 0.4;
  pointer-events: none;
}

/* 3. TIMELINE VIEW */
.timeline-view {
  display: flex;
  flex-direction: column;
  gap: 2.5rem;
}

.timeline-heading {
  margin-bottom: 1rem;
}

.timeline-heading h3 {
  font-size: 1.15rem;
  font-weight: 600;
}

.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.timeline-row {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  background: var(--surface-bg);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  padding: 1rem 1.25rem;
}

.timeline-row.row-past {
  opacity: 0.5;
}

.timeline-date {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 50px;
  border-right: 1px solid var(--surface-border);
  padding-right: 1.25rem;
}

.t-day {
  font-size: 1.25rem;
  font-weight: 700;
}

.t-month {
  font-size: 0.72rem;
  color: var(--text-muted);
}

.timeline-body {
  flex: 1;
}

.timeline-top {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
}

.timeline-item-title {
  font-size: 1.05rem;
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 0.2rem;
}

.timeline-item-title:hover {
  text-decoration: underline;
}

.timeline-item-format {
  font-size: 0.82rem;
  color: var(--text-secondary);
  margin-bottom: 0.65rem;
}

.timeline-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.minimal-box {
  padding: 2rem;
}

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
  max-width: 580px;
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

.modal-disc {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-close {
  color: var(--text-muted);
  font-size: 0.95rem;
  padding: 0.25rem;
}

.btn-close:hover {
  color: #fff;
}

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
  gap: 0.85rem;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-sm);
  padding: 1rem;
  margin-bottom: 1.5rem;
}

.meta-k {
  display: block;
  font-size: 0.72rem;
  text-transform: uppercase;
  color: var(--text-muted);
}

.meta-v {
  display: block;
  font-size: 0.92rem;
  font-weight: 600;
}

.meta-s {
  display: block;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.modal-block {
  margin-bottom: 1.5rem;
}

.block-title {
  font-size: 0.92rem;
  font-weight: 600;
  margin-bottom: 0.65rem;
}

.rules-box {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.step-item {
  display: flex;
  gap: 0.75rem;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-sm);
  padding: 0.65rem 0.85rem;
}

.step-index {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--text-muted);
}

.step-desc strong {
  display: block;
  font-size: 0.85rem;
}

.step-desc span {
  display: block;
  font-size: 0.78rem;
  color: var(--text-muted);
}

.modal-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.65rem;
  padding: 1.25rem 1.5rem;
  border-top: 1px solid var(--surface-border);
  background: rgba(0, 0, 0, 0.2);
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

@media (max-width: 768px) {
  .hero-title { font-size: 1.6rem; }
  .header-left { gap: 1rem; }
  .meta-grid { grid-template-columns: 1fr; }
}
</style>
