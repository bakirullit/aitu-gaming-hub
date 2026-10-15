<template>
  <div class="tournament-hub-page">
    <!-- Top Navigation Header -->
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
            id="btn-header-telegram"
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

    <!-- Main Tournament Hub Container -->
    <main class="hub-container">
      <!-- Breadcrumb & Back Navigation -->
      <nav class="hub-breadcrumb" aria-label="Breadcrumb">
        <router-link to="/tournaments" class="back-link">
          <svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor">
            <path fill-rule="evenodd" d="M9.707 14.707a1 1 0 01-1.414 0l-5-5a1 1 0 010-1.414l5-5a1 1 0 011.414 1.414L6.414 8H17a1 1 0 110 2H6.414l3.293 3.293a1 1 0 010 1.414z" clip-rule="evenodd" />
          </svg>
          <span>Все турниры</span>
        </router-link>
        <span class="sep">/</span>
        <span class="curr-crumb">Open Sunday Tournament CS2 2v2</span>
      </nav>

      <!-- 1. Header & Status Banner -->
      <section class="hero-card" id="tournament-hero">
        <div class="hero-bg-glow"></div>
        <div class="hero-content">
          <!-- Game / Discipline Label -->
          <div class="hero-top-meta">
            <div class="game-badge">
              <GameLogo discipline="CS2" :size="24" />
              <span class="game-name">Counter-Strike 2</span>
              <span class="mode-pill">2v2 Напарники (Wingman)</span>
            </div>
            <div class="event-id-tag">
              <span>Event #CS2-SUN-2V2</span>
            </div>
          </div>

          <!-- Title -->
          <h1 class="hero-title" id="tournament-main-title">Open Sunday Tournament CS2 2v2</h1>

          <!-- Subtitle -->
          <p class="hero-subtitle">Fastcup (Astana) • AITU Gaming Club</p>

          <!-- Stage Indicator Badges -->
          <div class="stage-indicators-wrap" id="stage-indicators">
            <div class="stage-badge live-stage">
              <span class="status-pulse-dot"></span>
              <span class="badge-text">Сегодня: Онлайн-квалификация (до топ-8)</span>
            </div>
            <div class="stage-badge upcoming-stage">
              <span class="lan-icon">🏢</span>
              <span class="badge-text">Завтра: Оффлайн-финал (Top 8 LAN @ C.1.3.267P)</span>
            </div>
          </div>

          <!-- Quick Stats Grid -->
          <div class="hero-stats-grid">
            <div class="stat-pill">
              <span class="stat-label">Команды</span>
              <span class="stat-value">74 команды</span>
            </div>
            <div class="stat-pill">
              <span class="stat-label">Формат этапов</span>
              <span class="stat-value">Two-Day Hybrid Stage</span>
            </div>
            <div class="stat-pill">
              <span class="stat-label">Платформа</span>
              <span class="stat-value">Fastcup (Астана)</span>
            </div>
            <div class="stat-pill">
              <span class="stat-label">LAN Локация</span>
              <span class="stat-value">C.1.3.267P Esport Club</span>
            </div>
          </div>

          <!-- Quick Action Buttons -->
          <div class="hero-cta-bar">
            <a href="#bracket-section" class="btn-primary-action" id="btn-jump-bracket">
              <svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor">
                <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
              </svg>
              <span>Смотреть турнирную сетку</span>
            </a>
            <a href="#schedule-section" class="btn-secondary-action" id="btn-jump-schedule">
              <svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd" />
              </svg>
              <span>Расписание этапов</span>
            </a>
            <a href="#regulations-section" class="btn-secondary-action" id="btn-jump-regulations">
              <svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor">
                <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clip-rule="evenodd" />
              </svg>
              <span>Регламент турнира</span>
            </a>
            <a 
              :href="`https://t.me/${botUsername}`" 
              target="_blank" 
              rel="noopener noreferrer" 
              class="btn-telegram-action"
              id="btn-telegram-bot"
            >
              <span>Telegram Bot Support ↗</span>
            </a>
          </div>
        </div>
      </section>

      <!-- 2. Schedule / Timeline Module (Расписание этапов) -->
      <section class="section-card" id="schedule-section">
        <div class="section-header">
          <div class="section-header-left">
            <span class="section-sub">Двухдневный гибридный формат</span>
            <h2 class="section-title">Расписание этапов</h2>
          </div>
          <div class="section-badge">
            <span>Two-Day Hybrid Stage</span>
          </div>
        </div>

        <div class="timeline-grid">
          <!-- Этап 1: Online Stage (Сегодня) -->
          <div class="stage-card stage-active" id="stage-1-card">
            <div class="stage-card-header">
              <div class="stage-num-badge">1</div>
              <div class="stage-title-wrap">
                <div class="stage-day-tag active-tag">
                  <span class="pulse-ring"></span>
                  <span>Сегодня (Суббота) • Day 1</span>
                </div>
                <h3 class="stage-name">Этап 1: Online Stage</h3>
              </div>
            </div>

            <div class="stage-meta-list">
              <div class="stage-meta-item">
                <span class="meta-label">Формат:</span>
                <span class="meta-value highlight">Single Elimination BO1</span>
              </div>
              <div class="stage-meta-item">
                <span class="meta-label">Цель этапа:</span>
                <span class="meta-value highlight-accent">Выход в топ-8</span>
              </div>
              <div class="stage-meta-item">
                <span class="meta-label">Сетка:</span>
                <span class="meta-value">Останавливается после завершения стадии 1/16 (раунды 1/64, 1/32, 1/16)</span>
              </div>
              <div class="stage-meta-item">
                <span class="meta-label">Локация:</span>
                <span class="meta-value">Онлайн / Дискорд AITU Gaming / Fastcup</span>
              </div>
              <div class="stage-meta-item">
                <span class="meta-label">Участники:</span>
                <span class="meta-value">74 команды (удаленное подключение с личных ПК)</span>
              </div>
            </div>

            <div class="stage-footer active-footer">
              <span class="stage-status-text">⚡ Текущий этап: Онлайн-игры в процессе</span>
            </div>
          </div>

          <!-- Этап 2: Offline Playoffs (Завтра) -->
          <div class="stage-card stage-upcoming" id="stage-2-card">
            <div class="stage-card-header">
              <div class="stage-num-badge offline-badge">2</div>
              <div class="stage-title-wrap">
                <div class="stage-day-tag upcoming-tag">
                  <span>Завтра (Воскресенье) • Day 2</span>
                </div>
                <h3 class="stage-name">Этап 2: Offline Playoffs</h3>
              </div>
            </div>

            <div class="stage-meta-list">
              <div class="stage-meta-item">
                <span class="meta-label">Участники:</span>
                <span class="meta-value highlight-accent">8 команд-победителей онлайн-этапа (Top 8)</span>
              </div>
              <div class="stage-meta-item">
                <span class="meta-label">Локация:</span>
                <span class="meta-value highlight">Esport Club (кабинет C.1.3.267P)</span>
              </div>
              <div class="stage-meta-item">
                <span class="meta-label">Формат матчей:</span>
                <span class="meta-value">1/4 финала и 1/2 финала — BO1; Grand Final — BO3</span>
              </div>
              <div class="stage-meta-item">
                <span class="meta-label">Оборудование:</span>
                <span class="meta-value">ПК клуба с предоставленных организаторами аккаунтов</span>
              </div>
              <div class="stage-meta-item">
                <span class="meta-label">Раунды:</span>
                <span class="meta-value">1/4 финала › Полуфинал › Гранд-финал за титул чемпиона</span>
              </div>
            </div>

            <div class="stage-footer upcoming-footer">
              <span class="stage-status-text">🏢 Оффлайн LAN финал в клубе AITU Esports</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 3. Bracket Section -->
      <section class="section-card" id="bracket-section">
        <div class="section-header">
          <div class="section-header-left">
            <span class="section-sub">Интерактивная турнирная сетка</span>
            <h2 class="section-title">Challonge Сетка Турнира</h2>
          </div>
          <div class="bracket-actions">
            <button @click="refreshIframe" class="btn-bracket-reload" title="Обновить сетку">
              <svg viewBox="0 0 20 20" width="14" height="14" fill="currentColor">
                <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
              </svg>
              <span>Обновить</span>
            </button>
            <a 
              href="https://challonge.com/aitu_gaming" 
              target="_blank" 
              rel="noopener noreferrer" 
              class="btn-bracket-external"
            >
              <span>Открыть на Challonge.com ↗</span>
            </a>
          </div>
        </div>

        <!-- Embedded Challonge Module Iframe -->
        <div class="challonge-embed-container">
          <iframe 
            :key="iframeKey"
            src="https://challonge.com/aitu_gaming/module" 
            width="100%" 
            height="650" 
            frameborder="0" 
            scrolling="auto" 
            allowtransparency="true" 
            class="rounded-xl border border-zinc-800 shadow-2xl bg-zinc-950 challonge-frame"
            id="challonge-module-iframe"
          ></iframe>
        </div>

        <!-- Notice Banner Under Bracket -->
        <div class="bracket-notice-banner" id="bracket-notice-banner">
          <div class="notice-icon-box">
            <svg viewBox="0 0 20 20" width="20" height="20" fill="currentColor">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
            </svg>
          </div>
          <div class="notice-text">
            <strong>Важное уведомление:</strong>
            Команды, прошедшие в 1/4 финала (топ-8), завершают матчи на сегодня и получают инвайт на оффлайн-этап в C.1.3.267P на завтра.
          </div>
        </div>
      </section>

      <!-- 4. Regulations Section (Пункт 1.1 и правила) -->
      <section class="section-card" id="regulations-section">
        <div class="section-header">
          <div class="section-header-left">
            <span class="section-sub">Официальные правила турнира</span>
            <h2 class="section-title">Регламент соревнований</h2>
          </div>
          <div class="section-badge rules-badge">
            <span>CS2 2v2 Wingman Official Rules</span>
          </div>
        </div>

        <!-- Regulations Accordion / Cards -->
        <div class="regulations-list">
          <!-- Highlighted clause 1.1 & 1.1.5 -->
          <div class="rule-card rule-highlight">
            <div class="rule-title-row">
              <span class="rule-num">1.1</span>
              <h3 class="rule-heading">Формат и двухдневная структура соревнований</h3>
            </div>
            <div class="rule-body">
              <p class="rule-quote">
                «1.1. Турнир состоит из двух этапов: квалификационный этап проходит в онлайн-формате на платформе Fastcup до определения 8 лучших команд. Финальный этап (топ-8) проводится в offline-формате в кабинете C.1.3.267P Esport Club».
              </p>
              <div class="rule-sub-item">
                <span class="sub-num">1.1.5</span>
                <p class="rule-quote">
                  «1.1.5. Для онлайн-этапа игроки подключаются со своих устройств через Fastcup (серверы Астана). На оффлайн-этапе матчи проводятся на ПК клуба с предоставленных организаторами аккаунтов».
                </p>
              </div>
            </div>
          </div>

          <!-- Section 2: Maps and Match Format -->
          <div class="rule-card">
            <div class="rule-title-row">
              <span class="rule-num">2.0</span>
              <h3 class="rule-heading">Маппул и структура матчей CS2 (Напарники)</h3>
            </div>
            <div class="rule-body">
              <div class="rules-grid">
                <div class="rule-item">
                  <strong>Маппул режима Напарники:</strong>
                  <span>de_inferno, de_nuke, de_vertigo, de_overpass, de_mirage.</span>
                </div>
                <div class="rule-item">
                  <strong>Выбор карт:</strong>
                  <span>Система Veto (Ban-Ban-Pick) на платформе Fastcup перед началом встречи.</span>
                </div>
                <div class="rule-item">
                  <strong>Онлайн-этап (Суббота):</strong>
                  <span>Все матчи стадий 1/64, 1/32, 1/16 играются в формате Best of 1 (BO1).</span>
                </div>
                <div class="rule-item">
                  <strong>Оффлайн-плейофф (Воскресенье):</strong>
                  <span>1/4 финала и 1/2 финала — Best of 1 (BO1); Grand Final — Best of 3 (BO3).</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Section 3: Technical Platform & Anti-Cheat -->
          <div class="rule-card">
            <div class="rule-title-row">
              <span class="rule-num">3.0</span>
              <h3 class="rule-heading">Платформа Fastcup, Античит и Связь</h3>
            </div>
            <div class="rule-body">
              <div class="rules-grid">
                <div class="rule-item">
                  <strong>Античит:</strong>
                  <span>Обязательное использование Fastcup Anti-Cheat всеми участниками онлайн-квалификации.</span>
                </div>
                <div class="rule-item">
                  <strong>Серверы:</strong>
                  <span>Матчи проводятся на выделенных серверах локации Астана с тикрейтом CS2 Sub-tick.</span>
                </div>
                <div class="rule-item">
                  <strong>Координация:</strong>
                  <span>Капитаны команд обязаны находиться в Discord сервере AITU Gaming в канале #cs2-tournaments.</span>
                </div>
                <div class="rule-item">
                  <strong>Готовность:</strong>
                  <span>Время на подключение к лобби после создания матча — не более 10 минут.</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Section 4: LAN Playoffs Requirements -->
          <div class="rule-card">
            <div class="rule-title-row">
              <span class="rule-num">4.0</span>
              <h3 class="rule-heading">Регламент оффлайн-стадии в Esport Club (C.1.3.267P)</h3>
            </div>
            <div class="rule-body">
              <div class="rules-grid">
                <div class="rule-item">
                  <strong>Прибытие команд:</strong>
                  <span>Команды топ-8 обязаны прибыть в кабинет C.1.3.267P за 30 минут до начала игр для чекина.</span>
                </div>
                <div class="rule-item">
                  <strong>Оборудование:</strong>
                  <span>Игровые ПК клуба предоставляются организаторами; разрешено подключение своих периферийных девайсов (мышь, клавиатура, наушники).</span>
                </div>
                <div class="rule-item">
                  <strong>Игровые аккаунты:</strong>
                  <span>Матчи на оффлайн-этапе проводятся на предоставленных турнирных аккаунтах организаторов.</span>
                </div>
                <div class="rule-item">
                  <strong>Судейство:</strong>
                  <span>На LAN-этапе присутствуют судьи AITU Gaming Hub для фиксации результатов и стрима финала.</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Bottom Quick Contact / Info Card -->
      <section class="footer-cta-card">
        <div class="cta-left">
          <h3 class="cta-title">Остались вопросы или нужна помощь судей?</h3>
          <p class="cta-desc">
            Свяжитесь с организаторами через официального Telegram-бота или в Discord AITU Gaming.
          </p>
        </div>
        <div class="cta-actions">
          <a 
            :href="`https://t.me/${botUsername}`" 
            target="_blank" 
            rel="noopener noreferrer" 
            class="btn-primary-action"
          >
            Написать в Telegram Bot ↗
          </a>
          <router-link to="/tournaments" class="btn-secondary-action">
            Вернуться ко всем турнирам
          </router-link>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import GameLogo from '../components/GameLogo.vue'

const router = useRouter()
const botUsername = ref('aitu_gaming_bot')
const iframeKey = ref(0)

const isAuthenticated = computed(() => !!localStorage.getItem('access_token'))

const refreshIframe = () => {
  iframeKey.value++
}

const logout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user')
  router.push('/login')
}
</script>

<style scoped>
.tournament-hub-page {
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
  border-bottom: 1px solid var(--surface-border, rgba(255, 255, 255, 0.08));
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
  color: var(--accent, #ef4444);
  background: var(--accent-subtle, rgba(239, 68, 68, 0.12));
  border: 1px solid var(--accent-border, rgba(239, 68, 68, 0.35));
  padding: 0.1rem 0.5rem;
  border-radius: 9999px;
}

.nav {
  display: flex;
  gap: 0.5rem;
}

.nav-item {
  color: var(--text-secondary, #94a3b8);
  font-size: 0.88rem;
  font-weight: 500;
  padding: 0.4rem 0.8rem;
  border-radius: var(--radius-sm, 6px);
  transition: all 0.15s ease;
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

.btn-tg {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.82rem;
  font-weight: 500;
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.1);
  border: 1px solid rgba(56, 189, 248, 0.25);
  padding: 0.35rem 0.75rem;
  border-radius: var(--radius-sm, 6px);
  transition: all 0.2s ease;
}

.btn-tg:hover {
  background: rgba(56, 189, 248, 0.18);
  border-color: rgba(56, 189, 248, 0.45);
}

.btn-ghost {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-secondary, #94a3b8);
  padding: 0.35rem 0.75rem;
  border-radius: var(--radius-sm, 6px);
  transition: all 0.2s ease;
}

.btn-ghost:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.05);
}

.text-danger {
  color: var(--danger, #ef4444) !important;
}

/* Page Container */
.hub-container {
  max-width: 1360px;
  margin: 0 auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* Breadcrumb */
.hub-breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.85rem;
  color: var(--text-muted, #64748b);
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--text-secondary, #94a3b8);
  font-weight: 500;
  transition: color 0.15s ease;
}

.back-link:hover {
  color: #fff;
}

.sep {
  opacity: 0.5;
}

.curr-crumb {
  color: #e2e8f0;
  font-weight: 500;
}

/* 1. Hero Card & Status Banner */
.hero-card {
  position: relative;
  background: linear-gradient(135deg, rgba(26, 32, 44, 0.85) 0%, rgba(15, 20, 30, 0.95) 100%);
  border: 1px solid rgba(245, 158, 11, 0.25);
  border-radius: 16px;
  padding: 2.25rem;
  overflow: hidden;
  box-shadow: 0 12px 35px -8px rgba(0, 0, 0, 0.6), 0 0 30px rgba(245, 158, 11, 0.06);
}

.hero-bg-glow {
  position: absolute;
  top: -60px;
  right: -60px;
  width: 320px;
  height: 320px;
  background: radial-gradient(circle, rgba(245, 158, 11, 0.18) 0%, rgba(239, 68, 68, 0.08) 50%, transparent 70%);
  pointer-events: none;
  filter: blur(40px);
}

.hero-content {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.hero-top-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;
}

.game-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  background: rgba(255, 255, 255, 0.06);
  padding: 0.35rem 0.85rem;
  border-radius: 9999px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.game-name {
  font-size: 0.88rem;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.02em;
}

.mode-pill {
  font-size: 0.78rem;
  font-weight: 600;
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.12);
  padding: 0.15rem 0.5rem;
  border-radius: 6px;
}

.event-id-tag {
  font-size: 0.75rem;
  font-family: monospace;
  color: var(--text-muted, #64748b);
  background: rgba(0, 0, 0, 0.3);
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.hero-title {
  font-size: 2.25rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: #ffffff;
  line-height: 1.2;
}

.hero-subtitle {
  font-size: 1.05rem;
  font-weight: 500;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* Stage Indicators */
.stage-indicators-wrap {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
  margin-top: 0.25rem;
}

.stage-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.65rem 1.2rem;
  border-radius: 12px;
  font-size: 0.92rem;
  font-weight: 600;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stage-badge:hover {
  transform: translateY(-1px);
}

.live-stage {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.18) 0%, rgba(16, 185, 129, 0.08) 100%);
  border: 1px solid rgba(16, 185, 129, 0.45);
  color: #34d399;
  box-shadow: 0 0 16px rgba(16, 185, 129, 0.15);
}

.status-pulse-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background-color: #10b981;
  position: relative;
}

.status-pulse-dot::before {
  content: '';
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  background-color: #10b981;
  opacity: 0.6;
  animation: pulse-dot 1.8s infinite;
}

@keyframes pulse-dot {
  0% { transform: scale(1); opacity: 0.7; }
  50% { transform: scale(2.2); opacity: 0; }
  100% { transform: scale(1); opacity: 0; }
}

.upcoming-stage {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.16) 0%, rgba(239, 68, 68, 0.06) 100%);
  border: 1px solid rgba(239, 68, 68, 0.4);
  color: #f87171;
  box-shadow: 0 0 16px rgba(239, 68, 68, 0.12);
}

.lan-icon {
  font-size: 1rem;
}

/* Hero Stats Grid */
.hero-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.85rem;
  margin-top: 0.5rem;
}

.stat-pill {
  background: rgba(10, 13, 20, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 0.75rem 1rem;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.stat-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
  font-weight: 600;
}

.stat-value {
  font-size: 0.95rem;
  font-weight: 700;
  color: #f1f5f9;
}

/* Hero CTA Bar */
.hero-cta-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.85rem;
  margin-top: 0.75rem;
}

.btn-primary-action {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: #fff;
  font-size: 0.9rem;
  font-weight: 600;
  padding: 0.65rem 1.25rem;
  border-radius: 8px;
  transition: all 0.2s ease;
  box-shadow: 0 4px 14px rgba(239, 68, 68, 0.35);
}

.btn-primary-action:hover {
  background: linear-gradient(135deg, #f87171 0%, #ef4444 100%);
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(239, 68, 68, 0.5);
}

.btn-secondary-action {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(255, 255, 255, 0.07);
  color: #e2e8f0;
  font-size: 0.9rem;
  font-weight: 500;
  padding: 0.65rem 1.15rem;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  transition: all 0.2s ease;
}

.btn-secondary-action:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  border-color: rgba(255, 255, 255, 0.25);
}

.btn-telegram-action {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: rgba(56, 189, 248, 0.1);
  color: #38bdf8;
  font-size: 0.9rem;
  font-weight: 600;
  padding: 0.65rem 1.15rem;
  border-radius: 8px;
  border: 1px solid rgba(56, 189, 248, 0.3);
  margin-left: auto;
  transition: all 0.2s ease;
}

.btn-telegram-action:hover {
  background: rgba(56, 189, 248, 0.2);
  border-color: rgba(56, 189, 248, 0.5);
}

/* Sections */
.section-card {
  background: var(--surface-bg, #10141f);
  border: 1px solid var(--surface-border, rgba(255, 255, 255, 0.08));
  border-radius: 16px;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.section-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  padding-bottom: 1rem;
}

.section-sub {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #f59e0b;
  font-weight: 700;
  display: block;
  margin-bottom: 0.25rem;
}

.section-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.01em;
}

.section-badge {
  font-size: 0.8rem;
  font-weight: 600;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 0.3rem 0.75rem;
  border-radius: 9999px;
}

.rules-badge {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.25);
}

/* Timeline Grid */
.timeline-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 1.5rem;
}

.stage-card {
  background: rgba(16, 20, 31, 0.7);
  border-radius: 14px;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: all 0.2s ease;
}

.stage-card:hover {
  transform: translateY(-2px);
}

.stage-active {
  border-color: rgba(16, 185, 129, 0.4);
  background: linear-gradient(180deg, rgba(16, 185, 129, 0.06) 0%, rgba(16, 20, 31, 0.9) 100%);
  box-shadow: 0 4px 20px -2px rgba(16, 185, 129, 0.12);
}

.stage-upcoming {
  border-color: rgba(239, 68, 68, 0.35);
  background: linear-gradient(180deg, rgba(239, 68, 68, 0.05) 0%, rgba(16, 20, 31, 0.9) 100%);
  box-shadow: 0 4px 20px -2px rgba(239, 68, 68, 0.1);
}

.stage-card-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.stage-num-badge {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.4);
  color: #34d399;
  font-size: 1.2rem;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.offline-badge {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.4);
  color: #f87171;
}

.stage-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.stage-day-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.active-tag {
  color: #34d399;
}

.pulse-ring {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #10b981;
}

.upcoming-tag {
  color: #f87171;
}

.stage-name {
  font-size: 1.25rem;
  font-weight: 700;
  color: #fff;
}

.stage-meta-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  background: rgba(0, 0, 0, 0.25);
  padding: 1rem;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.stage-meta-item {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  font-size: 0.88rem;
}

.meta-label {
  font-size: 0.75rem;
  color: #94a3b8;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.meta-value {
  color: #e2e8f0;
  font-weight: 500;
}

.meta-value.highlight {
  color: #38bdf8;
  font-weight: 600;
}

.meta-value.highlight-accent {
  color: #f59e0b;
  font-weight: 700;
}

.stage-footer {
  margin-top: auto;
  padding: 0.6rem 0.85rem;
  border-radius: 8px;
  font-size: 0.82rem;
  font-weight: 600;
  display: flex;
  align-items: center;
}

.active-footer {
  background: rgba(16, 185, 129, 0.1);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.25);
}

.upcoming-footer {
  background: rgba(239, 68, 68, 0.1);
  color: #fca5a5;
  border: 1px solid rgba(239, 68, 68, 0.2);
}

/* Bracket Section */
.bracket-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.btn-bracket-reload {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #cbd5e1;
  font-size: 0.82rem;
  font-weight: 500;
  padding: 0.4rem 0.85rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-bracket-reload:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
}

.btn-bracket-external {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.3);
  color: #f59e0b;
  font-size: 0.82rem;
  font-weight: 600;
  padding: 0.4rem 0.85rem;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.btn-bracket-external:hover {
  background: rgba(245, 158, 11, 0.22);
  border-color: rgba(245, 158, 11, 0.5);
}

.challonge-embed-container {
  width: 100%;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: #090d16;
}

.challonge-frame {
  display: block;
  width: 100%;
  height: 650px;
  border: none;
  background-color: #090d16;
}

/* Notice Banner Under Bracket */
.bracket-notice-banner {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(245, 158, 11, 0.04) 100%);
  border: 1px solid rgba(245, 158, 11, 0.35);
  padding: 1.15rem 1.4rem;
  border-radius: 12px;
  color: #fef3c7;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

.notice-icon-box {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: rgba(245, 158, 11, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #f59e0b;
  flex-shrink: 0;
}

.notice-text {
  font-size: 0.95rem;
  line-height: 1.5;
  color: #fde68a;
}

.notice-text strong {
  color: #fff;
  margin-right: 0.35rem;
}

/* Regulations Section */
.regulations-list {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.rule-card {
  background: rgba(16, 20, 31, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.rule-highlight {
  border-color: rgba(245, 158, 11, 0.4);
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(16, 20, 31, 0.8) 100%);
  box-shadow: 0 0 25px rgba(245, 158, 11, 0.08);
}

.rule-title-row {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

.rule-num {
  font-size: 0.82rem;
  font-weight: 800;
  font-family: monospace;
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.15);
  border: 1px solid rgba(245, 158, 11, 0.3);
  padding: 0.2rem 0.55rem;
  border-radius: 6px;
}

.rule-heading {
  font-size: 1.15rem;
  font-weight: 700;
  color: #fff;
}

.rule-body {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.rule-quote {
  font-size: 1.02rem;
  line-height: 1.6;
  color: #f1f5f9;
  font-weight: 500;
  background: rgba(0, 0, 0, 0.35);
  padding: 1rem 1.25rem;
  border-radius: 8px;
  border-left: 4px solid #f59e0b;
}

.rule-sub-item {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-top: 0.5rem;
}

.sub-num {
  font-size: 0.78rem;
  font-weight: 700;
  color: #38bdf8;
  font-family: monospace;
}

.rules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
}

.rule-item {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.05);
  padding: 0.85rem 1rem;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: 0.88rem;
}

.rule-item strong {
  color: #94a3b8;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.rule-item span {
  color: #e2e8f0;
  line-height: 1.4;
}

/* Footer CTA Card */
.footer-cta-card {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.12) 0%, rgba(16, 20, 31, 0.9) 100%);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 16px;
  padding: 2rem 2.25rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1.5rem;
}

.cta-left {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  max-width: 650px;
}

.cta-title {
  font-size: 1.3rem;
  font-weight: 700;
  color: #fff;
}

.cta-desc {
  font-size: 0.92rem;
  color: #94a3b8;
}

.cta-actions {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  flex-wrap: wrap;
}

/* Responsive */
@media (max-width: 768px) {
  .hero-card {
    padding: 1.5rem;
  }
  .hero-title {
    font-size: 1.65rem;
  }
  .section-card {
    padding: 1.25rem;
  }
  .challonge-frame {
    height: 500px;
  }
  .footer-cta-card {
    padding: 1.5rem;
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
