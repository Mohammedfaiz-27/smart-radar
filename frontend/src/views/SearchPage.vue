<template>
  <div class="min-h-screen bg-[#F8FAFC]">
    <!-- Page Header -->
    <div class="bg-white border-b border-gray-100 px-8 py-6">
      <div class="max-w-7xl mx-auto">
        <h2 class="text-xl font-bold text-gray-900">Search Intelligence</h2>
        <p class="text-sm text-gray-500 mt-0.5">Search across all collected posts and news by keyword or sentence</p>
      </div>
    </div>

    <div class="max-w-7xl mx-auto px-8 py-6 space-y-5">

      <!-- Search Bar -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
        <form @submit.prevent="search" class="flex flex-col sm:flex-row gap-3">
          <div class="flex-1 relative">
            <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0118 0z"/>
            </svg>
            <input
              v-model="query"
              type="text"
              placeholder='Search e.g. "election", "Swiggy delivery", "DMK rally"...'
              class="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              autofocus
            />
          </div>

          <!-- Sentiment filter -->
          <select v-model="filterSentiment" class="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none bg-white">
            <option value="">Any Sentiment</option>
            <option value="Positive">Positive</option>
            <option value="Negative">Negative</option>
            <option value="Neutral">Neutral</option>
          </select>

          <!-- Platform filter -->
          <select v-model="filterPlatform" class="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none bg-white">
            <option value="">All Platforms</option>
            <option value="X">X (Twitter)</option>
            <option value="Facebook">Facebook</option>
            <option value="YouTube">YouTube</option>
          </select>

          <button
            type="submit"
            :disabled="!query.trim() || loading"
            class="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-colors flex items-center space-x-2"
          >
            <svg v-if="loading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0118 0z"/>
            </svg>
            <span>{{ loading ? 'Searching…' : 'Search' }}</span>
          </button>
        </form>

        <!-- Recent searches -->
        <div v-if="recentSearches.length && !searched" class="mt-3 flex items-center gap-2 flex-wrap">
          <span class="text-xs text-gray-400">Recent:</span>
          <button
            v-for="s in recentSearches" :key="s"
            @click="query = s; search()"
            class="text-xs px-2.5 py-1 bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-full transition-colors"
          >{{ s }}</button>
        </div>
      </div>

      <!-- Results summary tabs -->
      <div v-if="searched && !loading" class="flex items-center justify-between flex-wrap gap-3">
        <div class="flex gap-2">
          <button
            v-for="tab in tabs" :key="tab.id"
            @click="activeTab = tab.id"
            class="px-4 py-1.5 text-sm rounded-lg font-medium transition-all"
            :class="activeTab === tab.id
              ? 'bg-blue-600 text-white'
              : 'bg-white border border-gray-200 text-gray-600 hover:border-blue-300'"
          >
            {{ tab.label }}
            <span class="ml-1.5 px-1.5 py-0.5 rounded text-xs"
              :class="activeTab === tab.id ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-500'"
            >{{ tab.count }}</span>
          </button>
        </div>
        <p class="text-sm text-gray-500">
          {{ visibleResults.length }} result{{ visibleResults.length !== 1 ? 's' : '' }} for
          <strong class="text-gray-800">"{{ lastQuery }}"</strong>
        </p>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading" class="space-y-3">
        <div v-for="i in 6" :key="i" class="bg-white rounded-xl border border-gray-100 p-5 animate-pulse">
          <div class="flex items-start space-x-3">
            <div class="w-8 h-8 bg-gray-100 rounded-lg flex-shrink-0"></div>
            <div class="flex-1 space-y-2">
              <div class="h-4 bg-gray-100 rounded w-3/4"></div>
              <div class="h-3 bg-gray-100 rounded w-full"></div>
              <div class="h-3 bg-gray-100 rounded w-2/3"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- No results -->
      <div v-else-if="searched && visibleResults.length === 0" class="bg-white rounded-xl border border-gray-100 p-12 text-center">
        <svg class="mx-auto h-12 w-12 text-gray-300 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0118 0z"/>
        </svg>
        <h3 class="text-sm font-semibold text-gray-900">No results found</h3>
        <p class="text-sm text-gray-500 mt-1">Try a different keyword or change the filters.</p>
      </div>

      <!-- Results list -->
      <div v-else-if="searched && !loading" class="space-y-3">
        <div
          v-for="post in visibleResults" :key="post.id"
          class="bg-white rounded-xl border border-gray-100 shadow-sm p-5 hover:border-gray-200 hover:shadow-md transition-all"
        >
          <div class="flex items-start justify-between gap-4">
            <div class="flex items-start space-x-3 flex-1 min-w-0">
              <!-- Platform badge -->
              <div class="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 text-sm font-bold"
                :class="platformBg(post.platform)">
                {{ platformIcon(post.platform) }}
              </div>
              <div class="flex-1 min-w-0">
                <!-- Meta row -->
                <div class="flex items-center gap-2 flex-wrap mb-1">
                  <span class="text-xs font-semibold text-gray-800">{{ post.author_username || post.author || 'Unknown' }}</span>
                  <span class="text-xs text-gray-400">· {{ post.platform }}</span>
                  <span v-if="post.cluster_name || post.matched_clusters?.[0]?.cluster_name" class="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full">{{ post.cluster_name || post.matched_clusters?.[0]?.cluster_name }}</span>
                  <span v-if="post.is_threat || post.intelligence?.threat_level === 'high'" class="text-xs px-2 py-0.5 bg-red-50 text-red-700 rounded-full">⚠ Threat</span>
                </div>
                <!-- Content -->
                <p class="text-sm text-gray-800 line-clamp-3" v-html="highlight(post.content)"></p>
                <!-- Footer -->
                <div class="mt-2 flex items-center gap-3 text-xs text-gray-400 flex-wrap">
                  <span>{{ formatDate(post.posted_at || post.published_at) }}</span>
                  <span v-if="post.engagement_metrics?.likes">❤ {{ post.engagement_metrics.likes }}</span>
                  <span v-if="post.engagement_metrics?.shares">🔁 {{ post.engagement_metrics.shares }}</span>
                  <span v-if="post.engagement_metrics?.views">👁 {{ fmtNum(post.engagement_metrics.views) }}</span>
                  <a v-if="post.url || post.post_url" :href="post.url || post.post_url" target="_blank"
                    class="ml-auto text-blue-500 hover:underline">View →</a>
                </div>
              </div>
            </div>
            <!-- Sentiment pill -->
            <span class="flex-shrink-0 text-xs px-2.5 py-1 rounded-full font-medium capitalize"
              :class="sentimentClass(post.sentiment)">
              {{ post.sentiment || 'neutral' }}
            </span>
          </div>
        </div>
      </div>

      <!-- Initial / empty state -->
      <div v-if="!searched && !loading" class="bg-white rounded-xl border border-gray-100 p-12 text-center">
        <svg class="mx-auto h-14 w-14 text-gray-200 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0118 0z"/>
        </svg>
        <h3 class="text-base font-semibold text-gray-700 mb-1">Search your intelligence data</h3>
        <p class="text-sm text-gray-400 max-w-sm mx-auto">
          Type any keyword or sentence — searches all collected social posts in real time.
        </p>
        <div class="mt-5 flex flex-wrap justify-center gap-2">
          <button
            v-for="s in suggestions" :key="s"
            @click="query = s; search()"
            class="text-xs px-3 py-1.5 bg-gray-50 hover:bg-blue-50 hover:text-blue-700 border border-gray-200 hover:border-blue-200 text-gray-600 rounded-full transition-colors"
          >{{ s }}</button>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'

const query         = ref('')
const filterSentiment = ref('')
const filterPlatform  = ref('')
const loading       = ref(false)
const searched      = ref(false)
const lastQuery     = ref('')
const allPosts      = ref([])
const activeTab     = ref('all')
const recentSearches = ref(JSON.parse(localStorage.getItem('sr_recent_searches') || '[]'))

const suggestions = ['Swiggy', 'Zomato', 'DMK', 'AIADMK', 'election', 'complaint', 'rally']

// ── Filter posts client-side by keyword + tab ─────────────────────
const visibleResults = computed(() => {
  const q = lastQuery.value.trim().toLowerCase()
  return allPosts.value.filter(p => {
    const text    = (p.content || p.post_text || '').toLowerCase()
    const author  = (p.author || p.author_username || '').toLowerCase()
    const matchQ  = !q || text.includes(q) || author.includes(q)
    const matchS  = !filterSentiment.value || (p.sentiment || '').toLowerCase() === filterSentiment.value.toLowerCase()
    const matchP  = !filterPlatform.value  || p.platform === filterPlatform.value
    const isNews  = !['X', 'Facebook', 'YouTube'].includes(p.platform)
    const matchT  = activeTab.value === 'all'
                 || (activeTab.value === 'posts' && !isNews)
                 || (activeTab.value === 'news'  && isNews)
    return matchQ && matchS && matchP && matchT
  })
})

const tabs = computed(() => {
  const q = lastQuery.value.trim().toLowerCase()
  const all   = allPosts.value.filter(p => {
    const text   = (p.content || '').toLowerCase()
    const author = (p.author  || '').toLowerCase()
    return !q || text.includes(q) || author.includes(q)
  })
  const posts = all.filter(p => ['X','Facebook','YouTube'].includes(p.platform))
  const news  = all.filter(p => !['X','Facebook','YouTube'].includes(p.platform))
  return [
    { id: 'all',   label: 'All',          count: all.length   },
    { id: 'posts', label: 'Social Posts', count: posts.length },
    { id: 'news',  label: 'News',         count: news.length  },
  ]
})

async function search() {
  const q = query.value.trim()
  if (!q) return

  loading.value  = true
  searched.value = true
  lastQuery.value = q
  activeTab.value = 'all'
  allPosts.value  = []

  // Save recent
  recentSearches.value = [q, ...recentSearches.value.filter(s => s !== q)].slice(0, 5)
  localStorage.setItem('sr_recent_searches', JSON.stringify(recentSearches.value))

  try {
    // Use the existing Smart Radar posts endpoint — fetch large batch then filter
    const params = { limit: 1000, skip: 0 }
    if (filterSentiment.value) params.sentiment_label = filterSentiment.value
    if (filterPlatform.value)  params.platform = filterPlatform.value

    const res = await axios.get('/api/v1/posts', { params })
    allPosts.value = Array.isArray(res.data) ? res.data : []
  } catch (e) {
    allPosts.value = []
  } finally {
    loading.value = false
  }
}

// ── Helpers ──────────────────────────────────────────────────────
function highlight(text) {
  if (!text || !lastQuery.value.trim()) return text
  const escaped = lastQuery.value.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return String(text).replace(
    new RegExp(`(${escaped})`, 'gi'),
    '<mark class="bg-yellow-100 text-yellow-900 rounded px-0.5">$1</mark>'
  )
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

function fmtNum(n) {
  if (!n) return 0
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000)     return (n / 1_000).toFixed(1) + 'K'
  return n
}

const platformIcons = { X: '𝕏', Twitter: '𝕏', Facebook: 'f', YouTube: '▶', Instagram: '📷', WhatsApp: '💬' }
const platformBgs   = {
  X: 'bg-black text-white', Twitter: 'bg-black text-white',
  Facebook: 'bg-blue-600 text-white', YouTube: 'bg-red-100 text-red-600',
  Instagram: 'bg-pink-100 text-pink-600'
}
const platformIcon = p => platformIcons[p] || '📣'
const platformBg   = p => platformBgs[p]   || 'bg-gray-100 text-gray-500'

function sentimentClass(s) {
  return {
    positive: 'bg-green-100 text-green-700',
    negative: 'bg-red-100 text-red-700',
    neutral:  'bg-gray-100 text-gray-600',
  }[(s || '').toLowerCase()] || 'bg-gray-100 text-gray-600'
}

// map cluster info from matched_clusters array
const getClusterName = p => p.cluster_name || p.matched_clusters?.[0]?.cluster_name || ''
</script>
