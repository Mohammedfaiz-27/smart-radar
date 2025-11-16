<template>
  <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center space-x-3">
        <div class="p-2 bg-blue-100 rounded-lg">
          <svg class="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9.5a2 2 0 00-2-2h-2m-4-3v8m0 0V9.5a2 2 0 012-2h2M7 13h10v6a1 1 0 01-1 1H8a1 1 0 01-1-1v-6zM7 13V9.5a2 2 0 012-2h2m3 7h2a1 1 0 001-1v-1a1 1 0 00-1-1h-2m-1 0V7.5a2 2 0 012-2h1a1 1 0 011 1V13M7 13h6" />
          </svg>
        </div>
        <div>
          <h2 class="text-lg font-semibold text-gray-900">📰 News Monitor</h2>
        </div>
      </div>
      <div class="flex items-center space-x-2">
        <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
        <span class="text-sm text-green-600 font-medium">Live Updates</span>
      </div>
    </div>

    <!-- News Feed Content -->
    <div class="flex-1 overflow-hidden">
      <div class="space-y-4 max-h-96 overflow-y-auto">
        <div
          v-for="article in newsArticles"
          :key="article.id"
          class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
          @click="openArticle(article)"
        >
          <!-- Article Header -->
          <div class="flex items-start justify-between mb-3">
            <div class="flex-1">
              <h3 class="font-medium text-gray-900 leading-tight mb-2">
                {{ article.title }}
              </h3>
              <div class="flex items-center space-x-4 text-sm text-gray-500">
                <span class="font-medium">{{ article.source }}</span>
                <span>{{ formatTimeAgo(article.published_at) }}</span>
                <span class="flex items-center space-x-1">
                  <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  <span>{{ formatNumber(article.readers_count) }} readers</span>
                </span>
              </div>
            </div>
            
            <!-- External Link -->
            <a 
              :href="article.url" 
              target="_blank"
              rel="noopener noreferrer"
              class="text-gray-400 hover:text-gray-600 ml-3"
              @click.stop
            >
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>

          <!-- Article Summary -->
          <p class="text-gray-700 text-sm mb-3 line-clamp-2">
            {{ article.summary }}
          </p>

          <!-- Tags and Impact -->
          <div class="flex items-center justify-between">
            <!-- Tags -->
            <div class="flex items-center space-x-2">
              <span
                v-for="tag in article.tags.slice(0, 2)"
                :key="tag"
                :class="[
                  'px-2 py-1 text-xs rounded-full font-medium',
                  getTagColor(tag)
                ]"
              >
                {{ tag }}
              </span>
            </div>

            <!-- Impact Level -->
            <span 
              :class="[
                'px-2 py-1 text-xs rounded-full font-medium',
                getImpactColor(article.impact_level)
              ]"
            >
              {{ article.impact_level }} impact
            </span>
          </div>

          <!-- Action Buttons -->
          <div class="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
            <div class="flex items-center space-x-2">
              <button 
                class="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
                @click.stop="fullAnalysis(article)"
              >
                Full Analysis
              </button>
              <button 
                class="px-3 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 transition-colors"
                @click.stop="generateResponse(article)"
              >
                Generate Response
              </button>
              <button 
                class="px-3 py-1 text-xs bg-purple-100 text-purple-700 rounded hover:bg-purple-200 transition-colors"
                @click.stop="trackCoverage(article)"
              >
                Track Coverage
              </button>
            </div>

            <!-- Sentiment -->
            <span 
              :class="[
                'px-2 py-1 text-xs rounded-full font-medium',
                getSentimentColor(article.sentiment)
              ]"
            >
              {{ article.sentiment }}
            </span>
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="flex justify-center py-8">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>

      <!-- Empty State -->
      <div v-if="!loading && newsArticles.length === 0" class="text-center py-8 text-gray-500">
        <svg class="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9.5a2 2 0 00-2-2h-2m-4-3v8m0 0V9.5a2 2 0 012-2h2M7 13h10v6a1 1 0 01-1 1H8a1 1 0 01-1-1v-6zM7 13V9.5a2 2 0 012-2h2m3 7h2a1 1 0 001-1v-1a1 1 0 00-1-1h-2m-1 0V7.5a2 2 0 012-2h1a1 1 0 011 1V13M7 13h6" />
        </svg>
        <p>No news articles available</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const newsArticles = ref([])
const loading = ref(false)
let refreshInterval = null

const fetchNewsArticles = async () => {
  loading.value = true
  try {
    // Fetch real news data from API
    const response = await fetch('http://localhost:8000/api/v1/news?limit=10&hours_back=24')
    if (response.ok) {
      const articles = await response.json()
      
      // Transform API data to match component expectations
      newsArticles.value = articles.map(article => ({
        id: article.id,
        title: article.title,
        summary: article.summary || 'No summary available',
        source: article.source,
        published_at: article.published_at,
        readers_count: article.readers_count || 0,
        url: article.url,
        tags: article.tags || [],
        impact_level: article.intelligence?.impact_level || 'medium',
        sentiment: getSentimentLabel(article.intelligence?.sentiment_score)
      }))
    } else {
      console.error('Failed to fetch news articles:', response.status)
      // Fallback to empty array if API fails
      newsArticles.value = []
    }
  } catch (error) {
    console.error('Error fetching news articles:', error)
    // Fallback to empty array if fetch fails
    newsArticles.value = []
  } finally {
    loading.value = false
  }
}

const getTagColor = (tag) => {
  const colors = {
    'Politics': 'bg-blue-100 text-blue-800',
    'Environment': 'bg-green-100 text-green-800',
    'Economy': 'bg-purple-100 text-purple-800',
    'Business': 'bg-indigo-100 text-indigo-800',
    'Social Policy': 'bg-pink-100 text-pink-800',
    'Youth': 'bg-yellow-100 text-yellow-800'
  }
  return colors[tag] || 'bg-gray-100 text-gray-800'
}

const getImpactColor = (impact) => {
  switch (impact) {
    case 'high': return 'bg-red-100 text-red-800'
    case 'medium': return 'bg-orange-100 text-orange-800'
    case 'low': return 'bg-yellow-100 text-yellow-800'
    default: return 'bg-gray-100 text-gray-600'
  }
}

const getSentimentColor = (sentiment) => {
  switch (sentiment) {
    case 'positive': return 'bg-green-100 text-green-800'
    case 'negative': return 'bg-red-100 text-red-800'
    case 'neutral': return 'bg-gray-100 text-gray-600'
    default: return 'bg-gray-100 text-gray-600'
  }
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

const openArticle = (article) => {
  window.open(article.url, '_blank')
}

const fullAnalysis = (article) => {
  console.log('Full analysis for article:', article.id)
  // Implement full analysis logic
}

const generateResponse = (article) => {
  console.log('Generate response for article:', article.id)
  // Implement response generation logic
}

const trackCoverage = (article) => {
  console.log('Track coverage for article:', article.id)
  // Implement coverage tracking logic
}

onMounted(() => {
  fetchNewsArticles()
  // Refresh every 2 minutes
  refreshInterval = setInterval(fetchNewsArticles, 120000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>