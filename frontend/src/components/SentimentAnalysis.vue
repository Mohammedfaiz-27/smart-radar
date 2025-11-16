<template>
  <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center space-x-3">
        <div class="p-2 bg-blue-100 rounded-lg">
          <svg class="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <div>
          <h2 class="text-lg font-semibold text-gray-900">Sentiment Analysis</h2>
          <p class="text-sm text-gray-500">{{ title }} sentiment breakdown</p>
        </div>
      </div>
      <div class="flex items-center text-sm">
        <svg class="h-4 w-4 text-green-500 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 17l9.2-9.2M17 17V7H7" />
        </svg>
        <span class="text-green-600 font-medium">{{ sentimentChange }}%</span>
      </div>
    </div>

    <!-- Overall Public Sentiment -->
    <div class="mb-6">
      <h3 class="text-base font-medium text-gray-900 mb-4">Overall Public Sentiment</h3>
      
      <div class="space-y-3">
        <!-- Positive -->
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium text-green-600">Positive</span>
          <span class="text-sm font-bold text-gray-900">{{ overallSentiment.positive_percentage }}%</span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2">
          <div 
            class="bg-green-500 h-2 rounded-full transition-all duration-500"
            :style="{ width: overallSentiment.positive_percentage + '%' }"
          ></div>
        </div>

        <!-- Neutral -->
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium text-gray-500">Neutral</span>
          <span class="text-sm font-bold text-gray-900">{{ overallSentiment.neutral_percentage }}%</span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2">
          <div 
            class="bg-blue-500 h-2 rounded-full transition-all duration-500"
            :style="{ width: overallSentiment.neutral_percentage + '%' }"
          ></div>
        </div>

        <!-- Negative -->
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium text-red-600">Negative</span>
          <span class="text-sm font-bold text-gray-900">{{ overallSentiment.negative_percentage }}%</span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2">
          <div 
            class="bg-red-500 h-2 rounded-full transition-all duration-500"
            :style="{ width: overallSentiment.negative_percentage + '%' }"
          ></div>
        </div>
      </div>
    </div>

    <!-- Cluster Sentiment -->
    <div class="mb-6">
      <h3 class="text-base font-medium text-gray-900 mb-4">Cluster Sentiment</h3>
      
      <div class="space-y-4">
        <!-- Primary Cluster (First cluster of the type) -->
        <div 
          v-if="primaryCluster"
          class="border border-gray-200 rounded-xl p-4 cursor-pointer hover:bg-gray-50 hover:border-gray-300 transition-all duration-200 hover:shadow-md"
          @click="handleClusterClick(primaryCluster.name)"
        >
          <!-- Cluster Header -->
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center space-x-3">
              <div class="w-3 h-3 rounded-full" :class="type === 'own' ? 'bg-blue-500' : 'bg-orange-500'"></div>
              <span class="font-medium text-gray-900">{{ primaryCluster.name }}</span>
            </div>
            <div class="flex items-center space-x-4 text-sm text-gray-500">
              <span>{{ formatNumber(overallSentiment.total_posts || 0) }} posts</span>
              <div class="flex items-center">
                <svg class="h-3 w-3 text-green-500 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 17l9.2-9.2M17 17V7H7" />
                </svg>
                <span class="text-green-600 font-medium">{{ sentimentChange }}%</span>
              </div>
            </div>
          </div>

          <!-- Cluster Sentiment Bars -->
          <div class="flex h-2 rounded-full overflow-hidden bg-gray-200 mb-2">
            <div 
              class="bg-green-500 transition-all duration-500"
              :style="{ width: overallSentiment.positive_percentage + '%' }"
            ></div>
            <div 
              class="bg-blue-500 transition-all duration-500"
              :style="{ width: overallSentiment.neutral_percentage + '%' }"
            ></div>
            <div 
              class="bg-red-500 transition-all duration-500"
              :style="{ width: overallSentiment.negative_percentage + '%' }"
            ></div>
          </div>

          <!-- Cluster Sentiment Labels -->
          <div class="flex justify-between items-center text-xs">
            <span class="text-green-600 font-medium">
              {{ overallSentiment.positive_percentage }}%
            </span>
            <span class="text-blue-500 font-medium">
              {{ overallSentiment.neutral_percentage }}%
            </span>
            <span class="text-red-600 font-medium">
              {{ overallSentiment.negative_percentage }}%
            </span>
          </div>
        </div>

        <!-- Secondary Cluster (TN GOVERNMENT/ADMK) -->
        <div 
          v-for="cluster in filteredClusters"
          :key="cluster.id"
          class="border border-gray-200 rounded-xl p-4 cursor-pointer hover:bg-gray-50 hover:border-gray-300 transition-all duration-200 hover:shadow-md"
          @click="handleClusterClick(cluster.name)"
        >
          <!-- Cluster Header -->
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center space-x-3">
              <div class="w-3 h-3 rounded-full" :class="type === 'own' ? 'bg-blue-500' : 'bg-orange-500'"></div>
              <span class="font-medium text-gray-900">{{ cluster.name }}</span>
            </div>
            <div class="flex items-center space-x-4 text-sm text-gray-500">
              <span>{{ formatNumber(clusterSentimentData[cluster.id]?.total_posts || 0) }} posts</span>
              <div class="flex items-center">
                <svg class="h-3 w-3 text-green-500 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 17l9.2-9.2M17 17V7H7" />
                </svg>
                <span class="text-green-600 font-medium">{{ sentimentChange }}%</span>
              </div>
            </div>
          </div>

          <!-- Cluster Sentiment Bars -->
          <div class="flex h-2 rounded-full overflow-hidden bg-gray-200 mb-2">
            <div 
              class="bg-green-500 transition-all duration-500"
              :style="{ width: (clusterSentimentData[cluster.id]?.positive_percentage || 0) + '%' }"
            ></div>
            <div 
              class="bg-blue-500 transition-all duration-500"
              :style="{ width: (clusterSentimentData[cluster.id]?.neutral_percentage || 0) + '%' }"
            ></div>
            <div 
              class="bg-red-500 transition-all duration-500"
              :style="{ width: (clusterSentimentData[cluster.id]?.negative_percentage || 0) + '%' }"
            ></div>
          </div>

          <!-- Cluster Sentiment Labels -->
          <div class="flex justify-between items-center text-xs">
            <span class="text-green-600 font-medium">
              {{ clusterSentimentData[cluster.id]?.positive_percentage || 0 }}%
            </span>
            <span class="text-blue-500 font-medium">
              {{ clusterSentimentData[cluster.id]?.neutral_percentage || 0 }}%
            </span>
            <span class="text-red-600 font-medium">
              {{ clusterSentimentData[cluster.id]?.negative_percentage || 0 }}%
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Platform Breakdown -->
    <div>
      <h3 class="text-base font-medium text-gray-900 mb-4">Platform Breakdown</h3>
      
      <div class="space-y-6">
        <div
          v-for="(platformData, platform) in platformBreakdown"
          :key="platform"
          class="border border-gray-200 rounded-xl p-4 cursor-pointer hover:bg-gray-50 hover:border-gray-300 transition-all duration-200 hover:shadow-md"
          @click="handlePlatformClick(platform, platformData)"
        >
          <!-- Platform Header -->
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center space-x-3">
              <div v-html="getPlatformIcon(platform)"></div>
              <span class="font-medium text-gray-900">{{ formatPlatformName(platform) }}</span>
            </div>
            <div class="flex items-center space-x-4 text-sm text-gray-500">
              <span>{{ formatNumber(platformData.total_posts) }} posts</span>
              <div class="flex items-center">
                <svg class="h-3 w-3 text-green-500 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 17l9.2-9.2M17 17V7H7" />
                </svg>
                <span class="text-green-600 font-medium">{{ platformData.sentiment_change }}%</span>
              </div>
            </div>
          </div>

          <!-- Platform Sentiment Bars -->
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

          <!-- Platform Sentiment Labels -->
          <div class="flex justify-between items-center mt-2 text-xs">
            <span class="text-green-600 font-medium">
              {{ getPlatformPercentage(platformData, 'positive') }}%
            </span>
            <span class="text-blue-500 font-medium">
              {{ getPlatformPercentage(platformData, 'neutral') }}%
            </span>
            <span class="text-red-600 font-medium">
              {{ getPlatformPercentage(platformData, 'negative') }}%
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePostsStore } from '@/stores/posts'
import { useClustersStore } from '@/stores/clusters'
import { 
  ChatBubbleLeftRightIcon,
  GlobeAltIcon,
  PlayIcon,
  PhotoIcon
} from '@heroicons/vue/24/outline'

// Initialize stores
const postsStore = usePostsStore()
const clustersStore = useClustersStore()

const props = defineProps({
  type: {
    type: String,
    required: true,
    validator: (value) => ['organization', 'competitors', 'overall', 'own'].includes(value)
  },
  title: {
    type: String,
    default: 'Overall'
  },
  clusterId: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['openPlatformModal'])

const loading = ref(false)
const clusters = ref([])
const sentimentData = ref({
  overall_sentiment: {
    positive_percentage: 0,
    neutral_percentage: 0,
    negative_percentage: 0,
    total_posts: 0
  },
  platform_breakdown: {},
  overall_sentiment_change: 0
})

// Cluster data by cluster ID
const clusterSentimentData = ref({})

const overallSentiment = computed(() => {
  return sentimentData.value.overall_sentiment || {
    positive_percentage: 0,
    neutral_percentage: 0,
    negative_percentage: 0,
    total_posts: 0
  }
})

// Static platform list - always show all 4 platforms
const staticPlatforms = ['X', 'Facebook', 'YouTube', 'Google News']

const platformBreakdown = computed(() => {
  const breakdown = sentimentData.value.platform_breakdown || {}

  // Create static platform object with all platforms
  const staticBreakdown = {}

  staticPlatforms.forEach(platform => {
    const platformKey = platform.toLowerCase()
    staticBreakdown[platform] = breakdown[platform] || breakdown[platformKey] || {
      total_posts: 0,
      sentiments: { positive: 0, negative: 0, neutral: 0 },
      sentiment_change: 0
    }
  })

  return staticBreakdown
})

const sentimentChange = computed(() => {
  return sentimentData.value.overall_sentiment_change || 0
})

// Get primary cluster for this type
const primaryCluster = computed(() => {
  const clusterType = (props.type === 'organization' || props.type === 'own') ? 'own' : 'competitor'
  const clusters = clustersStore.getClustersByType(clusterType)
  return clusters.length > 0 ? clusters[0] : null
})

// Filter clusters by type using cluster store (excluding primary)
const filteredClusters = computed(() => {
  const clusterType = (props.type === 'organization' || props.type === 'own') ? 'own' : 'competitor'
  const clusters = clustersStore.getClustersByType(clusterType)
  // Exclude the primary cluster from the additional clusters list
  return clusters.slice(1) // Return all except the first one
})

const getPlatformIcon = (platform) => {
  const platformName = platform.toLowerCase()
  
  // Return SVG string for brand logos
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
  
  if (platformName === 'instagram') {
    return `<svg viewBox="0 0 24 24" class="h-5 w-5 text-gray-500" fill="currentColor">
      <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
    </svg>`
  }
  
  // Default fallback - return a default SVG icon
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

const formatNumber = (num) => {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toString()
}

const getPlatformPercentage = (platformData, sentimentType) => {
  const sentiments = platformData.sentiments || {}
  const total = platformData.total_posts || 1
  const count = sentiments[sentimentType] || 0
  return Math.round((count / total) * 100)
}

// Helper function to get relevant posts based on component type using API cluster_type
const getRelevantPosts = () => {
  const allPosts = postsStore.posts
  
  if (props.type === 'organization' || props.type === 'own') {
    // Use API cluster_type for accurate classification
    return allPosts.filter(post => post.cluster_type === 'own')
  } else if (props.type === 'competitors') {
    // Use API cluster_type for accurate classification  
    return allPosts.filter(post => post.cluster_type === 'competitor')
  } else {
    return allPosts // Overall
  }
}

// Helper function to calculate sentiment from posts using new posts_table format
const calculateSentimentFromPosts = (posts) => {
  let positive = 0
  let negative = 0
  let neutral = 0
  const platformCounts = {}
  
  posts.forEach(post => {
    const platform = post.platform || 'unknown'
    const sentiment = post.sentiment || 'neutral'
    
    // Initialize platform counts if not exists
    if (!platformCounts[platform]) {
      platformCounts[platform] = {
        total_posts: 0,
        sentiments: { positive: 0, negative: 0, neutral: 0 },
        sentiment_change: 0
      }
    }
    
    platformCounts[platform].total_posts++
    
    // Count sentiments based on post.sentiment field
    if (sentiment === 'positive') {
      positive++
      platformCounts[platform].sentiments.positive++
    } else if (sentiment === 'negative') {
      negative++
      platformCounts[platform].sentiments.negative++
    } else {
      neutral++
      platformCounts[platform].sentiments.neutral++
    }
  })
  
  const total = positive + negative + neutral || 1
  
  return {
    overall_sentiment: {
      positive_percentage: Math.round((positive / total) * 100),
      negative_percentage: Math.round((negative / total) * 100),
      neutral_percentage: Math.round((neutral / total) * 100),
      total_posts: posts.length
    },
    platform_breakdown: platformCounts,
    overall_sentiment_change: 0 // Could be calculated from historical data
  }
}

const fetchSentimentData = async () => {
  loading.value = true
  try {
    // Ensure we have posts data
    await postsStore.fetchPosts()
    
    // Calculate sentiment from posts store
    const posts = getRelevantPosts()
    const calculatedSentiment = calculateSentimentFromPosts(posts)
    
    sentimentData.value = {
      overall_sentiment: calculatedSentiment.overall_sentiment,
      platform_breakdown: calculatedSentiment.platform_breakdown,
      overall_sentiment_change: calculatedSentiment.overall_sentiment_change || 0
    }
    
    console.log(`📊 Calculated sentiment for ${props.type}:`, sentimentData.value)
    
  } catch (error) {
    console.error('Error calculating sentiment data:', error)
    // Fallback to API if available
    try {
      let endpoint
      if (props.clusterId) {
        endpoint = props.type === 'organization' || props.type === 'own'
          ? `/api/v1/sentiment/organization?cluster_id=${props.clusterId}`
          : `/api/v1/sentiment/competitors?cluster_id=${props.clusterId}`
      } else {
        endpoint = props.type === 'organization' || props.type === 'own'
          ? '/api/v1/sentiment/organization'
          : props.type === 'competitors'
          ? '/api/v1/sentiment/competitors'
          : '/api/v1/sentiment/overall'
      }
      
      const response = await fetch(`http://localhost:8000${endpoint}`)
      if (response.ok) {
        sentimentData.value = await response.json()
      }
    } catch (fallbackError) {
      console.error('Fallback API also failed:', fallbackError)
    }
  } finally {
    loading.value = false
  }
}

// Fetch clusters using cluster store
const fetchClusters = async () => {
  try {
    await clustersStore.fetchClusters()
    
    // Fetch sentiment data for each filtered cluster
    await fetchClusterSentiments()
  } catch (error) {
    console.error('Error fetching clusters:', error)
  }
}

// Fetch sentiment data for individual clusters using API cluster IDs
const fetchClusterSentiments = async () => {
  const clusterType = (props.type === 'organization' || props.type === 'own') ? 'own' : 'competitor'
  const relevantClusters = clustersStore.getClustersByType(clusterType)
  
  for (const cluster of relevantClusters) {
    try {
      // Get posts that are specifically assigned to this cluster via API
      const clusterPosts = postsStore.posts.filter(post => post.cluster_id === cluster.id)
      const calculatedSentiment = calculateSentimentFromPosts(clusterPosts)
      
      clusterSentimentData.value[cluster.id] = calculatedSentiment.overall_sentiment || {
        positive_percentage: 0,
        neutral_percentage: 0,
        negative_percentage: 0,
        total_posts: 0
      }
      
      console.log(`📊 Calculated sentiment for cluster "${cluster.name}":`, 
        clusterSentimentData.value[cluster.id], 
        `(${clusterPosts.length} posts with cluster_id: ${cluster.id})`
      )
    } catch (error) {
      console.error(`Error calculating sentiment for cluster ${cluster.name}:`, error)
    }
  }
}

const router = useRouter()

const handleClusterClick = (clusterName) => {
  console.log('Navigating to cluster posts:', clusterName)
  router.push({
    name: 'cluster-posts',
    params: { name: clusterName }
  })
}

const handlePlatformClick = async (platform, platformData) => {
  console.log('Opening platform modal for:', platform, platformData)
  
  try {
    // Fetch posts for this platform and cluster type
    const clusterType = (props.type === 'organization' || props.type === 'own') ? 'own' : 'competitor'
    const response = await fetch(`http://localhost:8000/api/v1/posts?cluster_type=${clusterType}&platform=${platform}`)
    
    if (response.ok) {
      const posts = await response.json()
      const platformName = formatPlatformName(platform)
      const title = `${clusterType === 'own' ? 'Our Organization' : 'Competitors'} - ${platformName}`
      
      emit('openPlatformModal', {
        title,
        posts,
        platform
      })
    } else {
      console.error('Failed to fetch platform posts')
    }
  } catch (error) {
    console.error('Error fetching platform posts:', error)
  }
}

onMounted(async () => {
  await Promise.all([
    fetchSentimentData(),
    fetchClusters()
  ])
})
</script>