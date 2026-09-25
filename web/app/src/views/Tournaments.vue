<template>
  <div class="tournaments-page">
    <!-- Top Navigation Header -->
    <header class="glass-header">
      <div class="header-left">
        <router-link to="/tournaments" class="logo">
          <span class="icon">🕹️</span>
          <h1>AITU Gaming Hub <span class="badge live-badge">Esports</span></h1>
        </router-link>
        <nav class="nav-tabs">
          <router-link to="/tournaments" class="tab-link active">🏆 Tournaments</router-link>
          <router-link v-if="isAuthenticated" to="/admin" class="tab-link">👥 Members</router-link>
          <router-link v-if="isAuthenticated" to="/admin/disciplines" class="tab-link">🎮 Disciplines</router-link>
        </nav>
      </div>

      <div class="header-right">
        <a 
          :href="`https://t.me/${botUsername}`" 
          target="_blank" 
          rel="noopener noreferrer" 
          class="btn-telegram"
        >
          <svg class="tg-icon" viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.75-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
          </svg>
          <span>Open Telegram Bot</span>
        </a>

        <div v-if="isAuthenticated" class="user-menu">
          <span class="user-tag">👑 Admin</span>
          <router-link to="/admin" class="btn-admin-link">Dashboard</router-link>
          <button @click="logout" class="btn-logout">Logout</button>
        </div>
        <div v-else>
          <router-link to="/login" class="btn-login">
            🔐 Admin Login
          </router-link>
        </div>
      </div>
    </header>

    <!-- Main Container -->
    <main class="page-body">
      <!-- Hero Banner Section -->
      <section class="hero-section">
        <div class="hero-content">
          <div class="hero-badge">
            <span class="pulse-dot"></span>
            <span>Official Astana IT University Gaming Championships</span>
          </div>
          <h2 class="hero-title">
            Compete. Conquer. <span class="gradient-text">Become Champions.</span>
          </h2>
          <p class="hero-subtitle">
            Welcome to the central tournament portal of AITU Esports. Explore upcoming university tournaments,
            check match formats, review official rulebooks, and register your team directly via our verified Telegram Bot.
          </p>

          <!-- Live Metrics Counter -->
          <div class="metrics-grid">
            <div class="metric-card glass-panel">
              <span class="metric-icon">🏆</span>
              <div class="metric-info">
                <span class="metric-val">{{ stats.total_tournaments }}</span>
                <span class="metric-lbl">Total Tournaments</span>
              </div>
            </div>
            <div class="metric-card glass-panel highlight-card">
              <span class="metric-icon">⚡</span>
              <div class="metric-info">
                <span class="metric-val">{{ stats.upcoming_tournaments }}</span>
                <span class="metric-lbl">Active & Upcoming</span>
              </div>
            </div>
            <div class="metric-card glass-panel">
              <span class="metric-icon">🎮</span>
              <div class="metric-info">
                <span class="metric-val">{{ stats.active_disciplines }}</span>
                <span class="metric-lbl">Disciplines</span>
              </div>
            </div>
            <div class="metric-card glass-panel">
              <span class="metric-icon">🎓</span>
              <div class="metric-info">
                <span class="metric-val">100%</span>
                <span class="metric-lbl">Verified Students</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Filter, Search & View Controls -->
      <section class="controls-section glass-panel">
        <div class="controls-top">
          <!-- Search Bar -->
          <div class="search-box">
            <span class="search-icon">🔍</span>
            <input 
              v-model="searchQuery" 
              @input="onSearchInput"
              type="text" 
              placeholder="Search tournament by name or format..." 
            />
            <button v-if="searchQuery" @click="searchQuery = ''; fetchTournaments()" class="clear-btn">✕</button>
          </div>

          <!-- Status Filter Tabs -->
          <div class="status-tabs">
            <button 
              v-for="st in statusOptions" 
              :key="st.key" 
              :class="['status-btn', { active: selectedStatus === st.key }]"
              @click="selectStatus(st.key)"
            >
              {{ st.label }}
            </button>
          </div>

          <!-- View Mode Switcher -->
          <div class="view-switchers">
            <button 
              :class="['view-btn', { active: currentView === 'grid' }]"
              @click="currentView = 'grid'"
              title="Grid Cards View"
            >
              <span class="view-icon">🗂️</span> Cards
            </button>
            <button 
              :class="['view-btn', { active: currentView === 'table' }]"
              @click="currentView = 'table'"
              title="Compact Table View"
            >
              <span class="view-icon">📋</span> Table
            </button>
            <button 
              :class="['view-btn', { active: currentView === 'timeline' }]"
              @click="currentView = 'timeline'"
              title="Timeline Schedule"
            >
              <span class="view-icon">📅</span> Timeline
            </button>
          </div>
        </div>

        <!-- Discipline Filter Chips -->
        <div class="discipline-chips-row">
          <span class="chips-label">Discipline:</span>
          <div class="chips-scroll">
            <button 
              :class="['chip-btn', { active: selectedDiscipline === 'ALL' }]"
              @click="selectDiscipline('ALL')"
            >
              🌐 All ({{ tournaments.length }})
            </button>
            <button 
              v-for="disc in availableDisciplines" 
              :key="disc.slug"
              :class="['chip-btn', { active: selectedDiscipline === disc.slug }, disc.slug.toLowerCase()]"
              @click="selectDiscipline(disc.slug)"
            >
              <span class="disc-icon">{{ disc.icon }}</span> {{ disc.name }}
            </button>
          </div>
        </div>
      </section>

      <!-- Loading State -->
      <div v-if="loading" class="loading-container glass-panel">
        <div class="spinner"></div>
        <p>Loading AITU tournaments schedule...</p>
      </div>

      <!-- Empty State -->
      <div v-else-if="filteredTournaments.length === 0" class="empty-container glass-panel">
        <div class="empty-icon">🎮</div>
        <h3>No tournaments found</h3>
        <p>There are no tournaments matching your selected filters right now.</p>
        <button @click="resetFilters" class="btn-primary reset-btn">Reset All Filters</button>
      </div>

      <!-- 1. GRID CARDS VIEW -->
      <section v-else-if="currentView === 'grid'" class="tournaments-grid">
        <div 
          v-for="t in filteredTournaments" 
          :key="t.id" 
          class="tournament-card glass-panel"
          :class="[t.discipline.toLowerCase(), { 'is-past': t.is_past }]"
        >
          <!-- Card Header & Badge -->
          <div class="card-header">
            <div class="discipline-badge" :class="t.discipline.toLowerCase()">
              <span class="discipline-icon">{{ getDisciplineIcon(t.discipline) }}</span>
              <span class="discipline-name">{{ t.discipline }}</span>
            </div>
            <div class="status-indicator" :class="t.status.toLowerCase()">
              <span class="dot"></span>
              <span>{{ formatStatus(t.status) }}</span>
            </div>
          </div>

          <!-- Tournament Title -->
          <div class="card-body">
            <h3 class="tournament-title" @click="openModal(t)">{{ t.title }}</h3>
            
            <!-- Date & Countdown -->
            <div class="date-row">
              <span class="calendar-icon">📅</span>
              <span class="date-text">{{ formatDate(t.booking_date) }}</span>
              <span class="days-badge" :class="getDaysClass(t.days_until)">
                {{ formatDaysUntil(t.days_until) }}
              </span>
            </div>

            <!-- Format Pills -->
            <div class="format-pills">
              <span class="pill location-pill">
                {{ getLocationFromFormat(t.event_format) }}
              </span>
              <span class="pill bracket-pill">
                {{ getBracketFromFormat(t.event_format) }}
              </span>
              <span class="pill roster-pill">
                {{ getRosterFromFormat(t.event_format) }}
              </span>
            </div>

            <!-- Rulebook Note -->
            <div class="rulebook-row">
              <span class="lbl">Rulebook:</span>
              <a 
                v-if="t.rulebook_url" 
                :href="t.rulebook_url" 
                target="_blank" 
                rel="noopener noreferrer" 
                class="rulebook-link"
              >
                📜 Official Rules ↗
              </a>
              <span v-else-if="t.rulebook_file_id" class="rulebook-bot">
                📄 In Telegram Bot
              </span>
              <span v-else class="rulebook-none">Standard Rules</span>
            </div>

            <div class="organizer-row">
              <span class="org-icon">👤</span>
              <span class="org-text">Host: {{ t.creator_name || 'AITU Esports' }}</span>
            </div>
          </div>

          <!-- Card Actions -->
          <div class="card-footer">
            <button @click="openModal(t)" class="btn-details">
              ℹ️ Details
            </button>
            <a 
              :href="t.bot_registration_url" 
              target="_blank" 
              rel="noopener noreferrer" 
              class="btn-register-bot"
              :class="{ disabled: t.is_past }"
            >
              <svg class="tg-inline-icon" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.75-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
              </svg>
              <span>{{ t.is_past ? 'Tournament Ended' : 'Register in Bot' }}</span>
            </a>
          </div>
        </div>
      </section>

      <!-- 2. TABLE VIEW -->
      <section v-else-if="currentView === 'table'" class="table-container glass-panel">
        <div class="table-wrapper">
          <table class="tournaments-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Discipline</th>
                <th>Tournament Name</th>
                <th>Format</th>
                <th>Status</th>
                <th>Rulebook</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="t in filteredTournaments" 
                :key="t.id"
                :class="{ 'row-past': t.is_past }"
              >
                <td class="date-cell">
                  <div class="cell-date-main">{{ formatDate(t.booking_date) }}</div>
                  <span class="days-pill" :class="getDaysClass(t.days_until)">
                    {{ formatDaysUntil(t.days_until) }}
                  </span>
                </td>
                <td>
                  <span class="table-disc-badge" :class="t.discipline.toLowerCase()">
                    {{ getDisciplineIcon(t.discipline) }} {{ t.discipline }}
                  </span>
                </td>
                <td class="name-cell">
                  <strong class="clickable-title" @click="openModal(t)">{{ t.title }}</strong>
                  <span class="host-sub">by {{ t.creator_name || 'AITU Esports' }}</span>
                </td>
                <td>
                  <div class="format-cell">
                    <span class="format-label">{{ t.format_label }}</span>
                  </div>
                </td>
                <td>
                  <span class="status-indicator" :class="t.status.toLowerCase()">
                    <span class="dot"></span>
                    <span>{{ formatStatus(t.status) }}</span>
                  </span>
                </td>
                <td>
                  <a 
                    v-if="t.rulebook_url" 
                    :href="t.rulebook_url" 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    class="rulebook-link"
                  >
                    📜 Rules ↗
                  </a>
                  <span v-else-if="t.rulebook_file_id" class="rulebook-bot">📄 Bot PDF</span>
                  <span v-else class="rulebook-none">—</span>
                </td>
                <td class="actions-cell">
                  <a 
                    :href="t.bot_registration_url" 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    class="btn-table-register"
                    :class="{ disabled: t.is_past }"
                  >
                    {{ t.is_past ? 'Ended' : '🤖 Register' }}
                  </a>
                  <button @click="openModal(t)" class="btn-icon-details" title="View details">
                    👁️
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- 3. TIMELINE SCHEDULE VIEW -->
      <section v-else-if="currentView === 'timeline'" class="timeline-container">
        <!-- Upcoming Section -->
        <div class="timeline-group">
          <div class="timeline-group-header">
            <span class="group-icon">⚡</span>
            <h3>Upcoming Tournaments ({{ upcomingTournaments.length }})</h3>
          </div>
          
          <div v-if="upcomingTournaments.length === 0" class="empty-timeline glass-panel">
            <p>No upcoming tournaments scheduled yet. Check back soon!</p>
          </div>

          <div v-else class="timeline-items">
            <div 
              v-for="t in upcomingTournaments" 
              :key="t.id"
              class="timeline-card glass-panel"
              :class="t.discipline.toLowerCase()"
            >
              <div class="timeline-date-marker">
                <span class="marker-day">{{ getDayNumber(t.booking_date) }}</span>
                <span class="marker-month">{{ getMonthAbbr(t.booking_date) }}</span>
              </div>
              <div class="timeline-card-content">
                <div class="timeline-header-row">
                  <span class="table-disc-badge" :class="t.discipline.toLowerCase()">
                    {{ getDisciplineIcon(t.discipline) }} {{ t.discipline }}
                  </span>
                  <span class="days-pill" :class="getDaysClass(t.days_until)">
                    {{ formatDaysUntil(t.days_until) }}
                  </span>
                </div>
                <h4 class="timeline-title" @click="openModal(t)">{{ t.title }}</h4>
                <p class="timeline-format">{{ t.format_label }}</p>
                <div class="timeline-footer">
                  <span class="org-text">Host: {{ t.creator_name || 'AITU Esports' }}</span>
                  <a 
                    :href="t.bot_registration_url" 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    class="btn-register-bot"
                  >
                    🤖 Register via Bot ↗
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Past Events Section -->
        <div v-if="pastTournaments.length > 0" class="timeline-group past-group">
          <div class="timeline-group-header">
            <span class="group-icon">📜</span>
            <h3>Past Tournaments Archive ({{ pastTournaments.length }})</h3>
          </div>

          <div class="timeline-items">
            <div 
              v-for="t in pastTournaments" 
              :key="t.id"
              class="timeline-card glass-panel is-past"
            >
              <div class="timeline-date-marker past-marker">
                <span class="marker-day">{{ getDayNumber(t.booking_date) }}</span>
                <span class="marker-month">{{ getMonthAbbr(t.booking_date) }}</span>
              </div>
              <div class="timeline-card-content">
                <div class="timeline-header-row">
                  <span class="table-disc-badge" :class="t.discipline.toLowerCase()">
                    {{ getDisciplineIcon(t.discipline) }} {{ t.discipline }}
                  </span>
                  <span class="status-indicator closed">
                    <span class="dot"></span>
                    <span>Concluded</span>
                  </span>
                </div>
                <h4 class="timeline-title" @click="openModal(t)">{{ t.title }}</h4>
                <p class="timeline-format">{{ t.format_label }}</p>
                <div class="timeline-footer">
                  <span class="org-text">Host: {{ t.creator_name || 'AITU Esports' }}</span>
                  <button @click="openModal(t)" class="btn-details">
                    ℹ️ View Archive Info
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Tournament Details & Registration Modal -->
      <transition name="modal-fade">
        <div v-if="activeModalTournament" class="modal-backdrop" @click.self="closeModal">
          <div class="modal-card glass-panel" :class="activeModalTournament.discipline.toLowerCase()">
            <div class="modal-header">
              <div class="modal-disc-badge" :class="activeModalTournament.discipline.toLowerCase()">
                <span>{{ getDisciplineIcon(activeModalTournament.discipline) }}</span>
                <span>{{ activeModalTournament.discipline }}</span>
              </div>
              <button @click="closeModal" class="btn-close-modal">✕</button>
            </div>

            <div class="modal-body">
              <h2 class="modal-title">{{ activeModalTournament.title }}</h2>

              <div class="modal-meta-grid">
                <div class="meta-item">
                  <span class="meta-icon">📅</span>
                  <div class="meta-info">
                    <span class="meta-lbl">Date & Schedule</span>
                    <span class="meta-val">{{ formatDate(activeModalTournament.booking_date) }}</span>
                    <span class="meta-sub">{{ formatDaysUntil(activeModalTournament.days_until) }}</span>
                  </div>
                </div>

                <div class="meta-item">
                  <span class="meta-icon">⚙️</span>
                  <div class="meta-info">
                    <span class="meta-lbl">Event Format</span>
                    <span class="meta-val">{{ activeModalTournament.format_label }}</span>
                  </div>
                </div>

                <div class="meta-item">
                  <span class="meta-icon">📌</span>
                  <div class="meta-info">
                    <span class="meta-lbl">Current Status</span>
                    <span class="meta-val status-colored" :class="activeModalTournament.status.toLowerCase()">
                      {{ formatStatus(activeModalTournament.status) }}
                    </span>
                  </div>
                </div>

                <div class="meta-item">
                  <span class="meta-icon">👤</span>
                  <div class="meta-info">
                    <span class="meta-lbl">Organizer</span>
                    <span class="meta-val">{{ activeModalTournament.creator_name || 'AITU Esports' }}</span>
                  </div>
                </div>
              </div>

              <!-- Rulebook Information -->
              <div class="modal-section rulebook-section">
                <h4>📜 Tournament Rules & Regulations</h4>
                <div v-if="activeModalTournament.rulebook_url" class="rulebook-download">
                  <p>Official tournament rulebook is hosted online:</p>
                  <a 
                    :href="activeModalTournament.rulebook_url" 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    class="btn-open-rules"
                  >
                    Open Rulebook Document ↗
                  </a>
                </div>
                <div v-else-if="activeModalTournament.rulebook_file_id" class="rulebook-download">
                  <p>Official PDF rulebook is available directly inside our Telegram Bot upon registration.</p>
                </div>
                <div v-else class="rulebook-download">
                  <p>Standard Astana IT University Esports Code of Conduct applies.</p>
                </div>
              </div>

              <!-- Registration Instructions -->
              <div class="modal-section registration-guide">
                <h4>🚀 How to Register for this Tournament</h4>
                <div class="guide-steps">
                  <div class="step-card">
                    <span class="step-num">1</span>
                    <div class="step-text">
                      <strong>Launch the Bot</strong>
                      <span>Click the registration button below to open AITU Gaming Hub in Telegram.</span>
                    </div>
                  </div>
                  <div class="step-card">
                    <span class="step-num">2</span>
                    <div class="step-text">
                      <strong>Student Verification</strong>
                      <span>Verify your AITU Barcode & Student ID (one-time setup).</span>
                    </div>
                  </div>
                  <div class="step-card">
                    <span class="step-num">3</span>
                    <div class="step-text">
                      <strong>Join Match Roster</strong>
                      <span>Enter your in-game nickname or submit your team's roster.</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="modal-footer">
              <button @click="closeModal" class="btn-cancel">Close</button>
              <a 
                :href="activeModalTournament.bot_registration_url" 
                target="_blank" 
                rel="noopener noreferrer" 
                class="btn-cta-bot"
                :class="{ disabled: activeModalTournament.is_past }"
              >
                <svg class="tg-btn-icon" viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.75-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
                </svg>
                <span>{{ activeModalTournament.is_past ? 'Tournament Concluded' : 'Register in Telegram Bot ↗' }}</span>
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

// Reactive State
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

// View mode: 'grid' | 'table' | 'timeline'
const currentView = ref('grid')

// Filters
const searchQuery = ref('')
const selectedDiscipline = ref('ALL')
const selectedStatus = ref('UPCOMING')

// Modal state
const activeModalTournament = ref(null)

// Check Auth
const isAuthenticated = computed(() => !!localStorage.getItem('access_token'))

// Discipline Metadata with Icons
const availableDisciplines = [
  { slug: 'CS2', name: 'Counter-Strike 2', icon: '🔫' },
  { slug: 'DOTA2', name: 'Dota 2', icon: '🛡️' },
  { slug: 'VALORANT', name: 'Valorant', icon: '🎯' },
  { slug: 'FIFA', name: 'EA Sports FC / FIFA', icon: '⚽' },
  { slug: 'PUBG', name: 'PUBG Mobile', icon: '🪂' },
  { slug: 'MLBB', name: 'Mobile Legends', icon: '⚔️' },
  { slug: 'OTHER', name: 'Other Games', icon: '🎲' },
]

const statusOptions = [
  { key: 'UPCOMING', label: '⚡ Upcoming (Active)' },
  { key: 'ALL', label: 'All Events' },
  { key: 'PAST', label: '📜 Past Archives' },
]

// Fetch Public Tournaments from Backend
const fetchTournaments = async () => {
  loading.value = true
  try {
    const params = {
      limit: 100,
      offset: 0,
    }
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

// Client-side search & filtering for instant feedback
const filteredTournaments = computed(() => {
  let list = tournaments.value

  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase().trim()
    list = list.filter(t => 
      t.title.toLowerCase().includes(q) ||
      t.discipline.toLowerCase().includes(q) ||
      (t.format_label && t.format_label.toLowerCase().includes(q)) ||
      (t.creator_name && t.creator_name.toLowerCase().includes(q))
    )
  }

  return list
})

const upcomingTournaments = computed(() => {
  return filteredTournaments.value.filter(t => !t.is_past)
})

const pastTournaments = computed(() => {
  return filteredTournaments.value.filter(t => t.is_past)
})

// Handlers
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
  }, 350)
}

const resetFilters = () => {
  searchQuery.value = ''
  selectedDiscipline.value = 'ALL'
  selectedStatus.value = 'ALL'
  fetchTournaments()
}

const openModal = (tournament) => {
  activeModalTournament.value = tournament
}

const closeModal = () => {
  activeModalTournament.value = null
}

const logout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user')
  router.push('/login')
}

// Helpers
const getDisciplineIcon = (disc) => {
  const d = availableDisciplines.find(item => item.slug.toUpperCase() === (disc || '').toUpperCase())
  return d ? d.icon : '🎮'
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
  const d = new Date(dateStr)
  return d.getDate()
}

const getMonthAbbr = (dateStr) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-GB', { month: 'short' }).toUpperCase()
}

const formatDaysUntil = (days) => {
  if (days === undefined || days === null) return ''
  if (days < 0) return 'Concluded'
  if (days === 0) return '🔥 Today!'
  if (days === 1) return '⏳ Tomorrow'
  return `In ${days} days`
}

const getDaysClass = (days) => {
  if (days === undefined || days === null) return ''
  if (days < 0) return 'past'
  if (days === 0) return 'today'
  if (days <= 3) return 'urgent'
  return 'future'
}

const formatStatus = (status) => {
  const map = {
    APPROVED: 'Registration Open',
    PENDING: 'Pending Review',
    REJECTED: 'Rejected',
    CANCELLED: 'Cancelled',
  }
  return map[status] || status
}

const getLocationFromFormat = (fmt) => {
  if (!fmt) return '🌐 Online'
  if (fmt.toLowerCase().includes('lan')) return '🏢 Campus LAN'
  return '🌐 Online'
}

const getBracketFromFormat = (fmt) => {
  if (!fmt) return '⚔️ Single Elim'
  if (fmt.toLowerCase().includes('double_elim')) return '🔄 Double Elim'
  if (fmt.toLowerCase().includes('round_robin')) return '🔁 Round Robin'
  return '⚔️ Single Elim'
}

const getRosterFromFormat = (fmt) => {
  if (!fmt) return '👥 5x5'
  if (fmt.toLowerCase().includes('1x1')) return '👤 1x1 Solo'
  if (fmt.toLowerCase().includes('2x2')) return '👥 2x2 Duo'
  if (fmt.toLowerCase().includes('5x5')) return '👥 5x5 Team'
  return '👥 Team'
}

onMounted(() => {
  fetchTournaments()
})
</script>

<style scoped>
.tournaments-page {
  min-height: 100vh;
  background-color: #0b0f19;
  background-image: 
    radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.08) 0%, transparent 40%),
    radial-gradient(circle at 90% 80%, rgba(236, 72, 153, 0.06) 0%, transparent 40%);
  color: var(--text-primary, #f8fafc);
  padding-bottom: 80px;
}

/* Header */
.glass-header {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2.5rem;
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
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
  text-decoration: none;
  color: inherit;
}

.logo .icon {
  font-size: 1.6rem;
}

.logo h1 {
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: -0.5px;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.badge {
  font-size: 0.75rem;
  padding: 0.2rem 0.6rem;
  border-radius: 9999px;
  text-transform: uppercase;
  font-weight: 700;
}

.live-badge {
  background: rgba(99, 102, 241, 0.2);
  color: #818cf8;
  border: 1px solid rgba(99, 102, 241, 0.4);
}

.nav-tabs {
  display: flex;
  gap: 0.5rem;
}

.tab-link {
  text-decoration: none;
  color: var(--text-secondary, #94a3b8);
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 500;
  transition: all 0.2s ease;
}

.tab-link:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.05);
}

.tab-link.active {
  color: #fff;
  background: rgba(99, 102, 241, 0.25);
  border: 1px solid rgba(99, 102, 241, 0.5);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.btn-telegram {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: linear-gradient(135deg, #0088cc 0%, #006699 100%);
  color: #fff;
  text-decoration: none;
  padding: 0.55rem 1.1rem;
  border-radius: 10px;
  font-size: 0.9rem;
  font-weight: 600;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgba(0, 136, 204, 0.3);
}

.btn-telegram:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(0, 136, 204, 0.45);
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.user-tag {
  font-size: 0.85rem;
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  padding: 0.3rem 0.6rem;
  border-radius: 6px;
  font-weight: 600;
}

.btn-admin-link {
  color: #818cf8;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
}

.btn-admin-link:hover {
  text-decoration: underline;
}

.btn-logout, .btn-login {
  padding: 0.45rem 0.9rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-logout {
  background: transparent;
  border: 1px solid rgba(239, 68, 68, 0.4);
  color: #ef4444;
}

.btn-logout:hover {
  background: rgba(239, 68, 68, 0.15);
}

.btn-login {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #fff;
}

.btn-login:hover {
  background: rgba(255, 255, 255, 0.15);
}

/* Page Body */
.page-body {
  max-width: 1380px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
}

/* Hero Section */
.hero-section {
  padding: 2.5rem 0 3rem 0;
  text-align: center;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 1rem;
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 9999px;
  font-size: 0.85rem;
  color: #a5b4fc;
  font-weight: 600;
  margin-bottom: 1.25rem;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  background-color: #10b981;
  border-radius: 50%;
  box-shadow: 0 0 10px #10b981;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
  70% { transform: scale(1.05); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.hero-title {
  font-size: 2.8rem;
  font-weight: 800;
  letter-spacing: -1px;
  line-height: 1.2;
  margin-bottom: 1rem;
}

.gradient-text {
  background: linear-gradient(135deg, #818cf8 0%, #c084fc 50%, #f472b6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-subtitle {
  max-width: 760px;
  margin: 0 auto 2.5rem auto;
  font-size: 1.1rem;
  line-height: 1.6;
  color: #94a3b8;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1.25rem;
  max-width: 1050px;
  margin: 0 auto;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 1.25rem 1.5rem;
  border-radius: 16px;
  text-align: left;
}

.metric-card.highlight-card {
  border-color: rgba(99, 102, 241, 0.4);
  background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(49, 46, 129, 0.25) 100%);
}

.metric-icon {
  font-size: 2rem;
}

.metric-val {
  display: block;
  font-size: 1.75rem;
  font-weight: 800;
  color: #f8fafc;
}

.metric-lbl {
  font-size: 0.85rem;
  color: #94a3b8;
  font-weight: 500;
}

/* Controls Section */
.controls-section {
  padding: 1.5rem;
  border-radius: 18px;
  margin-bottom: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.controls-top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.search-box {
  position: relative;
  flex: 1;
  min-width: 280px;
  max-width: 450px;
}

.search-icon {
  position: absolute;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 1rem;
  opacity: 0.6;
}

.search-box input {
  width: 100%;
  padding: 0.75rem 2.5rem 0.75rem 2.8rem;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  color: #fff;
  font-size: 0.95rem;
  outline: none;
  transition: all 0.2s ease;
}

.search-box input:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
}

.clear-btn {
  position: absolute;
  right: 0.85rem;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  font-size: 0.9rem;
}

.status-tabs {
  display: flex;
  background: rgba(15, 23, 42, 0.6);
  padding: 0.3rem;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.status-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.status-btn:hover {
  color: #fff;
}

.status-btn.active {
  background: rgba(99, 102, 241, 0.35);
  color: #fff;
}

.view-switchers {
  display: flex;
  gap: 0.35rem;
  background: rgba(15, 23, 42, 0.6);
  padding: 0.3rem;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.view-btn {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  background: transparent;
  border: none;
  color: #94a3b8;
  padding: 0.5rem 0.85rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.view-btn:hover {
  color: #fff;
}

.view-btn.active {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
}

/* Discipline Chips */
.discipline-chips-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding-top: 1rem;
}

.chips-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.chips-scroll {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.chip-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  padding: 0.4rem 0.85rem;
  border-radius: 9999px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.chip-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.chip-btn.active {
  background: #6366f1;
  color: #fff;
  border-color: #818cf8;
  box-shadow: 0 0 14px rgba(99, 102, 241, 0.4);
}

/* Loading & Empty States */
.loading-container, .empty-container {
  padding: 4rem 2rem;
  text-align: center;
  border-radius: 20px;
}

.spinner {
  width: 44px;
  height: 44px;
  border: 3px solid rgba(99, 102, 241, 0.2);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 1.5rem auto;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 3.5rem;
  margin-bottom: 1rem;
  opacity: 0.7;
}

.empty-container h3 {
  font-size: 1.4rem;
  margin-bottom: 0.5rem;
}

.empty-container p {
  color: #94a3b8;
  margin-bottom: 1.5rem;
}

.reset-btn {
  background: #6366f1;
  color: #fff;
  border: none;
  padding: 0.65rem 1.5rem;
  border-radius: 10px;
  font-weight: 600;
  cursor: pointer;
}

/* 1. GRID CARDS VIEW */
.tournaments-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 1.5rem;
}

.tournament-card {
  border-radius: 20px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: all 0.25s ease;
  position: relative;
}

.tournament-card:hover {
  transform: translateY(-4px);
  border-color: rgba(99, 102, 241, 0.4);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.35);
}

.tournament-card.is-past {
  opacity: 0.65;
  filter: grayscale(20%);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem 0.5rem 1.5rem;
}

.discipline-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.35rem 0.85rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.discipline-badge.cs2 { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
.discipline-badge.dota2 { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
.discipline-badge.valorant { background: rgba(244, 63, 94, 0.15); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.3); }
.discipline-badge.fifa { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
.discipline-badge.pubg { background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.3); }
.discipline-badge.mlbb { background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }
.discipline-badge.other { background: rgba(14, 165, 233, 0.15); color: #38bdf8; border: 1px solid rgba(14, 165, 233, 0.3); }

.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.8rem;
  font-weight: 600;
  padding: 0.25rem 0.6rem;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.05);
}

.status-indicator .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-indicator.approved { color: #10b981; }
.status-indicator.approved .dot { background-color: #10b981; box-shadow: 0 0 6px #10b981; }

.status-indicator.pending { color: #f59e0b; }
.status-indicator.pending .dot { background-color: #f59e0b; }

.status-indicator.closed { color: #94a3b8; }
.status-indicator.closed .dot { background-color: #64748b; }

.card-body {
  padding: 1rem 1.5rem;
  flex: 1;
}

.tournament-title {
  font-size: 1.3rem;
  font-weight: 700;
  line-height: 1.35;
  margin-bottom: 0.85rem;
  cursor: pointer;
  transition: color 0.2s ease;
}

.tournament-title:hover {
  color: #818cf8;
}

.date-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.calendar-icon {
  font-size: 1rem;
}

.date-text {
  font-size: 0.95rem;
  font-weight: 600;
  color: #e2e8f0;
}

.days-badge {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.2rem 0.55rem;
  border-radius: 6px;
  margin-left: auto;
}

.days-badge.today { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); }
.days-badge.urgent { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
.days-badge.future { background: rgba(99, 102, 241, 0.15); color: #818cf8; }
.days-badge.past { background: rgba(148, 163, 184, 0.15); color: #94a3b8; }

.format-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-bottom: 1.25rem;
}

.pill {
  font-size: 0.8rem;
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #cbd5e1;
}

.rulebook-row, .organizer-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: #94a3b8;
  margin-bottom: 0.4rem;
}

.rulebook-link {
  color: #38bdf8;
  text-decoration: none;
  font-weight: 600;
}

.rulebook-link:hover {
  text-decoration: underline;
}

.rulebook-bot {
  color: #a78bfa;
}

.card-footer {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.25rem 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(15, 23, 42, 0.3);
}

.btn-details {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  padding: 0.65rem 1rem;
  border-radius: 10px;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-details:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
}

.btn-register-bot {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%);
  color: #fff;
  text-decoration: none;
  padding: 0.65rem 1rem;
  border-radius: 10px;
  font-size: 0.9rem;
  font-weight: 600;
  transition: all 0.2s ease;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3);
}

.btn-register-bot:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45);
}

.btn-register-bot.disabled {
  background: rgba(255, 255, 255, 0.08);
  color: #64748b;
  cursor: not-allowed;
  box-shadow: none;
  pointer-events: none;
}

/* 2. TABLE VIEW */
.table-container {
  border-radius: 20px;
  overflow: hidden;
}

.table-wrapper {
  overflow-x: auto;
}

.tournaments-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.tournaments-table th {
  padding: 1.1rem 1.5rem;
  background: rgba(15, 23, 42, 0.7);
  font-size: 0.85rem;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.tournaments-table td {
  padding: 1.1rem 1.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  font-size: 0.92rem;
  vertical-align: middle;
}

.tournaments-table tbody tr:hover {
  background: rgba(255, 255, 255, 0.02);
}

.tournaments-table tbody tr.row-past {
  opacity: 0.6;
}

.cell-date-main {
  font-weight: 700;
  color: #fff;
  margin-bottom: 0.2rem;
}

.days-pill {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
}

.days-pill.today { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
.days-pill.urgent { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
.days-pill.future { background: rgba(99, 102, 241, 0.15); color: #818cf8; }
.days-pill.past { background: rgba(148, 163, 184, 0.15); color: #94a3b8; }

.table-disc-badge {
  display: inline-block;
  font-weight: 700;
  font-size: 0.85rem;
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
}

.clickable-title {
  display: block;
  font-size: 1.05rem;
  cursor: pointer;
  transition: color 0.2s;
}

.clickable-title:hover {
  color: #818cf8;
}

.host-sub {
  display: block;
  font-size: 0.8rem;
  color: #94a3b8;
}

.format-label {
  font-size: 0.85rem;
  color: #cbd5e1;
}

.actions-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-table-register {
  background: #4f46e5;
  color: #fff;
  text-decoration: none;
  padding: 0.45rem 0.9rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-table-register:hover {
  background: #6366f1;
}

.btn-table-register.disabled {
  background: rgba(255, 255, 255, 0.08);
  color: #64748b;
  pointer-events: none;
}

.btn-icon-details {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 0.45rem 0.6rem;
  border-radius: 8px;
  cursor: pointer;
}

/* 3. TIMELINE VIEW */
.timeline-container {
  display: flex;
  flex-direction: column;
  gap: 3rem;
}

.timeline-group-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.group-icon {
  font-size: 1.5rem;
}

.timeline-group-header h3 {
  font-size: 1.4rem;
  font-weight: 700;
}

.timeline-items {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.timeline-card {
  display: flex;
  align-items: center;
  gap: 2rem;
  padding: 1.5rem;
  border-radius: 18px;
  transition: transform 0.2s;
}

.timeline-card:hover {
  transform: translateX(6px);
}

.timeline-date-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 75px;
  height: 75px;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.35);
  border-radius: 14px;
}

.timeline-date-marker.past-marker {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
}

.marker-day {
  font-size: 1.6rem;
  font-weight: 800;
  line-height: 1;
}

.marker-month {
  font-size: 0.75rem;
  font-weight: 700;
  color: #818cf8;
}

.past-marker .marker-month {
  color: #94a3b8;
}

.timeline-card-content {
  flex: 1;
}

.timeline-header-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.timeline-title {
  font-size: 1.25rem;
  font-weight: 700;
  cursor: pointer;
  margin-bottom: 0.35rem;
}

.timeline-title:hover {
  color: #818cf8;
}

.timeline-format {
  font-size: 0.9rem;
  color: #94a3b8;
  margin-bottom: 0.75rem;
}

.timeline-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.empty-timeline {
  padding: 2.5rem;
  text-align: center;
  color: #94a3b8;
  border-radius: 16px;
}

/* Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1.5rem;
}

.modal-card {
  width: 100%;
  max-width: 680px;
  max-height: 90vh;
  overflow-y: auto;
  border-radius: 24px;
  background: #111827;
  border: 1px solid rgba(255, 255, 255, 0.15);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem 2rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.modal-disc-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.85rem;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.9rem;
}

.btn-close-modal {
  background: rgba(255, 255, 255, 0.08);
  border: none;
  color: #fff;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1rem;
}

.modal-body {
  padding: 2rem;
}

.modal-title {
  font-size: 1.8rem;
  font-weight: 800;
  line-height: 1.3;
  margin-bottom: 1.5rem;
}

.modal-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.25rem;
  margin-bottom: 2rem;
  background: rgba(255, 255, 255, 0.03);
  padding: 1.25rem;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.meta-item {
  display: flex;
  align-items: flex-start;
  gap: 0.85rem;
}

.meta-icon {
  font-size: 1.4rem;
}

.meta-lbl {
  display: block;
  font-size: 0.78rem;
  color: #94a3b8;
  text-transform: uppercase;
  font-weight: 600;
}

.meta-val {
  display: block;
  font-size: 1rem;
  font-weight: 700;
  color: #f8fafc;
}

.meta-sub {
  display: block;
  font-size: 0.8rem;
  color: #818cf8;
}

.status-colored.approved { color: #10b981; }
.status-colored.pending { color: #f59e0b; }

.modal-section {
  margin-bottom: 2rem;
}

.modal-section h4 {
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 0.85rem;
  color: #e2e8f0;
}

.rulebook-download {
  background: rgba(15, 23, 42, 0.6);
  padding: 1rem 1.25rem;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.rulebook-download p {
  font-size: 0.9rem;
  color: #94a3b8;
  margin-bottom: 0.75rem;
}

.btn-open-rules {
  display: inline-block;
  background: #38bdf8;
  color: #0f172a;
  text-decoration: none;
  font-weight: 700;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 0.88rem;
}

.guide-steps {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}

.step-card {
  background: rgba(15, 23, 42, 0.6);
  padding: 1rem;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  background: #6366f1;
  color: #fff;
  border-radius: 50%;
  font-weight: 700;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
}

.step-text strong {
  display: block;
  font-size: 0.9rem;
  margin-bottom: 0.25rem;
}

.step-text span {
  display: block;
  font-size: 0.8rem;
  color: #94a3b8;
  line-height: 1.4;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 1rem;
  padding: 1.5rem 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.btn-cancel {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  padding: 0.75rem 1.25rem;
  border-radius: 10px;
  font-weight: 600;
  cursor: pointer;
}

.btn-cta-bot {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  background: linear-gradient(135deg, #0088cc 0%, #006699 100%);
  color: #fff;
  text-decoration: none;
  padding: 0.75rem 1.5rem;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 700;
  box-shadow: 0 4px 16px rgba(0, 136, 204, 0.4);
}

.btn-cta-bot:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 22px rgba(0, 136, 204, 0.55);
}

.btn-cta-bot.disabled {
  background: #475569;
  cursor: not-allowed;
  pointer-events: none;
  box-shadow: none;
}

/* Animations */
.modal-fade-enter-active, .modal-fade-leave-active {
  transition: opacity 0.25s ease;
}

.modal-fade-enter-from, .modal-fade-leave-to {
  opacity: 0;
}

@media (max-width: 900px) {
  .hero-title { font-size: 2.1rem; }
  .guide-steps { grid-template-columns: 1fr; }
  .modal-meta-grid { grid-template-columns: 1fr; }
  .glass-header { padding: 1rem 1.25rem; }
  .header-left { gap: 1rem; }
}
</style>
