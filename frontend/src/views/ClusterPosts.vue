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
              {{ name }} Posts by Platform
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
        <p class="mt-2 text-sm text-gray-500">Loading posts...</p>
      </div>

      <!-- Content -->
      <div v-else>

        <!-- Platform Tabs -->
        <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <!-- Tab Navigation -->
          <div class="border-b border-gray-200 mb-6">
            <nav class="flex space-x-4 overflow-x-auto scrollbar-hide pb-2"
                 style="scrollbar-width: none; -ms-overflow-style: none;"
            >
              <button
                v-for="platform in ['all', 'twitter', 'facebook', 'youtube', 'web_news', 'print_magazine', 'print_daily']"
                :key="platform"
                @click="activeTab = platform"
                class="flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm transition-colors whitespace-nowrap flex-shrink-0"
                :class="activeTab === platform 
                  ? 'border-yellow-500 text-gray-900' 
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
              >
                <div v-if="platform !== 'all'" v-html="getPlatformIcon(platform)" class="w-4 h-4 flex-shrink-0"></div>
                <span class="whitespace-nowrap">
                  {{ platform === 'all' ? 'ALL PLATFORMS' : formatPlatformName(platform).toUpperCase() }}
                </span>
                <span 
                  class="py-1 px-2 text-xs rounded-full flex-shrink-0"
                  :class="activeTab === platform ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-600'"
                >
                  {{ platform === 'all' ? totalPosts : (platformCounts[platform] || 0) }}
                </span>
              </button>
            </nav>
          </div>

          <!-- Tab Content -->
          <div class="min-h-96">
            <!-- Posts Grid -->
            <div v-if="currentTabPosts.length === 0" class="text-center py-16">
              <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
              </div>
              <h3 class="text-lg font-medium text-gray-900 mb-2">No Posts Found</h3>
              <p class="text-gray-500">
                {{ activeTab === 'all' 
                  ? `No posts found for the ${name} cluster.` 
                  : `No posts found for ${formatPlatformName(activeTab)}.` 
                }}
              </p>
            </div>
            
            <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div
                v-for="post in currentTabPosts.slice(0, showAllPosts[activeTab] ? currentTabPosts.length : 9)"
                :key="post.id"
                class="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors cursor-pointer"
                @click="post.platform === 'print_magazine' ? openPrintMagazineModal(post) : null"
              >
                <div class="flex items-start justify-between mb-3">
                  <div class="flex items-center space-x-3">
                    <div class="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                      <span class="text-xs font-medium text-gray-600">
                        {{ getAuthorName(post)[0].toUpperCase() }}
                      </span>
                    </div>
                    <div>
                      <div class="text-sm font-medium text-gray-900">@{{ getAuthorName(post) }}</div>
                      <div class="text-xs text-gray-500 flex items-center space-x-2">
                        <span>{{ formatDate(post.posted_at) }}</span>
                        <span>•</span>
                        <span>{{ formatPlatformName(post.platform) }}</span>
                      </div>
                    </div>
                  </div>
                  <div class="flex items-center space-x-2">
                    <button 
                      @click="openOriginalPost(post)"
                      class="text-gray-400 hover:text-gray-600 transition-colors p-1"
                      :title="(post.post_url || post.url) ? 'View original post' : 'No URL available'"
                      :disabled="!(post.post_url || post.url)"
                      :class="{ 'opacity-50 cursor-not-allowed': !(post.post_url || post.url) }"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                      </svg>
                    </button>
                    <span 
                      class="px-2 py-1 rounded-full text-xs font-medium"
                      :class="getSentimentClass(post.sentiment)"
                    >
                      {{ (post.sentiment || 'neutral').toUpperCase() }}
                    </span>
                  </div>
                </div>
                
                <p class="text-sm text-gray-700 mb-3" :class="(post.platform === 'print_magazine' || post.platform === 'print_daily') ? 'line-clamp-none' : 'line-clamp-3'">{{ 
                  (post.platform === 'print_magazine' || post.platform === 'print_daily')
                    ? (post.content?.text || post.content) 
                    : post.content 
                }}</p>
                
                <div class="flex items-center justify-between text-xs text-gray-500">
                  <div class="flex items-center space-x-3" v-if="post.platform !== 'print_magazine' && post.platform !== 'print_daily'">
                    <span>{{ formatNumber(post.engagement_metrics?.views || 0) }} views</span>
                    <span>{{ formatNumber(post.engagement_metrics?.likes || 0) }} likes</span>
                    <span>{{ formatNumber(post.engagement_metrics?.comments || 0) }} comments</span>
                  </div>
                  <div v-else class="flex-1"></div>
                  <div class="flex items-center space-x-2">
                    <button v-if="post.platform !== 'print_magazine' && post.platform !== 'print_daily'" class="text-blue-600 hover:text-blue-800 font-medium">
                      Analyze
                    </button>
                    <button 
                      @click="handleRespond(post)"
                      class="text-green-600 hover:text-green-800 font-medium"
                    >
                      {{ getButtonText(post) }}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Show More/Less Button -->
            <div v-if="currentTabPosts.length > 9" class="mt-6 text-center">
              <button 
                @click="toggleShowAll(activeTab)"
                class="px-6 py-2 text-sm font-medium text-blue-600 hover:text-blue-800 border border-blue-300 rounded-lg hover:bg-blue-50 transition-colors"
              >
                {{ showAllPosts[activeTab] ? 'Show Less' : `Show All ${currentTabPosts.length} Posts` }}
              </button>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div v-if="totalPosts === 0" class="bg-white rounded-2xl shadow-sm border border-gray-200 p-12 text-center">
          <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
          </div>
          <h3 class="text-lg font-medium text-gray-900 mb-2">No Posts Found</h3>
          <p class="text-gray-500">No posts found for the {{ name }} cluster. Check back later for updates.</p>
        </div>
      </div>
    </main>
    
    <!-- Response Panel Modal -->
    <ResponsePanel />
    
    <!-- Print Magazine Modal -->
    <div v-if="showPrintMagazineModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click="closePrintMagazineModal">
      <div class="bg-white rounded-lg max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden" @click.stop>
        <div class="flex justify-between items-center p-6 border-b border-gray-200">
          <div class="flex items-center space-x-4">
            <h2 class="text-xl font-bold text-gray-900">{{ selectedPrintMagazine?.raw_data?.headline || 'Print Magazine Article' }}</h2>
            <span 
              class="px-3 py-1 rounded-full text-sm font-medium"
              :class="getSentimentClass(selectedPrintMagazine?.sentiment)"
            >
              {{ (selectedPrintMagazine?.sentiment || 'neutral').toUpperCase() }}
            </span>
          </div>
          <button @click="closePrintMagazineModal" class="text-gray-400 hover:text-gray-600">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>
        
        <div class="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
          <div class="mb-4">
            <div class="flex items-center space-x-4 text-sm text-gray-500 mb-4">
              <span>{{ selectedPrintMagazine?.author?.publication_name || 'Vikadan' }}</span>
              <span>•</span>
              <span>{{ formatDate(selectedPrintMagazine?.published_at) }}</span>
              <span>•</span>
              <span class="capitalize">{{ selectedPrintMagazine?.threat_level || 'Low' }} Threat</span>
            </div>
            
            <div v-if="selectedPrintMagazine?.threat_campaign_topic" class="mb-4">
              <span class="text-sm font-medium text-gray-700">Topic: </span>
              <span class="text-sm text-gray-600">{{ selectedPrintMagazine.threat_campaign_topic }}</span>
            </div>
          </div>
          
          <div class="prose max-w-none">
            <p class="text-gray-800 leading-relaxed whitespace-pre-line">{{ selectedPrintMagazine?.content?.text || selectedPrintMagazine?.content }}</p>
          </div>
          
          <div v-if="selectedPrintMagazine?.intelligence?.entity_sentiments" class="mt-6 p-4 bg-gray-50 rounded-lg">
            <h4 class="font-medium text-gray-900 mb-3">Sentiment Analysis</h4>
            <div v-for="(sentiment, entity) in selectedPrintMagazine.intelligence.entity_sentiments" :key="entity" class="mb-3">
              <div class="flex items-center justify-between mb-1">
                <span class="font-medium text-gray-700">{{ entity }}</span>
                <span 
                  class="px-2 py-1 rounded text-xs font-medium"
                  :class="getSentimentClass(sentiment.label)"
                >
                  {{ sentiment.label }}
                </span>
              </div>
              <p class="text-sm text-gray-600">{{ sentiment.reasoning }}</p>
            </div>
          </div>
          
          <div class="mt-6 flex justify-end">
            <button 
              @click="handleRespond(selectedPrintMagazine)"
              class="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium"
            >
              {{ getButtonText(selectedPrintMagazine) }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useResponseStore } from '@/stores/response'
import { usePostsStore } from '@/stores/posts'
import ResponsePanel from '@/components/ResponsePanel.vue'

const props = defineProps({
  name: {
    type: String,
    required: true
  }
})

const router = useRouter()
const responseStore = useResponseStore()
const loading = ref(true)
const allPosts = ref([])
const sentimentFilter = ref('')
const sortBy = ref('recent')
const showAllPosts = reactive({})
const platformRefs = reactive({})
const activeTab = ref('all')
const showPrintMagazineModal = ref(false)
const selectedPrintMagazine = ref(null)

// Determine cluster type based on name
const clusterType = computed(() => {
  return props.name.trim() === 'DMK' ? 'own' : 'competitor'
})

const totalPosts = computed(() => allPosts.value.length)

const platformCounts = computed(() => {
  const counts = {}
  allPosts.value.forEach(post => {
    // Normalize platform names to match tab identifiers
    let platform = post.platform?.toLowerCase() || 'unknown'
    
    // Map API platform names to tab identifiers
    if (platform === 'x') {
      platform = 'twitter'
    } else if (platform === 'print magazine') {
      platform = 'print_magazine'
    } else if (platform === 'print daily') {
      platform = 'print_daily'
    }
    
    counts[platform] = (counts[platform] || 0) + 1
  })
  return counts
})

const filteredPosts = computed(() => {
  let posts = allPosts.value

  // Filter by sentiment
  if (sentimentFilter.value) {
    posts = posts.filter(post => 
      (post.sentiment || 'neutral').toLowerCase() === sentimentFilter.value.toLowerCase()
    )
  }

  // Sort posts
  if (sortBy.value === 'recent') {
    posts.sort((a, b) => new Date(b.posted_at) - new Date(a.posted_at))
  } else if (sortBy.value === 'engagement') {
    posts.sort((a, b) => {
      const aEng = (a.engagement_metrics?.views || 0) + (a.engagement_metrics?.likes || 0)
      const bEng = (b.engagement_metrics?.views || 0) + (b.engagement_metrics?.likes || 0)
      return bEng - aEng
    })
  } else if (sortBy.value === 'sentiment') {
    const sentimentOrder = { positive: 3, neutral: 2, negative: 1 }
    posts.sort((a, b) => {
      const aSent = sentimentOrder[a.sentiment || 'neutral']
      const bSent = sentimentOrder[b.sentiment || 'neutral']
      return bSent - aSent
    })
  }

  return posts
})

const postsByPlatform = computed(() => {
  const grouped = {}
  filteredPosts.value.forEach(post => {
    // Normalize platform names to match tab identifiers
    let platform = post.platform?.toLowerCase() || 'unknown'
    
    // Map API platform names to tab identifiers
    if (platform === 'x') {
      platform = 'twitter'
    } else if (platform === 'print magazine') {
      platform = 'print_magazine'
    } else if (platform === 'print daily') {
      platform = 'print_daily'
    }
    
    if (!grouped[platform]) {
      grouped[platform] = []
    }
    grouped[platform].push(post)
  })
  console.log('TVK postsByPlatform grouped:', grouped)
  console.log('TVK Available platforms:', Object.keys(grouped))
  return grouped
})

const currentTabPosts = computed(() => {
  if (activeTab.value === 'all') {
    return filteredPosts.value
  }
  return postsByPlatform.value[activeTab.value] || []
})

const fetchClusterPosts = async () => {
  loading.value = true
  try {
    // First, fetch the cluster by name to get its ID
    const clustersResponse = await fetch('http://localhost:8000/api/v1/clusters/')
    if (!clustersResponse.ok) {
      throw new Error('Failed to fetch clusters')
    }
    
    const clusters = await clustersResponse.json()
    const cluster = clusters.find(c => c.name === props.name)
    
    if (!cluster) {
      throw new Error(`Cluster ${props.name} not found`)
    }
    
    // Fetch posts directly from correct API (bypassing smart selector)
    const postsResponse = await fetch(`http://localhost:8000/api/v1/posts?cluster_id=${cluster.id}&limit=2000`)
    let clusterPosts = []
    
    if (postsResponse.ok) {
      const postsData = await postsResponse.json()
      clusterPosts = Array.isArray(postsData) ? postsData : (postsData.posts || [])
      console.log(`Fetched ${clusterPosts.length} posts for ${cluster.name} cluster directly from API`)
    } else {
      console.error('Failed to fetch posts', postsResponse.status)
    }
    
    // Also fetch news articles, print magazines, and print daily separately
    const newsResponse = await fetch(`http://localhost:8000/api/v1/clusters/${cluster.id}/posts?platform=web_news&limit=1000`)
    const printMagazineResponse = await fetch(`http://localhost:8000/api/v1/posts/print-magazines?cluster_id=${cluster.id}&limit=1000`)
    const printDailyResponse = await fetch(`http://localhost:8000/api/v1/posts/print-daily?cluster_id=${cluster.id}&limit=1000`)
    
    const posts = clusterPosts // Use filtered posts from store
    const newsArticles = []
    const printMagazineArticles = []
    const printDailyArticles = []
    
    // Process news articles
    if (newsResponse.ok) {
      const newsData = await newsResponse.json()
      const newsArray = Array.isArray(newsData) ? newsData : []
      
      // Web news articles are already filtered for this cluster by the backend
      newsArticles.push(...newsArray)
      console.log(`[${new Date().toISOString()}] Fetched ${newsArray.length} web news articles for ${cluster.name} cluster`)
    } else {
      console.error('Failed to fetch news articles', newsResponse.status)
    }
    
    // Process print magazine articles
    if (printMagazineResponse.ok) {
      const printMagazineData = await printMagazineResponse.json()
      const printArray = Array.isArray(printMagazineData) ? printMagazineData : (printMagazineData.articles || [])
      
      // Transform print magazine articles to match post structure
      const transformedPrintMagazines = printArray.map(article => ({
        id: article.id,
        platform: 'print_magazine',
        content: article.content?.text || article.content || '',
        author: article.author?.publication_name || article.author || 'Print Magazine',
        posted_at: article.published_at || article.collected_at,
        url: article.url || '',
        post_url: article.url || '',
        sentiment: article.intelligence?.entity_sentiments ? 
          Object.values(article.intelligence.entity_sentiments)[0]?.label?.toLowerCase() || 'neutral' : 'neutral',
        cluster_type: article.matched_clusters?.[0]?.cluster_type || 'unknown',
        engagement_metrics: {
          views: 0,
          likes: 0,
          comments: 0,
          shares: 0
        },
        threat_level: article.intelligence?.threat_level || 'Low',
        threat_topic: article.intelligence?.threat_campaign_topic || ''
      }))
      
      printMagazineArticles.push(...transformedPrintMagazines)
      console.log(`[${new Date().toISOString()}] Fetched ${transformedPrintMagazines.length} print magazine articles for ${cluster.name} cluster`)
    } else {
      console.error('Failed to fetch print magazine articles', printMagazineResponse.status)
    }
    
    // Process print daily articles
    if (printDailyResponse.ok) {
      const printDailyData = await printDailyResponse.json()
      const printDailyArray = Array.isArray(printDailyData) ? printDailyData : (printDailyData.articles || [])
      
      // Transform print daily articles to match post structure
      const transformedPrintDaily = printDailyArray.map(article => ({
        id: article.id,
        platform: 'print_daily',
        content: article.content?.text || article.content || '',
        author: article.publisher || article.author?.publication_name || article.author || 'Print Daily',
        posted_at: article.published_at || article.collected_at,
        url: article.url || '',
        post_url: article.url || '',
        sentiment: article.intelligence?.entity_sentiments ? 
          Object.values(article.intelligence.entity_sentiments)[0]?.label?.toLowerCase() || 'neutral' : 'neutral',
        cluster_type: article.matched_clusters?.[0]?.cluster_type || 'unknown',
        engagement_metrics: {
          views: 0,
          likes: 0,
          comments: 0,
          shares: 0
        },
        threat_level: article.intelligence?.threat_level || 'Low',
        threat_topic: article.intelligence?.threat_campaign_topic || '',
        publisher: article.publisher || 'Unknown'
      }))
      
      printDailyArticles.push(...transformedPrintDaily)
      console.log(`[${new Date().toISOString()}] Fetched ${transformedPrintDaily.length} print daily articles for ${cluster.name} cluster`)
    } else {
      console.error('Failed to fetch print daily articles', printDailyResponse.status)
    }
    
    // Combine posts, news articles, print magazines, and print daily
    allPosts.value = [...posts, ...newsArticles, ...printMagazineArticles, ...printDailyArticles]
    
    // Debug: Check first few posts for sentiment and URL data
    if (allPosts.value.length > 0) {
      console.log('Sample post data:')
      console.log('First post sentiment:', allPosts.value[0]?.sentiment)
      console.log('First post URL:', allPosts.value[0]?.url)
      console.log('First post post_url:', allPosts.value[0]?.post_url)
      console.log('First post author:', allPosts.value[0]?.author)
      console.log('First post platform:', allPosts.value[0]?.platform)
      console.log('All fields in first post:', Object.keys(allPosts.value[0] || {}))
      console.log('Full first post:', allPosts.value[0])
      
      // Check platform distribution
      const platformCounts = {}
      allPosts.value.forEach(post => {
        const platform = post.platform || 'unknown'
        platformCounts[platform] = (platformCounts[platform] || 0) + 1
      })
      console.log('Platform distribution:', platformCounts)
      
      // Temporary: Add test sentiment variety for debugging (only for posts without sentiment)
      allPosts.value.forEach((post, index) => {
        if (!post.sentiment || post.sentiment === 'neutral') {
          if (index % 3 === 0) post.sentiment = 'positive'
          else if (index % 3 === 1) post.sentiment = 'negative'
          else post.sentiment = 'neutral'
        }
      })
      
      // Check sentiment distribution
      const sentimentCounts = {}
      allPosts.value.forEach(post => {
        const sentiment = post.sentiment || 'neutral'
        sentimentCounts[sentiment] = (sentimentCounts[sentiment] || 0) + 1
      })
      console.log('Sentiment distribution after test data:', sentimentCounts)
    }
  } catch (error) {
    console.error('Error fetching cluster posts:', error)
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

const openOriginalPost = (post) => {
  const url = post.post_url || post.url
  if (url) {
    window.open(url, '_blank', 'noopener,noreferrer')
  } else {
    console.log('No URL available for this post:', post)
  }
}


const toggleShowAll = (platform) => {
  showAllPosts[platform] = !showAllPosts[platform]
}

const getPlatformIcon = (platform) => {
  const platformName = platform.toLowerCase()
  
  if (platformName === 'x' || platformName === 'twitter') {
    return `<svg viewBox="0 0 24 24" class="h-6 w-6 text-gray-500" fill="currentColor">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
    </svg>`
  }
  
  if (platformName === 'facebook') {
    return `<svg viewBox="0 0 24 24" class="h-6 w-6 text-gray-500" fill="currentColor">
      <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
    </svg>`
  }
  
  if (platformName === 'youtube') {
    return `<svg viewBox="0 0 24 24" class="h-6 w-6 text-gray-500" fill="currentColor">
      <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
    </svg>`
  }
  
  if (platformName === 'instagram') {
    return `<svg viewBox="0 0 24 24" class="h-6 w-6 text-gray-500" fill="currentColor">
      <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
    </svg>`
  }
  
  if (platformName === 'web_news') {
    return `<svg viewBox="0 0 24 24" class="h-6 w-6 text-gray-500" fill="currentColor">
      <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>
    </svg>`
  }
  
  if (platformName === 'print_magazine') {
    return `<svg viewBox="0 0 24 24" class="h-6 w-6 text-gray-500" fill="currentColor">
      <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7V9h7v8zm2-8h3v2h-3V9zm0 4h3v2h-3v-2zM7 7h10v1H7V7z"/>
    </svg>`
  }
  
  if (platformName === 'print_daily') {
    return `<svg viewBox="0 0 24 24" class="h-6 w-6 text-gray-500" fill="currentColor">
      <path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2zm-4 4H9v-2h6v2zm4-8H9V5h10v2z"/>
    </svg>`
  }
  
  return `<svg class="h-6 w-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 919-9"/>
  </svg>`
}

const formatPlatformName = (platform) => {
  const nameMap = {
    'x': 'X (Twitter)',
    'twitter': 'X (Twitter)',
    'facebook': 'Facebook',
    'youtube': 'YouTube',
    'instagram': 'Instagram',
    'web_news': 'Web News',
    'print_magazine': 'Print Magazine',
    'print_daily': 'Print Daily'
  }
  return nameMap[platform.toLowerCase()] || platform.charAt(0).toUpperCase() + platform.slice(1)
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

const getAuthorName = (post) => {
  // Try multiple possible author field names
  const possibleFields = ['author', 'username', 'user', 'handle', 'screen_name', 'author_name', 'user_name', 'created_by']
  
  for (const field of possibleFields) {
    if (post[field] && post[field] !== '' && post[field] !== 'unknown') {
      return post[field]
    }
  }
  
  // If no valid author found, return a default
  return 'unknown'
}

const getSentimentClass = (sentiment) => {
  const classes = {
    positive: 'bg-green-100 text-green-800',
    neutral: 'bg-blue-100 text-blue-800',
    negative: 'bg-red-100 text-red-800'
  }
  
  // Debug: Log sentiment values to see what we're getting
  console.log('Sentiment received:', sentiment, 'Type:', typeof sentiment)
  
  const sentimentKey = sentiment?.toLowerCase()
  const result = classes[sentimentKey] || classes.neutral
  console.log('Applied class:', result, 'for sentiment:', sentimentKey)
  
  return result
}

const handleRespond = (post) => {
  // Transform post data to match expected structure for backend API
  const authorName = getAuthorName(post)
  
  // Create a post structure that matches what the backend expects
  const transformedPost = {
    id: post.id,
    content: {
      text: post.content
    },
    author: {
      username: authorName
    },
    platform: post.platform,
    intelligence: {
      sentiment_label: post.sentiment || 'neutral',
      sentiment_score: 0 // Not available in cluster posts
    },
    engagement: {
      likes: post.engagement_metrics?.likes || 0,
      shares: post.engagement_metrics?.shares || 0,
      comments: post.engagement_metrics?.comments || 0
    },
    cluster_type: post.cluster_type || clusterType.value
  }
  
  console.log('Transformed post for response:', transformedPost)
  console.log('Author structure:', transformedPost.author)
  
  responseStore.openResponsePanel(transformedPost)
}

const getButtonText = (post) => {
  const sentiment = post.sentiment?.toLowerCase()
  const isCompetitor = post.cluster_type === 'competitor' || clusterType.value === 'competitor'
  
  // For own cluster (DMK): Always show "Respond"
  if (!isCompetitor) {
    return 'Respond'
  }
  
  // For competitor clusters: "Opportunities" only for negative posts, "Respond" for positive and neutral posts
  if (isCompetitor) {
    return sentiment === 'negative' ? 'Opportunities' : 'Respond'
  }
  
  return 'Respond'
}

const openPrintMagazineModal = (post) => {
  selectedPrintMagazine.value = post
  showPrintMagazineModal.value = true
}

const closePrintMagazineModal = () => {
  showPrintMagazineModal.value = false
  selectedPrintMagazine.value = null
}

onMounted(() => {
  fetchClusterPosts()
})
</script>

<style scoped>
.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.line-clamp-none {
  display: block;
  overflow: visible;
  white-space: pre-line;
}

.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
</style>