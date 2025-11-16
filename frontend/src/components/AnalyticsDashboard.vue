<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200">
    <div class="px-6 py-4 border-b border-gray-200">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-lg font-semibold text-gray-900">Analytics Overview</h3>
          <p class="text-sm text-gray-500">Real-time intelligence and data insights</p>
        </div>
        
        <div class="flex items-center space-x-2">
          <select 
            v-model="selectedTimeRange"
            @change="refreshAnalytics"
            class="text-sm border border-gray-300 rounded-md px-3 py-1"
          >
            <option value="1h">Last Hour</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
          </select>
          
          <button 
            @click="refreshAnalytics"
            class="btn-secondary text-sm"
            :disabled="loading"
          >
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>
      </div>
    </div>

    <!-- Key Metrics -->
    <div class="px-6 py-4">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div class="text-center p-4 bg-blue-50 rounded-lg">
          <div class="text-2xl font-bold text-blue-600">{{ analytics.totalPosts || 0 }}</div>
          <div class="text-sm text-blue-600">Total Posts</div>
          <div class="text-xs text-gray-500 mt-1">
            <span :class="getChangeClass(analytics.postsChange)">
              {{ formatChange(analytics.postsChange) }}%
            </span>
            vs previous period
          </div>
        </div>
        
        <div class="text-center p-4 bg-red-50 rounded-lg">
          <div class="text-2xl font-bold text-red-600">{{ analytics.threatPosts || 0 }}</div>
          <div class="text-sm text-red-600">Threats Detected</div>
          <div class="text-xs text-gray-500 mt-1">
            {{ analytics.threatPercentage || 0 }}% threat rate
          </div>
        </div>
        
        <div class="text-center p-4 bg-green-50 rounded-lg">
          <div class="text-2xl font-bold text-green-600">{{ analytics.avgSentiment || 0 }}</div>
          <div class="text-sm text-green-600">Avg Sentiment</div>
          <div class="text-xs text-gray-500 mt-1">
            Scale: -1 to +1
          </div>
        </div>
        
        <div class="text-center p-4 bg-purple-50 rounded-lg">
          <div class="text-2xl font-bold text-purple-600">{{ analytics.responsesGenerated || 0 }}</div>
          <div class="text-sm text-purple-600">Responses Generated</div>
          <div class="text-xs text-gray-500 mt-1">
            {{ analytics.responseRate || 0 }}% response rate
          </div>
        </div>
      </div>

      <!-- Platform Breakdown -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div class="bg-gray-50 rounded-lg p-4">
          <h4 class="text-sm font-medium text-gray-900 mb-3">Platform Distribution</h4>
          <div class="space-y-3">
            <div v-for="(platform, name) in analytics.platformBreakdown" :key="name" class="flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <div class="w-3 h-3 rounded-full" :class="getPlatformColor(name)"></div>
                <span class="text-sm text-gray-700 capitalize">{{ name }}</span>
              </div>
              <div class="flex items-center space-x-3">
                <span class="text-sm font-medium text-gray-900">{{ platform.total || 0 }}</span>
                <div class="w-20 bg-gray-200 rounded-full h-2">
                  <div 
                    class="h-2 rounded-full" 
                    :class="getPlatformColor(name)" 
                    :style="{ width: `${(platform.total / analytics.totalPosts) * 100}%` }"
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-gray-50 rounded-lg p-4">
          <h4 class="text-sm font-medium text-gray-900 mb-3">Threat Level Distribution</h4>
          <div class="space-y-3">
            <div v-for="(count, level) in analytics.threatLevels" :key="level" class="flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <div class="w-3 h-3 rounded-full" :class="getThreatLevelColor(level)"></div>
                <span class="text-sm text-gray-700 capitalize">{{ level }}</span>
              </div>
              <span class="text-sm font-medium text-gray-900">{{ count || 0 }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Sentiment Trend -->
      <div class="bg-gray-50 rounded-lg p-4 mb-6">
        <h4 class="text-sm font-medium text-gray-900 mb-3">Sentiment Trend</h4>
        <div class="flex items-center justify-center h-32 text-gray-500">
          <!-- Placeholder for chart - could integrate Chart.js or similar -->
          <div class="text-center">
            <svg class="w-12 h-12 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <p class="text-xs">Sentiment trend visualization</p>
            <p class="text-xs">Integration ready for Chart.js</p>
          </div>
        </div>
      </div>

      <!-- Recent Activity -->
      <div class="bg-gray-50 rounded-lg p-4">
        <h4 class="text-sm font-medium text-gray-900 mb-3">Recent Activity</h4>
        <div class="space-y-2 max-h-40 overflow-y-auto">
          <div v-for="activity in recentActivity" :key="activity.id" class="flex items-center space-x-3 text-sm">
            <div class="flex-shrink-0">
              <div class="w-2 h-2 rounded-full" :class="getActivityColor(activity.type)"></div>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-gray-900 truncate">{{ activity.message }}</p>
              <p class="text-xs text-gray-500">{{ formatTime(activity.timestamp) }}</p>
            </div>
          </div>
          
          <div v-if="recentActivity.length === 0" class="text-center py-4">
            <p class="text-sm text-gray-500">No recent activity</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { usePostsStore } from '@/stores/posts'
import { useTasksStore } from '@/stores/tasks'
import { narrativesEnhancedApi } from '@/services/api'

const postsStore = usePostsStore()
const tasksStore = useTasksStore()

const loading = ref(false)
const selectedTimeRange = ref('24h')

const analytics = reactive({
  totalPosts: 0,
  threatPosts: 0,
  avgSentiment: 0,
  responsesGenerated: 0,
  threatPercentage: 0,
  responseRate: 0,
  postsChange: 0,
  platformBreakdown: {},
  threatLevels: {
    low: 0,
    medium: 0,
    high: 0,
    critical: 0
  }
})

const recentActivity = ref([])

// Auto-refresh interval
let refreshInterval = null

const refreshAnalytics = async () => {
  loading.value = true
  
  try {
    // Fetch posts data
    await postsStore.fetchPosts()
    
    // Calculate analytics
    calculateAnalytics()
    
    // Fetch narrative analytics
    await fetchNarrativeAnalytics()
    
    // Update recent activity
    updateRecentActivity()
    
  } catch (error) {
    console.error('Failed to refresh analytics:', error)
  } finally {
    loading.value = false
  }
}

const calculateAnalytics = () => {
  const posts = postsStore.posts
  
  analytics.totalPosts = posts.length
  analytics.threatPosts = posts.filter(post => post.intelligence?.is_threat).length
  analytics.threatPercentage = analytics.totalPosts > 0 
    ? Math.round((analytics.threatPosts / analytics.totalPosts) * 100) 
    : 0
  
  // Calculate average sentiment
  const sentimentScores = posts
    .map(post => post.intelligence?.sentiment_score || 0)
    .filter(score => score !== 0)
  
  analytics.avgSentiment = sentimentScores.length > 0
    ? (sentimentScores.reduce((sum, score) => sum + score, 0) / sentimentScores.length).toFixed(2)
    : 0
  
  // Platform breakdown
  const platformCounts = {}
  posts.forEach(post => {
    const platform = post.platform || 'unknown'
    if (!platformCounts[platform]) {
      platformCounts[platform] = { total: 0, threats: 0 }
    }
    platformCounts[platform].total++
    if (post.intelligence?.is_threat) {
      platformCounts[platform].threats++
    }
  })
  analytics.platformBreakdown = platformCounts
  
  // Threat level distribution
  const threatLevels = { low: 0, medium: 0, high: 0, critical: 0 }
  posts.forEach(post => {
    if (post.intelligence?.is_threat) {
      const level = post.intelligence.threat_level || 'low'
      threatLevels[level] = (threatLevels[level] || 0) + 1
    }
  })
  analytics.threatLevels = threatLevels
}

const fetchNarrativeAnalytics = async () => {
  try {
    const overview = await narrativesEnhancedApi.getOverview()
    analytics.responsesGenerated = overview.data.total_responses_generated || 0
    
    if (analytics.totalPosts > 0) {
      analytics.responseRate = Math.round((analytics.responsesGenerated / analytics.totalPosts) * 100)
    }
  } catch (error) {
    console.error('Failed to fetch narrative analytics:', error)
  }
}

const updateRecentActivity = () => {
  const activities = []
  
  // Add recent tasks from task store
  tasksStore.recentTasks.forEach(task => {
    activities.push({
      id: `task-${task.id}`,
      type: 'task',
      message: task.message,
      timestamp: task.timestamp
    })
  })
  
  // Add recent threat posts
  const threats = postsStore.threatPosts.slice(0, 5)
  threats.forEach(post => {
    activities.push({
      id: `threat-${post.id}`,
      type: 'threat',
      message: `Threat detected: ${post.intelligence.threat_level} on ${post.platform}`,
      timestamp: post.collected_at
    })
  })
  
  // Sort by timestamp and take the most recent
  recentActivity.value = activities
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    .slice(0, 10)
}

const getPlatformColor = (platform) => {
  const colors = {
    x: 'bg-blue-500',
    facebook: 'bg-blue-600',
    youtube: 'bg-red-500',
    instagram: 'bg-pink-500',
    unknown: 'bg-gray-500'
  }
  return colors[platform] || colors.unknown
}

const getThreatLevelColor = (level) => {
  const colors = {
    low: 'bg-yellow-500',
    medium: 'bg-orange-500',
    high: 'bg-red-500',
    critical: 'bg-red-700'
  }
  return colors[level] || colors.low
}

const getActivityColor = (type) => {
  const colors = {
    task: 'bg-blue-500',
    threat: 'bg-red-500',
    collection: 'bg-green-500',
    intelligence: 'bg-purple-500'
  }
  return colors[type] || 'bg-gray-500'
}

const getChangeClass = (change) => {
  if (change > 0) return 'text-green-600'
  if (change < 0) return 'text-red-600'
  return 'text-gray-600'
}

const formatChange = (change) => {
  if (change === undefined || change === null) return '0'
  return change > 0 ? `+${change}` : change.toString()
}

const formatTime = (timestamp) => {
  return new Date(timestamp).toLocaleString()
}

onMounted(async () => {
  // Initial load
  await refreshAnalytics()
  
  // Set up auto-refresh every 60 seconds
  refreshInterval = setInterval(refreshAnalytics, 60000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>