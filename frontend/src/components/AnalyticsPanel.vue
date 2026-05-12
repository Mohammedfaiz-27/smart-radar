<template>
  <div class="space-y-6">
    <!-- Summary cards -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div v-for="metric in summaryMetrics" :key="metric.label" class="bg-white rounded-xl border border-gray-200 p-4">
        <p class="text-xs text-gray-500 font-medium uppercase mb-1">{{ metric.label }}</p>
        <p class="text-2xl font-bold text-gray-900">{{ metric.value }}</p>
        <p v-if="metric.change" class="text-xs mt-1" :class="metric.positive ? 'text-green-600' : 'text-red-600'">
          {{ metric.change }}
        </p>
      </div>
    </div>

    <!-- Insights -->
    <div class="bg-white rounded-2xl border border-gray-200 p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-base font-semibold text-gray-900">AI Insights</h3>
        <button @click="loadInsights" class="text-xs text-blue-600 hover:underline">Refresh</button>
      </div>

      <div v-if="loadingInsights" class="space-y-3">
        <div v-for="i in 3" :key="i" class="h-12 bg-gray-50 rounded-xl animate-pulse"></div>
      </div>

      <div v-else-if="insights.length === 0" class="py-8 text-center text-gray-400 text-sm">
        No insights available yet
      </div>

      <ul v-else class="space-y-3">
        <li
          v-for="(insight, i) in insights"
          :key="i"
          class="flex items-start space-x-3 p-3 bg-blue-50 rounded-xl"
        >
          <span class="text-blue-600 mt-0.5">💡</span>
          <p class="text-sm text-blue-800">{{ insight.text || insight }}</p>
        </li>
      </ul>
    </div>

    <!-- Platform breakdown -->
    <div class="bg-white rounded-2xl border border-gray-200 p-6">
      <h3 class="text-base font-semibold text-gray-900 mb-4">Platform Performance</h3>

      <div v-if="loadingDashboard" class="space-y-2">
        <div v-for="i in 4" :key="i" class="h-10 bg-gray-50 rounded-lg animate-pulse"></div>
      </div>

      <div v-else-if="platformStats.length === 0" class="py-8 text-center text-gray-400 text-sm">
        No data yet — start publishing to see analytics
      </div>

      <div v-else class="space-y-3">
        <div v-for="stat in platformStats" :key="stat.platform" class="flex items-center space-x-3">
          <span class="text-xl w-8">{{ getPlatformIcon(stat.platform) }}</span>
          <div class="flex-1">
            <div class="flex items-center justify-between mb-1">
              <span class="text-sm font-medium text-gray-700">{{ stat.platform }}</span>
              <span class="text-xs text-gray-500">{{ stat.posts }} posts</span>
            </div>
            <div class="w-full bg-gray-100 rounded-full h-2">
              <div
                class="bg-blue-500 h-2 rounded-full transition-all"
                :style="{ width: `${stat.percentage}%` }"
              ></div>
            </div>
          </div>
          <span class="text-sm font-semibold text-gray-900 w-16 text-right">
            {{ stat.engagement_rate ? (stat.engagement_rate * 100).toFixed(1) + '%' : '—' }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { smartPostApi } from '@/services/smartpost'

const loadingDashboard = ref(false)
const loadingInsights = ref(false)
const dashboardData = ref(null)
const insights = ref([])

const platformIcons = { twitter: '🐦', facebook: '📘', linkedin: '💼', instagram: '📷', whatsapp: '💬' }
const getPlatformIcon = (id) => platformIcons[id?.toLowerCase()] || '📣'

const summaryMetrics = computed(() => {
  const d = dashboardData.value
  if (!d) return [
    { label: 'Total Posts', value: '—' },
    { label: 'Total Reach', value: '—' },
    { label: 'Avg Engagement', value: '—' },
    { label: 'Scheduled', value: '—' },
  ]
  return [
    { label: 'Total Posts', value: d.total_posts ?? '—', change: d.posts_change, positive: (d.posts_change || '').startsWith('+') },
    { label: 'Total Reach', value: formatNumber(d.total_reach) },
    { label: 'Avg Engagement', value: d.avg_engagement_rate ? (d.avg_engagement_rate * 100).toFixed(1) + '%' : '—' },
    { label: 'Scheduled', value: d.scheduled_posts ?? '—' },
  ]
})

const platformStats = computed(() => {
  const d = dashboardData.value
  if (!d?.by_platform) return []
  const total = Object.values(d.by_platform).reduce((s, v) => s + (v.posts || 0), 0)
  return Object.entries(d.by_platform).map(([platform, v]) => ({
    platform,
    posts: v.posts || 0,
    engagement_rate: v.engagement_rate,
    percentage: total > 0 ? Math.round(((v.posts || 0) / total) * 100) : 0,
  })).sort((a, b) => b.posts - a.posts)
})

function formatNumber(n) {
  if (!n) return '—'
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return String(n)
}

async function loadDashboard() {
  loadingDashboard.value = true
  try {
    const res = await smartPostApi.getAnalyticsDashboard()
    dashboardData.value = res.data
  } catch {
    dashboardData.value = null
  } finally {
    loadingDashboard.value = false
  }
}

async function loadInsights() {
  loadingInsights.value = true
  try {
    const res = await smartPostApi.getInsights()
    insights.value = res.data?.insights || res.data || []
  } catch {
    insights.value = []
  } finally {
    loadingInsights.value = false
  }
}

onMounted(() => {
  loadDashboard()
  loadInsights()
})
</script>
