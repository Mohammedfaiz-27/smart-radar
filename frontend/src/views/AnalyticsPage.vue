<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-gray-900">Analytics</h2>
        <p class="text-sm text-gray-600 mt-1">Track your publishing performance across all platforms</p>
      </div>
      <select v-model="period" @change="load" class="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500">
        <option value="7d">Last 7 days</option>
        <option value="30d">Last 30 days</option>
        <option value="90d">Last 90 days</option>
      </select>
    </div>

    <!-- Overview Stats (matches omnipush AnalyticsView exactly) -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      <div class="bg-white rounded-lg shadow border border-gray-200 p-6">
        <div class="flex items-center">
          <div class="p-2 bg-blue-100 rounded-lg">
            <svg class="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
            </svg>
          </div>
          <div class="ml-4">
            <h3 class="text-2xl font-bold text-gray-900">{{ fmtNum(totalImpressions) }}</h3>
            <p class="text-sm text-gray-600">Total Impressions</p>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-lg shadow border border-gray-200 p-6">
        <div class="flex items-center">
          <div class="p-2 bg-green-100 rounded-lg">
            <svg class="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
            </svg>
          </div>
          <div class="ml-4">
            <h3 class="text-2xl font-bold text-gray-900">{{ fmtNum(totalEngagements) }}</h3>
            <p class="text-sm text-gray-600">Total Engagements</p>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-lg shadow border border-gray-200 p-6">
        <div class="flex items-center">
          <div class="p-2 bg-purple-100 rounded-lg">
            <svg class="w-6 h-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5"/>
            </svg>
          </div>
          <div class="ml-4">
            <h3 class="text-2xl font-bold text-gray-900">{{ fmtNum(totalClicks) }}</h3>
            <p class="text-sm text-gray-600">Total Clicks</p>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-lg shadow border border-gray-200 p-6">
        <div class="flex items-center">
          <div class="p-2 bg-yellow-100 rounded-lg">
            <svg class="w-6 h-6 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
            </svg>
          </div>
          <div class="ml-4">
            <h3 class="text-2xl font-bold text-gray-900">{{ engagementRate }}%</h3>
            <p class="text-sm text-gray-600">Engagement Rate</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Platform Performance (matches omnipush AnalyticsView) -->
    <div class="bg-white rounded-lg shadow border border-gray-200">
      <div class="px-6 py-4 border-b border-gray-200">
        <h3 class="text-base font-semibold text-gray-900">Platform Performance</h3>
      </div>
      <div class="p-6">
        <div v-if="loading" class="space-y-3">
          <div v-for="i in 3" :key="i" class="h-20 bg-gray-50 rounded-lg animate-pulse"></div>
        </div>
        <div v-else-if="platformStats.length === 0" class="text-center py-8">
          <svg class="mx-auto h-12 w-12 text-gray-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
          </svg>
          <h3 class="text-sm font-medium text-gray-900">No analytics data yet</h3>
          <p class="text-sm text-gray-500 mt-1">Publish some posts to see performance analytics here.</p>
        </div>
        <div v-else class="space-y-4">
          <div
            v-for="stat in platformStats"
            :key="stat.platform"
            class="border border-gray-200 rounded-lg p-4"
          >
            <div class="flex items-center justify-between mb-3">
              <h4 class="text-sm font-semibold text-gray-900 flex items-center space-x-2">
                <span>{{ getPlatformIcon(stat.platform) }}</span>
                <span class="capitalize">{{ stat.platform }}</span>
              </h4>
              <span class="text-xs text-gray-500">{{ stat.posts }} posts</span>
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
              <div>
                <p class="text-gray-500 text-xs">Impressions</p>
                <p class="font-semibold text-gray-900">{{ fmtNum(stat.impressions ?? stat.total_reach ?? 0) }}</p>
              </div>
              <div>
                <p class="text-gray-500 text-xs">Engagements</p>
                <p class="font-semibold text-gray-900">{{ fmtNum(stat.engagements ?? stat.total_engagement ?? 0) }}</p>
              </div>
              <div>
                <p class="text-gray-500 text-xs">Clicks</p>
                <p class="font-semibold text-gray-900">{{ fmtNum(stat.clicks ?? 0) }}</p>
              </div>
              <div>
                <p class="text-gray-500 text-xs">Eng. Rate</p>
                <p class="font-semibold text-gray-900">
                  {{ stat.engagement_rate != null ? (stat.engagement_rate * 100).toFixed(1) + '%' : (stat.engagementRate ?? '—') }}
                </p>
              </div>
            </div>
            <!-- progress bar -->
            <div class="mt-3 w-full bg-gray-100 rounded-full h-1.5">
              <div class="bg-blue-500 h-1.5 rounded-full" :style="{ width: stat.percentage + '%' }"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- AI Insights -->
    <div class="bg-white rounded-lg shadow border border-gray-200">
      <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <h3 class="text-base font-semibold text-gray-900">AI Insights</h3>
        <button @click="loadInsights" class="text-xs text-blue-600 hover:underline">Refresh</button>
      </div>
      <div class="p-6">
        <div v-if="loadingInsights" class="space-y-3">
          <div v-for="i in 3" :key="i" class="h-12 bg-gray-50 rounded-xl animate-pulse"></div>
        </div>
        <div v-else-if="insights.length === 0" class="text-center py-6 text-gray-400 text-sm">
          No insights available yet — publish some posts to get AI-powered recommendations.
        </div>
        <ul v-else class="space-y-3">
          <li
            v-for="(insight, i) in insights"
            :key="i"
            class="flex items-start space-x-3 p-3 bg-blue-50 rounded-xl"
          >
            <span class="text-blue-500 mt-0.5">💡</span>
            <p class="text-sm text-blue-800">{{ insight.recommendation || insight.text || insight }}</p>
          </li>
        </ul>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { smartPostApi } from '@/services/smartpost'

const period = ref('30d')
const loading = ref(false)
const loadingInsights = ref(false)
const dashboardData = ref(null)
const insights = ref([])

const platformIcons = { twitter: '🐦', facebook: '📘', linkedin: '💼', instagram: '📷', whatsapp: '💬' }
const getPlatformIcon = (id) => platformIcons[id?.toLowerCase()] || '📣'

function fmtNum(n) {
  if (n == null) return '0'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

const overview = computed(() => dashboardData.value?.overview ?? dashboardData.value ?? null)

const totalImpressions = computed(() => overview.value?.total_reach ?? 0)
const totalEngagements = computed(() => overview.value?.total_engagement ?? 0)
const totalClicks      = computed(() => overview.value?.total_clicks ?? 0)
const engagementRate   = computed(() => {
  const r = overview.value?.avg_engagement_rate
  return r != null ? (r * 100).toFixed(1) : '0.0'
})

const platformStats = computed(() => {
  const raw = dashboardData.value?.platforms ?? dashboardData.value?.by_platform ?? []
  if (!raw.length) return []
  const max = Math.max(...raw.map(p => p.posts || 0)) || 1
  return raw.map(p => ({ ...p, percentage: Math.round(((p.posts || 0) / max) * 100) }))
})

async function load() {
  loading.value = true
  try {
    const res = await smartPostApi.getAnalyticsDashboard({ period: period.value })
    dashboardData.value = res.data
  } catch {
    dashboardData.value = null
  } finally {
    loading.value = false
  }
}

async function loadInsights() {
  loadingInsights.value = true
  try {
    const res = await smartPostApi.getInsights()
    insights.value = res.data?.insights ?? res.data ?? []
  } catch {
    insights.value = []
  } finally {
    loadingInsights.value = false
  }
}

onMounted(() => {
  load()
  loadInsights()
})
</script>
