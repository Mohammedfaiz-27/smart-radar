<template>
  <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center space-x-3">
        <div class="p-2 bg-blue-100 rounded-lg">
          <svg class="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-8l-4 4z" />
          </svg>
        </div>
        <div>
          <h2 class="text-lg font-semibold text-gray-900"># Social Media Monitor</h2>
        </div>
      </div>
      <div class="flex items-center space-x-2">
        <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
        <span class="text-sm text-green-600 font-medium">Live Feed</span>
      </div>
    </div>

    <!-- Live Feed Content -->
    <div class="flex-1 overflow-hidden">
      <div class="space-y-4 max-h-96 overflow-y-auto">
        <div
          v-for="post in livePosts"
          :key="post.id"
          class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
        >
          <!-- Post Header -->
          <div class="flex items-start justify-between mb-3">
            <div class="flex items-center space-x-3">
              <!-- Platform Icon -->
              <div v-if="post.platform === 'x'" class="w-6 h-6 text-gray-600">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                </svg>
              </div>
              <div v-else-if="post.platform === 'facebook'" class="w-6 h-6 text-blue-600">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                </svg>
              </div>
              
              <div class="flex flex-col">
                <span class="font-medium text-gray-900">{{ post.author }}</span>
                <div class="flex items-center space-x-2 text-sm text-gray-500">
                  <span>{{ formatTimeAgo(post.posted_at) }}</span>
                  <span 
                    :class="[
                      'px-2 py-1 text-xs rounded-full font-medium',
                      getThreatBadgeColor(post.threat_level)
                    ]"
                  >
                    {{ post.threat_level }}
                  </span>
                </div>
              </div>
            </div>
            
            <!-- External Link -->
            <a 
              :href="post.post_url" 
              target="_blank"
              rel="noopener noreferrer"
              class="text-gray-400 hover:text-gray-600"
            >
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>

          <!-- Post Content -->
          <p class="text-gray-800 mb-3 leading-relaxed">
            {{ post.content }}
          </p>

          <!-- Engagement & Actions -->
          <div class="flex items-center justify-between">
            <!-- Engagement Metrics -->
            <div class="flex items-center space-x-4 text-sm text-gray-500">
              <span class="flex items-center space-x-1">
                <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
                </svg>
                <span>{{ formatNumber(post.engagement_metrics?.likes || 0) }}</span>
              </span>
              <span class="flex items-center space-x-1">
                <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clip-rule="evenodd" />
                </svg>
                <span>{{ formatNumber(post.engagement_metrics?.comments || 0) }}</span>
              </span>
            </div>

            <!-- Action Buttons -->
            <div class="flex items-center space-x-2">
              <button 
                class="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
                @click="analyzePost(post)"
              >
                Analyze
              </button>
              <button 
                class="px-3 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 transition-colors"
                @click="generateResponse(post)"
              >
                Generate Response
              </button>
              <button 
                class="px-3 py-1 text-xs bg-purple-100 text-purple-700 rounded hover:bg-purple-200 transition-colors"
                @click="trackThread(post)"
              >
                Track Thread
              </button>
            </div>
          </div>

          <!-- Sentiment Badge -->
          <div class="mt-3 flex justify-end">
            <span 
              :class="[
                'px-2 py-1 text-xs rounded-full font-medium',
                getSentimentColor(post.intelligence?.sentiment_score)
              ]"
            >
              {{ getSentimentLabel(post.intelligence?.sentiment_score) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="flex justify-center py-8">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>

      <!-- Empty State -->
      <div v-if="!loading && livePosts.length === 0" class="text-center py-8 text-gray-500">
        <svg class="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-8l-4 4z" />
        </svg>
        <p>No live social media posts at the moment</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { usePostsStore } from '@/stores/posts'

const postsStore = usePostsStore()
const livePosts = ref([])
const loading = ref(false)
let refreshInterval = null

const fetchLivePosts = async () => {
  loading.value = true
  try {
    const response = await fetch('http://localhost:8000/api/v1/posts?limit=10')
    if (response.ok) {
      const posts = await response.json()
      // Add threat levels and format data
      livePosts.value = posts.map(post => ({
        ...post,
        threat_level: getThreatLevel(post.intelligence?.sentiment_score, post.engagement_metrics)
      }))
    }
  } catch (error) {
    console.error('Error fetching live posts:', error)
  } finally {
    loading.value = false
  }
}

const getThreatLevel = (sentimentScore, engagement) => {
  const likes = engagement?.likes || 0
  const comments = engagement?.comments || 0
  const totalEngagement = likes + comments

  if (sentimentScore < -0.5 && totalEngagement > 1000) return 'high'
  if (sentimentScore < -0.3 && totalEngagement > 500) return 'medium'
  if (sentimentScore < 0) return 'low'
  return 'neutral'
}

const getThreatBadgeColor = (threatLevel) => {
  switch (threatLevel) {
    case 'high': return 'bg-red-100 text-red-800'
    case 'medium': return 'bg-orange-100 text-orange-800'
    case 'low': return 'bg-yellow-100 text-yellow-800'
    default: return 'bg-gray-100 text-gray-600'
  }
}

const getSentimentColor = (score) => {
  if (score === null || score === undefined) return 'bg-gray-100 text-gray-600'
  if (score > 0.3) return 'bg-green-100 text-green-800'
  if (score < -0.3) return 'bg-red-100 text-red-800'
  return 'bg-yellow-100 text-yellow-800'
}

const getSentimentLabel = (score) => {
  if (score === null || score === undefined) return 'neutral'
  if (score > 0.3) return 'positive'
  if (score < -0.3) return 'negative'
  return 'neutral'
}

const formatTimeAgo = (dateString) => {
  const now = new Date()
  const date = new Date(dateString)
  const diffInMinutes = Math.floor((now - date) / (1000 * 60))
  
  if (diffInMinutes < 1) return 'now'
  if (diffInMinutes < 60) return `${diffInMinutes}m ago`
  if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`
  return `${Math.floor(diffInMinutes / 1440)}d ago`
}

const formatNumber = (num) => {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toString()
}

const analyzePost = (post) => {
  console.log('Analyzing post:', post.id)
  // Implement analysis logic
}

const generateResponse = (post) => {
  console.log('Generating response for post:', post.id)
  // Implement response generation logic
}

const trackThread = (post) => {
  console.log('Tracking thread for post:', post.id)
  // Implement thread tracking logic
}

onMounted(() => {
  fetchLivePosts()
  // Refresh every 30 seconds
  refreshInterval = setInterval(fetchLivePosts, 30000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>