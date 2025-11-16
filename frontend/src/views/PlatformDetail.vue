<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center h-16">
          <div class="flex items-center space-x-4">
            <button @click="$router.go(-1)" class="text-gray-600 hover:text-gray-900">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
              </svg>
            </button>
            <router-link to="/" class="text-2xl font-bold text-gray-900">SMART RADAR</router-link>
            <span class="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
              {{ formatPlatformName(platform) }} Analytics
            </span>
          </div>
          
          <nav class="flex space-x-4">
            <router-link 
              to="/" 
              class="px-3 py-2 rounded-md text-sm font-medium text-gray-500 hover:text-gray-900"
            >
              Dashboard
            </router-link>
            <router-link 
              to="/clusters" 
              class="px-3 py-2 rounded-md text-sm font-medium text-gray-500 hover:text-gray-900"
            >
              Clusters
            </router-link>
            <router-link 
              to="/narratives" 
              class="px-3 py-2 rounded-md text-sm font-medium text-gray-500 hover:text-gray-900"
            >
              Narratives
            </router-link>
          </nav>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <!-- Loading State -->
      <div v-if="loading" class="text-center py-8">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
        <p class="mt-2 text-sm text-gray-500">Loading platform analytics...</p>
      </div>

      <!-- Content -->
      <div v-else>
        <!-- Platform Header -->
        <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 mb-6">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center space-x-4">
              <div class="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center">
                <div v-html="getPlatformIcon(platform)"></div>
              </div>
              <div>
                <h1 class="text-2xl font-bold text-gray-900">{{ formatPlatformName(platform) }}</h1>
                <p class="text-sm text-gray-500">{{ type === 'own' ? 'Own Organization' : 'Competitor' }} Content Analysis</p>
              </div>
            </div>
            <div class="text-right">
              <div class="text-2xl font-bold text-gray-900">{{ platformData.total_posts || 0 }}</div>
              <div class="text-sm text-gray-500">Total Posts</div>
            </div>
          </div>

          <!-- Platform Statistics -->
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div class="bg-gray-50 rounded-lg p-4">
              <div class="text-2xl font-bold text-green-600">{{ getPlatformPercentage(platformData, 'positive') }}%</div>
              <div class="text-sm text-gray-500">Positive Sentiment</div>
            </div>
            <div class="bg-gray-50 rounded-lg p-4">
              <div class="text-2xl font-bold text-blue-600">{{ getPlatformPercentage(platformData, 'neutral') }}%</div>
              <div class="text-sm text-gray-500">Neutral Sentiment</div>
            </div>
            <div class="bg-gray-50 rounded-lg p-4">
              <div class="text-2xl font-bold text-red-600">{{ getPlatformPercentage(platformData, 'negative') }}%</div>
              <div class="text-sm text-gray-500">Negative Sentiment</div>
            </div>
            <div class="bg-gray-50 rounded-lg p-4">
              <div class="text-2xl font-bold text-gray-900">{{ formatNumber(totalEngagement) }}</div>
              <div class="text-sm text-gray-500">Total Engagement</div>
            </div>
          </div>
        </div>

        <!-- Sentiment Visualization -->
        <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">Sentiment Distribution</h2>
          
          <!-- Sentiment Bars -->
          <div class="space-y-4">
            <!-- Positive -->
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-green-600">Positive</span>
              <span class="text-sm font-bold text-gray-900">{{ getPlatformPercentage(platformData, 'positive') }}%</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-4">
              <div 
                class="bg-green-500 h-4 rounded-full transition-all duration-500"
                :style="{ width: getPlatformPercentage(platformData, 'positive') + '%' }"
              ></div>
            </div>

            <!-- Neutral -->
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-gray-500">Neutral</span>
              <span class="text-sm font-bold text-gray-900">{{ getPlatformPercentage(platformData, 'neutral') }}%</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-4">
              <div 
                class="bg-blue-500 h-4 rounded-full transition-all duration-500"
                :style="{ width: getPlatformPercentage(platformData, 'neutral') + '%' }"
              ></div>
            </div>

            <!-- Negative -->
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-red-600">Negative</span>
              <span class="text-sm font-bold text-gray-900">{{ getPlatformPercentage(platformData, 'negative') }}%</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-4">
              <div 
                class="bg-red-500 h-4 rounded-full transition-all duration-500"
                :style="{ width: getPlatformPercentage(platformData, 'negative') + '%' }"
              ></div>
            </div>
          </div>

          <!-- Combined Bar -->
          <div class="mt-6">
            <div class="flex h-6 rounded-full overflow-hidden bg-gray-200">
              <div 
                class="bg-green-500 transition-all duration-500"
                :style="{ width: getPlatformPercentage(platformData, 'positive') + '%' }"
              ></div>
              <div 
                class="bg-blue-500 transition-all duration-500"
                :style="{ width: getPlatformPercentage(platformData, 'neutral') + '%' }"
              ></div>
              <div 
                class="bg-red-500 transition-all duration-500"
                :style="{ width: getPlatformPercentage(platformData, 'negative') + '%' }"
              ></div>
            </div>
          </div>
        </div>

        <!-- Recent Posts -->
        <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-semibold text-gray-900">Recent Posts</h2>
            <div class="flex items-center space-x-2">
              <select v-model="sentimentFilter" class="text-sm border border-gray-300 rounded-md px-3 py-1">
                <option value="">All Sentiments</option>
                <option value="positive">Positive Only</option>
                <option value="neutral">Neutral Only</option>
                <option value="negative">Negative Only</option>
              </select>
            </div>
          </div>
          
          <div v-if="filteredPosts.length === 0" class="text-center py-8">
            <p class="text-gray-500">No posts found matching your criteria</p>
          </div>
          
          <div v-else class="space-y-4">
            <div
              v-for="post in filteredPosts"
              :key="post.id"
              class="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
            >
              <div class="flex items-start justify-between mb-3">
                <div class="flex items-center space-x-3">
                  <div class="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center">
                    <span class="text-sm font-medium text-gray-600">
                      {{ (post.author || 'U')[0].toUpperCase() }}
                    </span>
                  </div>
                  <div>
                    <div class="text-sm font-medium text-gray-900">@{{ post.author || 'unknown' }}</div>
                    <div class="text-xs text-gray-500">{{ formatDate(post.posted_at) }}</div>
                  </div>
                </div>
                <span 
                  class="px-2 py-1 rounded-full text-xs font-medium"
                  :class="getSentimentClass(post.sentiment)"
                >
                  {{ (post.sentiment || 'neutral').toUpperCase() }}
                </span>
              </div>
              
              <p class="text-sm text-gray-700 mb-3 leading-relaxed">{{ post.content }}</p>
              
              <div class="flex items-center justify-between text-xs text-gray-500">
                <div class="flex items-center space-x-4">
                  <div class="flex items-center space-x-1">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/>
                      <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd"/>
                    </svg>
                    <span>{{ formatNumber(post.engagement_metrics?.views || 0) }}</span>
                  </div>
                  <div class="flex items-center space-x-1">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clip-rule="evenodd"/>
                    </svg>
                    <span>{{ formatNumber(post.engagement_metrics?.likes || 0) }}</span>
                  </div>
                  <div class="flex items-center space-x-1">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clip-rule="evenodd"/>
                    </svg>
                    <span>{{ formatNumber(post.engagement_metrics?.comments || 0) }}</span>
                  </div>
                </div>
                <div class="flex items-center space-x-2">
                  <button class="text-blue-600 hover:text-blue-800 font-medium">
                    Analyze
                  </button>
                  <button class="text-green-600 hover:text-green-800 font-medium">
                    {{ getButtonText(post) }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'

const props = defineProps({
  platform: {
    type: String,
    required: true
  },
  type: {
    type: String,
    required: true
  }
})

const loading = ref(true)
const platformData = ref({
  total_posts: 0,
  sentiments: {
    positive: 0,
    neutral: 0,
    negative: 0
  }
})
const recentPosts = ref([])
const sentimentFilter = ref('')

const totalEngagement = computed(() => {
  return recentPosts.value.reduce((sum, post) => {
    const metrics = post.engagement_metrics || {}
    return sum + (metrics.views || 0) + (metrics.likes || 0) + (metrics.comments || 0)
  }, 0)
})

const filteredPosts = computed(() => {
  if (!sentimentFilter.value) {
    return recentPosts.value
  }
  return recentPosts.value.filter(post => 
    (post.sentiment || 'neutral').toLowerCase() === sentimentFilter.value.toLowerCase()
  )
})

const fetchPlatformData = async () => {
  loading.value = true
  try {
    // Fetch sentiment data for the specific platform
    const endpoint = props.type === 'own' 
      ? '/api/v1/sentiment/organization'
      : '/api/v1/sentiment/competitors'
    
    const response = await fetch(`http://localhost:8000${endpoint}`)
    if (response.ok) {
      const data = await response.json()
      const breakdown = data.platform_breakdown || {}
      platformData.value = breakdown[props.platform] || platformData.value
    }

    // Fetch recent posts for this platform
    const postsResponse = await fetch(`http://localhost:8000/api/v1/posts?cluster_type=${props.type}&platform=${props.platform}&limit=20`)
    if (postsResponse.ok) {
      const postsData = await postsResponse.json()
      recentPosts.value = postsData.posts || []
    }
  } catch (error) {
    console.error('Error fetching platform data:', error)
  } finally {
    loading.value = false
  }
}

const getPlatformIcon = (platform) => {
  const platformName = platform.toLowerCase()
  
  if (platformName === 'x' || platformName === 'twitter') {
    return `<svg viewBox="0 0 24 24" class="h-6 w-6 text-gray-600" fill="currentColor">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
    </svg>`
  }
  
  if (platformName === 'facebook') {
    return `<svg viewBox="0 0 24 24" class="h-6 w-6 text-gray-600" fill="currentColor">
      <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
    </svg>`
  }
  
  if (platformName === 'youtube') {
    return `<svg viewBox="0 0 24 24" class="h-6 w-6 text-gray-600" fill="currentColor">
      <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
    </svg>`
  }
  
  return `<svg class="h-6 w-6 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/>
  </svg>`
}

const formatPlatformName = (platform) => {
  const nameMap = {
    'x': 'X (Twitter)',
    'twitter': 'X (Twitter)',
    'facebook': 'Facebook',
    'youtube': 'YouTube',
    'instagram': 'Instagram'
  }
  return nameMap[platform.toLowerCase()] || platform.charAt(0).toUpperCase() + platform.slice(1)
}

const getPlatformPercentage = (platformData, sentimentType) => {
  const sentiments = platformData.sentiments || {}
  const total = platformData.total_posts || 1
  const count = sentiments[sentimentType] || 0
  return Math.round((count / total) * 100)
}

const formatNumber = (num) => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num?.toString() || '0'
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  const now = new Date()
  const diff = now - date
  
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  return `${days}d ago`
}

const getSentimentClass = (sentiment) => {
  const classes = {
    positive: 'bg-green-100 text-green-800',
    neutral: 'bg-blue-100 text-blue-800',
    negative: 'bg-red-100 text-red-800'
  }
  return classes[sentiment?.toLowerCase()] || classes.neutral
}

const getButtonText = (post) => {
  const sentiment = post.sentiment?.toLowerCase()
  const isCompetitor = props.type === 'competitor' || post.cluster_type === 'competitor'
  const isNegative = sentiment === 'negative'
  
  // Show "Opportunities" for competitor negative posts
  if (isCompetitor && isNegative) {
    return 'Opportunities'
  }
  
  return 'Respond'
}

onMounted(() => {
  fetchPlatformData()
})
</script>