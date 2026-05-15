<template>
  <div class="min-h-screen bg-gray-50 flex">

    <!-- ── Left Sidebar ─────────────────────────────────────── -->
    <aside class="w-56 h-screen bg-white border-r border-gray-200 flex flex-col fixed top-0 left-0 z-30">

      <!-- Brand -->
      <div class="px-4 py-5 border-b border-gray-100">
        <div class="flex items-center space-x-2.5">
          <div class="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow">
            <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <div>
            <div class="text-sm font-black text-gray-900 tracking-tight">SMART RADAR</div>
            <div class="text-xs text-gray-400 leading-tight">Command Center</div>
          </div>
        </div>
        <div class="flex items-center space-x-1.5 mt-3">
          <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          <span class="text-xs text-green-600 font-semibold">Live</span>
          <span v-if="postsStore.threatPosts.length > 0" class="ml-auto bg-orange-100 text-orange-700 text-xs rounded-full px-2 py-0.5 font-medium">
            {{ postsStore.threatPosts.length }} threats
          </span>
        </div>
      </div>

      <!-- Nav -->
      <nav class="flex-1 px-3 py-4 overflow-y-auto space-y-0.5">

        <p class="sidebar-section-label">Intelligence</p>
        <router-link to="/" class="sidebar-link" :class="$route.path === '/' ? 'sidebar-active' : 'sidebar-inactive'">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>
          <span>Dashboard</span>
        </router-link>
        <router-link to="/clusters" class="sidebar-link" :class="$route.path.startsWith('/clusters') ? 'sidebar-active' : 'sidebar-inactive'">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>
          <span>Clusters</span>
        </router-link>
        <router-link to="/narratives" class="sidebar-link" :class="$route.path === '/narratives' ? 'sidebar-active' : 'sidebar-inactive'">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
          <span>Narratives</span>
        </router-link>
        <router-link to="/search" class="sidebar-link" :class="$route.path === '/search' ? 'sidebar-active' : 'sidebar-inactive'">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0118 0z"/></svg>
          <span>Search</span>
        </router-link>

        <p class="sidebar-section-label mt-4">Publishing</p>
        <router-link to="/post-creator" class="sidebar-link" :class="$route.path === '/post-creator' ? 'sidebar-active' : 'sidebar-inactive'">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
          <span>Post Creator</span>
        </router-link>
        <router-link to="/research" class="sidebar-link" :class="$route.path === '/research' ? 'sidebar-active' : 'sidebar-inactive'">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0118 0z"/></svg>
          <span>Research Hub</span>
        </router-link>
        <router-link to="/posts" class="sidebar-link" :class="$route.path === '/posts' ? 'sidebar-active' : 'sidebar-inactive'">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
          <span>Posts</span>
        </router-link>
        <router-link to="/calendar" class="sidebar-link" :class="$route.path === '/calendar' ? 'sidebar-active' : 'sidebar-inactive'">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
          <span>Calendar</span>
        </router-link>
        <router-link to="/analytics" class="sidebar-link" :class="$route.path === '/analytics' ? 'sidebar-active' : 'sidebar-inactive'">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
          <span>Analytics</span>
        </router-link>
        <router-link to="/publish" class="sidebar-link" :class="$route.path === '/publish' ? 'sidebar-active' : 'sidebar-inactive'">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>
          <span>Publish Hub</span>
        </router-link>
        <router-link to="/drafts" class="sidebar-link" :class="$route.path === '/drafts' ? 'sidebar-active' : 'sidebar-inactive'">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/></svg>
          <span class="flex-1">Drafts</span>
          <span v-if="pendingCount > 0" class="bg-orange-500 text-white text-xs rounded-full min-w-5 h-5 px-1 flex items-center justify-center font-medium">{{ pendingCount }}</span>
        </router-link>
        <router-link to="/social-accounts" class="sidebar-link" :class="$route.path === '/social-accounts' ? 'sidebar-active' : 'sidebar-inactive'">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
          <span>Social Accounts</span>
        </router-link>
        <router-link to="/templates" class="sidebar-link" :class="$route.path === '/templates' ? 'sidebar-active' : 'sidebar-inactive'">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/></svg>
          <span>Templates</span>
        </router-link>

        <p class="sidebar-section-label mt-4">Automation</p>
        <router-link to="/automation" class="sidebar-link" :class="$route.path === '/automation' ? 'sidebar-active' : 'sidebar-inactive'">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          <span>Automation</span>
        </router-link>
        <router-link to="/external-news" class="sidebar-link" :class="$route.path === '/external-news' ? 'sidebar-active' : 'sidebar-inactive'">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"/></svg>
          <span>News Queue</span>
        </router-link>
        <router-link to="/scraper" class="sidebar-link" :class="$route.path === '/scraper' ? 'sidebar-active' : 'sidebar-inactive'">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/></svg>
          <span>Scraper</span>
        </router-link>

      </nav>

      <!-- System time at bottom -->
      <div class="px-4 py-3 border-t border-gray-100">
        <div class="text-xs text-gray-400">System Time</div>
        <div class="text-sm font-bold text-gray-800 font-mono tracking-wide">{{ currentTime }}</div>
      </div>
    </aside>

    <!-- ── Main content ────────────────────────────────────────── -->
    <div class="flex-1 ml-56 min-h-screen">
      <router-view />
    </div>

  </div>

  <!-- Global Response Panel -->
  <ResponsePanel />
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { usePostsStore } from '@/stores/posts'
import { useClustersStore } from '@/stores/clusters'
import { useSmartPostStore } from '@/stores/smartpost'
import ResponsePanel from '@/components/ResponsePanel.vue'

const postsStore   = usePostsStore()
const clustersStore = useClustersStore()
const smartPostStore = useSmartPostStore()
const pendingCount = computed(() => smartPostStore.pendingDrafts.length)

const currentTime = ref('')
let timeInterval = null
const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

onMounted(async () => {
  updateTime()
  timeInterval = setInterval(updateTime, 1000)
  try {
    await clustersStore.fetchClusters()
    await postsStore.fetchPosts()
  } catch (e) {
    console.error('App init error:', e)
  }
})
onUnmounted(() => { if (timeInterval) clearInterval(timeInterval) })
</script>

<style scoped>
.sidebar-link {
  @apply flex items-center space-x-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-all w-full;
}
.sidebar-active {
  @apply bg-blue-50 text-blue-700;
}
.sidebar-inactive {
  @apply text-gray-600 hover:bg-gray-50 hover:text-gray-900;
}
.sidebar-section-label {
  @apply text-xs font-semibold text-gray-400 uppercase tracking-wider px-3 py-1.5;
}
</style>
