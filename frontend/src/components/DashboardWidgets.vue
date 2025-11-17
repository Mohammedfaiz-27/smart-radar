<template>
  <div :class="[
    'grid grid-cols-1 gap-4 mb-6',
    hasCompetitorClusters ? 'md:grid-cols-2 lg:grid-cols-4' : 'md:grid-cols-3 lg:grid-cols-3'
  ]">
    <!-- Posts Today Widget -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm font-medium text-gray-600">Total Posts</p>
          <p class="text-2xl font-bold text-gray-900">{{ stats.posts_today }}</p>
        </div>
        <div class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
          <svg class="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 4V2a1 1 0 011-1h8a1 1 0 011 1v2m4 0H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V6a2 2 0 00-2-2z" />
          </svg>
        </div>
      </div>
      <div class="mt-4 flex items-center">
        <span class="text-xs text-blue-600 font-medium">
          📊 Total
        </span>
        <span class="text-xs text-gray-500 ml-2">All-time posts count</span>
      </div>
    </div>

    <!-- Positive Posts Widget -->
    <div
      class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 cursor-pointer hover:shadow-md transition-shadow"
      @click="openModal('positive')"
    >
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm font-medium text-gray-600">Positive Posts</p>
          <p class="text-2xl font-bold text-gray-900">{{ stats.positive_posts }}</p>
        </div>
        <div class="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
          <svg class="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h8m-5-9V3m0 18v-2" />
          </svg>
        </div>
      </div>
      <div class="mt-4 flex items-center">
        <span class="text-xs text-green-600 font-medium">
          ↗ {{ getPositivePercentage() }}%
        </span>
        <span class="text-xs text-gray-500 ml-2">of total sentiment</span>
      </div>
    </div>

    <!-- Negative Posts Widget -->
    <div
      class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 cursor-pointer hover:shadow-md transition-shadow"
      @click="openModal('negative')"
    >
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm font-medium text-gray-600">Negative Posts</p>
          <p class="text-2xl font-bold text-gray-900">{{ stats.negative_posts }}</p>
        </div>
        <div class="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center">
          <svg class="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
      </div>
      <div class="mt-4 flex items-center">
        <span class="text-xs text-red-600 font-medium">
          ↗ {{ getNegativePercentage() }}%
        </span>
        <span class="text-xs text-gray-500 ml-2">require attention</span>
      </div>
    </div>

    <!-- Opportunities Widget - Only show if competitor clusters exist -->
    <div
      v-if="hasCompetitorClusters"
      class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 cursor-pointer hover:shadow-md transition-shadow"
      @click="openModal('opportunities')"
    >
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm font-medium text-gray-600">Opportunities</p>
          <p class="text-2xl font-bold text-gray-900">{{ stats.opportunities }}</p>
        </div>
        <div class="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
          <svg class="w-6 h-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
        </div>
      </div>
      <div class="mt-4 flex items-center">
        <span class="text-xs text-purple-600 font-medium">
          ↗ Competitor trends
        </span>
        <span class="text-xs text-gray-500 ml-2">negative sentiment</span>
      </div>
    </div>
  </div>

  <!-- Widget Details Modal -->
  <WidgetDetailsModal 
    :is-open="modalState.isOpen"
    :widget-type="modalState.widgetType"
    @close="closeModal"
  />
</template>

<script setup>
import { ref, onMounted, computed, reactive } from 'vue'
import WidgetDetailsModal from './WidgetDetailsModal.vue'
import { usePostsStore } from '@/stores/posts'
import { useClustersStore } from '@/stores/clusters'

// Initialize stores
const postsStore = usePostsStore()
const clustersStore = useClustersStore()

// Check if competitor clusters exist
const hasCompetitorClusters = computed(() => clustersStore.competitorClusters.length > 0)

// Stats data
const stats = ref({
  posts_today: 0,
  positive_posts: 0,
  negative_posts: 0,
  opportunities: 0
})

// Loading state
const loading = ref(true)

// Modal state
const modalState = reactive({
  isOpen: false,
  widgetType: ''
})

// Computed percentages
const getPositivePercentage = () => {
  const total = stats.value.positive_posts + stats.value.negative_posts
  if (total === 0) return 0
  return Math.round((stats.value.positive_posts / total) * 100)
}

const getNegativePercentage = () => {
  const total = stats.value.positive_posts + stats.value.negative_posts
  if (total === 0) return 0
  return Math.round((stats.value.negative_posts / total) * 100)
}

// Fetch dashboard statistics
const fetchDashboardStats = async () => {
  try {
    loading.value = true
    
    // Always calculate from posts data for accurate results
    await postsStore.fetchPosts()
    
    const posts = postsStore.posts
    const ownPosts = postsStore.ownPosts
    const competitorPosts = postsStore.competitorPosts
    const threatPosts = postsStore.threatPosts
    
    console.log('📊 Calculating dashboard stats from', posts.length, 'posts')
    console.log('📊 Own posts:', ownPosts.length, 'Competitor posts:', competitorPosts.length, 'Threat posts:', threatPosts.length)
    
    // Calculate sentiment metrics from posts_table sentiment field
    let positiveCount = 0
    let negativeCount = 0
    let opportunitiesCount = 0
    
    posts.forEach(post => {
      // Use direct sentiment field from posts_table
      const sentiment = post.sentiment || 'neutral'
      
      // Count own cluster sentiments (for positive/negative widgets)
      if (post.cluster_type === 'own') {
        if (sentiment === 'positive') {
          positiveCount++
        } else if (sentiment === 'negative') {
          negativeCount++
        }
      }
      
      // Count opportunities (competitor negative sentiment)
      if (post.cluster_type === 'competitor' && sentiment === 'negative') {
        opportunitiesCount++
      }
    })
    
    stats.value = {
      posts_today: posts.length,
      positive_posts: positiveCount,
      negative_posts: negativeCount,
      opportunities: opportunitiesCount,
      own_posts: ownPosts.length,
      competitor_posts: competitorPosts.length,
      threat_posts: threatPosts.length
    }
    
    console.log('📊 Dashboard stats calculated:', stats.value)
    
  } catch (error) {
    console.error('Error fetching dashboard stats:', error)
    stats.value = {
      posts_today: 0,
      positive_posts: 0,
      negative_posts: 0,
      opportunities: 0,
      own_posts: 0,
      competitor_posts: 0,
      threat_posts: 0
    }
  } finally {
    loading.value = false
  }
}

// Modal functions
const openModal = (widgetType) => {
  modalState.isOpen = true
  modalState.widgetType = widgetType
}

const closeModal = () => {
  modalState.isOpen = false
  modalState.widgetType = ''
}

// Initialize on mount
onMounted(() => {
  fetchDashboardStats()
  
  // Refresh stats every 30 seconds
  const interval = setInterval(fetchDashboardStats, 30000)
  
  // Cleanup interval on unmount
  return () => clearInterval(interval)
})
</script>