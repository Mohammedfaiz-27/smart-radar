<template>
  <div>
    <!-- Page Header with Back Button -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 bg-white border-b">
      <div class="flex items-center space-x-4">
        <button @click="$router.go(-1)" class="text-gray-600 hover:text-gray-900">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
          </svg>
        </button>
        <h1 class="text-2xl font-bold text-gray-900">{{ name }} Cluster Details</h1>
      </div>
    </div>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <!-- Loading State -->
      <div v-if="loading" class="text-center py-8">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
        <p class="mt-2 text-sm text-gray-500">Loading cluster details...</p>
      </div>

      <!-- Content -->
      <div v-else>
        <!-- Cluster Header -->
        <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 mb-6">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center space-x-4">
              <div class="w-12 h-12 rounded-full flex items-center justify-center" 
                   :class="clusterType === 'own' ? 'bg-blue-100' : 'bg-orange-100'">
                <div class="w-6 h-6 rounded-full" 
                     :class="clusterType === 'own' ? 'bg-blue-500' : 'bg-orange-500'"></div>
              </div>
              <div>
                <h1 class="text-2xl font-bold text-gray-900">{{ name }}</h1>
                <p class="text-sm text-gray-500">{{ clusterType === 'own' ? 'Own Organization' : 'Competitor' }} Cluster</p>
              </div>
            </div>
            <div class="text-right">
              <div class="text-2xl font-bold text-gray-900">{{ sentimentData.total_posts || 0 }}</div>
              <div class="text-sm text-gray-500">Total Posts</div>
            </div>
          </div>

          <!-- Keywords -->
          <div class="mb-4">
            <h3 class="text-sm font-medium text-gray-700 mb-2">Tracked Keywords</h3>
            <div class="flex flex-wrap gap-2">
              <span 
                v-for="keyword in keywords" 
                :key="keyword"
                class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800"
              >
                {{ keyword }}
              </span>
            </div>
          </div>
        </div>

        <!-- Sentiment Analytics -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <!-- Overall Sentiment -->
          <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <h2 class="text-lg font-semibold text-gray-900 mb-4">Overall Sentiment</h2>
            
            <div class="space-y-4">
              <!-- Positive -->
              <div class="flex items-center justify-between">
                <span class="text-sm font-medium text-green-600">Positive</span>
                <span class="text-sm font-bold text-gray-900">{{ sentimentData.positive_percentage || 0 }}%</span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-3">
                <div 
                  class="bg-green-500 h-3 rounded-full transition-all duration-500"
                  :style="{ width: (sentimentData.positive_percentage || 0) + '%' }"
                ></div>
              </div>

              <!-- Neutral -->
              <div class="flex items-center justify-between">
                <span class="text-sm font-medium text-gray-500">Neutral</span>
                <span class="text-sm font-bold text-gray-900">{{ sentimentData.neutral_percentage || 0 }}%</span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-3">
                <div 
                  class="bg-blue-500 h-3 rounded-full transition-all duration-500"
                  :style="{ width: (sentimentData.neutral_percentage || 0) + '%' }"
                ></div>
              </div>

              <!-- Negative -->
              <div class="flex items-center justify-between">
                <span class="text-sm font-medium text-red-600">Negative</span>
                <span class="text-sm font-bold text-gray-900">{{ sentimentData.negative_percentage || 0 }}%</span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-3">
                <div 
                  class="bg-red-500 h-3 rounded-full transition-all duration-500"
                  :style="{ width: (sentimentData.negative_percentage || 0) + '%' }"
                ></div>
              </div>
            </div>
          </div>

          <!-- Platform Breakdown -->
          <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <h2 class="text-lg font-semibold text-gray-900 mb-4">Platform Breakdown</h2>
            
            <div class="space-y-4">
              <div
                v-for="(platformData, platform) in sentimentData.platform_breakdown"
                :key="platform"
                class="border border-gray-200 rounded-lg p-3 cursor-pointer hover:bg-gray-50 transition-colors"
                @click="navigateToPlatform(platform)"
              >
                <div class="flex items-center justify-between mb-2">
                  <div class="flex items-center space-x-2">
                    <div v-html="getPlatformIcon(platform)"></div>
                    <span class="font-medium text-gray-900">{{ formatPlatformName(platform) }}</span>
                  </div>
                  <span class="text-sm text-gray-500">{{ platformData.total_posts || 0 }} posts</span>
                </div>
                
                <div class="flex h-2 rounded-full overflow-hidden bg-gray-200">
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
          </div>
        </div>

        <!-- Recent Posts -->
        <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">Recent Posts</h2>
          
          <div v-if="recentPosts.length === 0" class="text-center py-8">
            <p class="text-gray-500">No recent posts found for this cluster</p>
          </div>
          
          <div v-else class="space-y-4">
            <div
              v-for="post in recentPosts"
              :key="post.id"
              class="border border-gray-200 rounded-lg p-4"
            >
              <div class="flex items-start justify-between mb-2">
                <div class="flex items-center space-x-2">
                  <span class="text-sm font-medium text-gray-900">@{{ post.author || 'unknown' }}</span>
                  <span class="text-sm text-gray-500">{{ formatPlatformName(post.platform) }}</span>
                </div>
                <span class="text-xs text-gray-500">{{ formatDate(post.posted_at) }}</span>
              </div>
              
              <p class="text-sm text-gray-700 mb-2">{{ post.content }}</p>
              
              <div class="flex items-center justify-between text-xs">
                <span 
                  class="px-2 py-1 rounded-full font-medium"
                  :class="getSentimentClass(post.sentiment)"
                >
                  {{ (post.sentiment || 'neutral').toUpperCase() }}
                </span>
                <div class="flex items-center space-x-2 text-gray-500">
                  <span>{{ formatNumber(post.engagement_metrics?.views || 0) }} views</span>
                  <span>{{ formatNumber(post.engagement_metrics?.likes || 0) }} likes</span>
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
import { useRouter } from 'vue-router'

const props = defineProps({
  name: {
    type: String,
    required: true
  }
})

const router = useRouter()
const loading = ref(true)
const sentimentData = ref({
  total_posts: 0,
  positive_percentage: 0,
  neutral_percentage: 0,
  negative_percentage: 0,
  platform_breakdown: {}
})
const recentPosts = ref([])
const keywords = ref(['Political News', 'Public Policy', 'Government Affairs'])

// Determine cluster type based on name
const clusterType = computed(() => {
  return props.name === 'DMK' ? 'own' : 'competitor'
})

const fetchClusterData = async () => {
  loading.value = true
  try {
    // Fetch sentiment data for the specific cluster
    const endpoint = clusterType.value === 'own' 
      ? '/api/v1/sentiment/organization'
      : '/api/v1/sentiment/competitors'
    
    const response = await fetch(`http://localhost:8000${endpoint}`)
    if (response.ok) {
      const data = await response.json()
      sentimentData.value = data.overall_sentiment || sentimentData.value
      sentimentData.value.platform_breakdown = data.platform_breakdown || {}
    }

    // Fetch recent posts for this cluster
    const postsResponse = await fetch(`http://localhost:8000/api/v1/posts?cluster_type=${clusterType.value}&limit=10`)
    if (postsResponse.ok) {
      const postsData = await postsResponse.json()
      recentPosts.value = postsData.posts || []
    }
  } catch (error) {
    console.error('Error fetching cluster data:', error)
  } finally {
    loading.value = false
  }
}

const navigateToPlatform = (platform) => {
  router.push({
    name: 'platform-detail',
    params: {
      platform: platform,
      type: clusterType.value
    }
  })
}

const getPlatformIcon = (platform) => {
  const platformName = platform.toLowerCase()
  
  if (platformName === 'x' || platformName === 'twitter') {
    return `<svg viewBox="0 0 24 24" class="h-5 w-5 text-gray-500" fill="currentColor">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
    </svg>`
  }
  
  if (platformName === 'facebook') {
    return `<svg viewBox="0 0 24 24" class="h-5 w-5 text-gray-500" fill="currentColor">
      <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
    </svg>`
  }
  
  if (platformName === 'youtube') {
    return `<svg viewBox="0 0 24 24" class="h-5 w-5 text-gray-500" fill="currentColor">
      <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
    </svg>`
  }
  
  return `<svg class="h-5 w-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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

onMounted(() => {
  fetchClusterData()
})
</script>