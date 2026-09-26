<template>
  <span class="game-logo-wrapper" :style="{ width: size + 'px', height: size + 'px' }">
    <!-- CS2 Official Logo -->
    <svg v-if="slug === 'CS2'" :width="size" :height="size" viewBox="0 0 32 32" fill="none">
      <rect width="32" height="32" rx="6" fill="#1e1e24"/>
      <!-- CS2 iconic soldier silhouette & orange slash -->
      <path d="M11 7h10l-1.5 5h-7L11 7z" fill="#f59e0b"/>
      <path d="M9 13.5h11.5l-1.5 5H7.5l1.5-5z" fill="#e2e8f0"/>
      <path d="M7 20h11.5l-1.5 5H5.5L7 20z" fill="#e2e8f0"/>
      <path d="M21 16l3-1.5v6l-3-1.5v-3z" fill="#ef4444"/>
      <circle cx="23" cy="11" r="2.5" fill="#f59e0b"/>
    </svg>

    <!-- Dota 2 Official Red Stone Emblem -->
    <svg v-else-if="slug === 'DOTA2'" :width="size" :height="size" viewBox="0 0 32 32" fill="none">
      <rect width="32" height="32" rx="6" fill="#181313"/>
      <!-- Dota 2 red stylized map emblem -->
      <path d="M8 8h6l-3 4H8V8z" fill="#dc2626"/>
      <path d="M21 21h-5l3-4h5l-3 4z" fill="#dc2626"/>
      <path d="M9 23l14-14h2L11 23H9z" fill="#ef4444"/>
      <path d="M7 6c-.55 0-1 .45-1 1v18c0 .55.45 1 1 1h18c.55 0 1-.45 1-1V7c0-.55-.45-1-1-1H7zm1 2h16v16H8V8z" fill="#7f1d1d" opacity="0.4"/>
    </svg>

    <!-- Valorant Official V Emblem -->
    <svg v-else-if="slug === 'VALORANT'" :width="size" :height="size" viewBox="0 0 32 32" fill="none">
      <rect width="32" height="32" rx="6" fill="#121820"/>
      <!-- Official Valorant V icon -->
      <path d="M7 9l7 14h3.5L24 9h-4.2l-4.1 8.8L11.5 9H7z" fill="#ff4655"/>
      <path d="M19.5 9l5 10V9h-5z" fill="#ff4655" opacity="0.6"/>
    </svg>

    <!-- EA Sports FC / FIFA Triangle Emblem -->
    <svg v-else-if="slug === 'FIFA'" :width="size" :height="size" viewBox="0 0 32 32" fill="none">
      <rect width="32" height="32" rx="6" fill="#0d1b14"/>
      <!-- EA Sports FC iconic triangle badge -->
      <path d="M16 6L26 24H6L16 6z" fill="#10b981"/>
      <path d="M16 10l6.5 12h-13L16 10z" fill="#0d1b14"/>
      <path d="M13 15h6v2h-4v2h3v2h-5v-6z" fill="#ffffff"/>
    </svg>

    <!-- PUBG Mobile Official Helmet/Emblem -->
    <svg v-else-if="slug === 'PUBG'" :width="size" :height="size" viewBox="0 0 32 32" fill="none">
      <rect width="32" height="32" rx="6" fill="#201a14"/>
      <!-- Level 3 Helmet silhouette -->
      <path d="M9 14c0-4.4 3.1-8 7-8s7 3.6 7 8v5H9v-5z" fill="#f59e0b"/>
      <path d="M8 19h16v4c0 2-2 3-4 3H12c-2 0-4-1-4-3v-4z" fill="#78350f"/>
      <rect x="11" y="16" width="10" height="3" rx="1" fill="#090a0f"/>
      <path d="M15 16v3h2v-3h-2z" fill="#f59e0b"/>
    </svg>

    <!-- Mobile Legends (MLBB) Official Crown/M Logo -->
    <svg v-else-if="slug === 'MLBB'" :width="size" :height="size" viewBox="0 0 32 32" fill="none">
      <rect width="32" height="32" rx="6" fill="#1c1626"/>
      <!-- MLBB M Shield -->
      <path d="M16 6l9 5v8c0 5-4 8.5-9 10-5-1.5-9-5-9-10v-8l9-5z" fill="#a855f7"/>
      <path d="M11 12l5 4 5-4v8l-5-2-5 2v-8z" fill="#fbbf24"/>
      <circle cx="16" cy="10" r="1.5" fill="#ffffff"/>
    </svg>

    <!-- Fallback / Other Games Controller -->
    <svg v-else :width="size" :height="size" viewBox="0 0 32 32" fill="none">
      <rect width="32" height="32" rx="6" fill="#1e2029"/>
      <path d="M9 13c-2 0-3 1.5-3 4v3c0 2 1.5 3 3 2l3-2h8l3 2c1.5 1 3 0 3-2v-3c0-2.5-1-4-3-4H9z" fill="#94a3b8"/>
      <circle cx="11" cy="17" r="1.2" fill="#ef4444"/>
      <circle cx="21" cy="16" r="1" fill="#ef4444"/>
      <circle cx="23" cy="18" r="1" fill="#ef4444"/>
    </svg>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  discipline: {
    type: String,
    default: 'OTHER'
  },
  size: {
    type: [Number, String],
    default: 24
  }
})

const slug = computed(() => {
  return (props.discipline || 'OTHER').toUpperCase()
})
</script>

<style scoped>
.game-logo-wrapper {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  vertical-align: middle;
}

.game-logo-wrapper svg {
  display: block;
}
</style>
