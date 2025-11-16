<template>
  <div class="flex flex-col h-full">
    <!-- Header with Threat Count -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center space-x-3">
        <div class="p-2 bg-orange-100 rounded-lg">
          <ExclamationTriangleIcon class="h-6 w-6 text-orange-600" />
        </div>
        <div>
          <h2 class="text-lg font-semibold text-gray-900">Threat Monitor</h2>
          <p class="text-sm text-gray-500">Critical security alerts</p>
        </div>
      </div>
      <div class="flex items-center text-sm">
        <span class="px-2 py-1 text-xs bg-red-100 text-red-800 rounded-full font-medium">
          {{ threats.length }} Active
        </span>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600 mx-auto"></div>
      <p class="mt-2 text-sm text-gray-500">Loading threats...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="threats.length === 0" class="text-center py-8">
      <ExclamationTriangleIcon class="h-12 w-12 text-gray-300 mx-auto mb-2" />
      <p class="text-gray-500">No threats detected</p>
    </div>

    <!-- Threats List -->
    <div v-else class="flex-1 flex flex-col">
      <div class="space-y-2 overflow-y-auto">
        <div
          v-for="threat in displayedThreats"
          :key="threat.id"
          class="border border-gray-200 rounded-xl p-3 cursor-pointer hover:bg-gray-50 hover:border-gray-300 transition-all duration-200 hover:shadow-md"
          :class="getThreatBorderColor(threat.intelligence?.threat_level)"
          @click="handleRespond(threat)"
        >
          <div class="flex items-start justify-between mb-2">
            <div class="flex items-center space-x-2 flex-1 min-w-0">
              <span 
                class="px-2 py-1 text-xs rounded-full font-medium whitespace-nowrap"
                :class="getThreatLevelClass(threat.intelligence?.threat_level)"
              >
                {{ (threat.intelligence?.threat_level || 'HIGH').toUpperCase() }}
              </span>
              <span class="text-sm font-medium text-gray-900 truncate">
                {{ getThreatTypeLabel(threat) }}
              </span>
            </div>
            <span class="text-xs text-gray-500 whitespace-nowrap ml-2">
              {{ formatDate(threat.posted_at) }}
            </span>
          </div>
          
          <p class="text-sm text-gray-700 mb-2 break-words">
            {{ threat.intelligence?.summary || threat.content || 'No description available' }}
          </p>
          
          <div class="flex items-center justify-between text-xs">
            <div class="flex items-center space-x-2 text-gray-500 flex-1 min-w-0">
              <span class="flex items-center truncate">
                <span class="text-blue-600 mr-1 truncate">@{{ threat.author || 'unknown' }}</span>
                <span class="truncate">{{ formatPlatformName(threat.platform) }}</span>
              </span>
              <span class="flex items-center whitespace-nowrap">
                <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/>
                  <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd"/>
                </svg>
                {{ formatNumber(threat.engagement_metrics?.views || threat.engagement_metrics?.likes || 0) }}
              </span>
            </div>
            
            <div class="flex items-center space-x-1 ml-2">
              <button 
                v-if="threat.url || threat.post_url"
                class="text-blue-600 hover:text-blue-800 font-medium text-xs whitespace-nowrap flex items-center"
                @click.stop="openSourceLink(threat)"
                title="View original post"
              >
                <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                </svg>
                Source
              </button>
              <button 
                class="text-red-600 hover:text-red-800 font-medium text-xs whitespace-nowrap"
                @click.stop="handleRespond(threat)"
              >
                {{ getButtonText(threat) }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Load More Button - Always at bottom -->
      <div v-if="threats.length > maxDisplayedThreats" class="mt-4 flex-shrink-0">
        <button
          @click="showAllThreatsModal"
          class="w-full py-3 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors flex items-center justify-center space-x-2"
        >
          <ExclamationTriangleIcon class="h-4 w-4" />
          <span>View All {{ threats.length }} Threats</span>
        </button>
      </div>
    </div>

    <!-- All Threats Modal -->
    <div v-if="showModal" class="fixed inset-0 z-50 overflow-y-auto" @click="closeModal">
      <div class="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <!-- Background overlay -->
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"></div>
        
        <!-- Modal panel -->
        <div class="inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full sm:p-6" @click.stop>
          <!-- Modal Header -->
          <div class="flex items-center justify-between mb-6">
            <div class="flex items-center space-x-3">
              <div class="p-2 bg-orange-100 rounded-lg">
                <ExclamationTriangleIcon class="h-6 w-6 text-orange-600" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-gray-900">All Active Threats</h3>
                <p class="text-sm text-gray-500">{{ threats.length }} security alerts require attention</p>
              </div>
            </div>
            <button @click="closeModal" class="text-gray-400 hover:text-gray-600">
              <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <!-- Modal Content -->
          <div class="max-h-96 overflow-y-auto space-y-3">
            <div 
              v-for="threat in threats" 
              :key="threat.id"
              class="border border-gray-200 rounded-xl p-3 cursor-pointer hover:bg-gray-50 hover:border-gray-300 transition-all duration-200 hover:shadow-md"
              :class="getThreatBorderColor(threat.intelligence?.threat_level)"
              @click="handleThreatClick(threat)"
            >
              <div class="flex items-start justify-between mb-2">
                <div class="flex items-center space-x-2 flex-1 min-w-0">
                  <span 
                    class="px-2 py-1 text-xs rounded-full font-medium whitespace-nowrap"
                    :class="getThreatLevelClass(threat.intelligence?.threat_level)"
                  >
                    {{ (threat.intelligence?.threat_level || 'HIGH').toUpperCase() }}
                  </span>
                  <span class="text-sm font-medium text-gray-900 truncate">
                    {{ getThreatTypeLabel(threat) }}
                  </span>
                </div>
                <span class="text-xs text-gray-500 whitespace-nowrap ml-2">
                  {{ formatDate(threat.posted_at) }}
                </span>
              </div>
              
              <p class="text-sm text-gray-700 mb-2 break-words">
                {{ threat.intelligence?.summary || threat.content || 'No description available' }}
              </p>
              
              <div class="flex items-center justify-between text-xs">
                <div class="flex items-center space-x-2 text-gray-500 flex-1 min-w-0">
                  <span class="flex items-center truncate">
                    <span class="text-blue-600 mr-1 truncate">@{{ threat.author || 'unknown' }}</span>
                    <span class="truncate">{{ formatPlatformName(threat.platform) }}</span>
                  </span>
                  <span class="flex items-center whitespace-nowrap">
                    <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/>
                      <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd"/>
                    </svg>
                    {{ formatNumber(threat.engagement_metrics?.views || threat.engagement_metrics?.likes || 0) }}
                  </span>
                </div>
                
                <div class="flex items-center space-x-1 ml-2">
                  <button 
                    v-if="threat.url || threat.post_url"
                    class="text-blue-600 hover:text-blue-800 font-medium text-xs whitespace-nowrap flex items-center"
                    @click.stop="openSourceLink(threat)"
                    title="View original post"
                  >
                    <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                    </svg>
                    Source
                  </button>
                  <button 
                    class="text-red-600 hover:text-red-800 font-medium text-xs whitespace-nowrap"
                    @click.stop="handleThreatClick(threat)"
                  >
                    {{ getButtonText(threat) }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import { usePostsStore } from '@/stores/posts'
import { useResponseStore } from '@/stores/response'

const postsStore = usePostsStore()
const responseStore = useResponseStore()

const threats = ref([])
const loading = ref(false)
const maxDisplayedThreats = ref(6) // Limit to 6 threats to match sentiment column height
const showModal = ref(false)

const displayedThreats = computed(() => {
  return threats.value.slice(0, maxDisplayedThreats.value)
})

const refreshThreats = async () => {
  loading.value = true
  try {
    // Fetch all posts first
    await postsStore.fetchPosts()
    
    // Get threat posts from the store - only own organization threats
    const threatPosts = await postsStore.fetchThreats({ cluster_type: 'own' })
    
    // Also check existing posts for threats based on intelligence data
    const allPosts = postsStore.posts
    const additionalThreats = allPosts.filter(post => {
      // Check if post has high threat level or negative sentiment for own organization
      const hasHighThreat = post.intelligence?.threat_level === 'high' || 
                           post.intelligence?.threat_level === 'critical'
      
      // Check if it's negative sentiment about own organization
      const hasNegativeSentiment = post.cluster_type === 'own' && 
                                  (post.sentiment === 'negative' ||
                                   Object.values(post.intelligence?.entity_sentiments || {})
                                     .some(s => s.label === 'Negative' || s.label === 'negative'))
      
      return hasHighThreat || hasNegativeSentiment
    })
    
    // Combine and deduplicate threats
    const allThreats = [...threatPosts, ...additionalThreats]
    const uniqueThreats = allThreats.filter((threat, index, self) => 
      index === self.findIndex(t => t.id === threat.id)
    )
    
    threats.value = uniqueThreats
    console.log('📊 Loaded', threats.value.length, 'threats')
    
  } catch (error) {
    console.error('Failed to fetch threats:', error)
    // Fallback to threat posts from store
    threats.value = postsStore.threatPosts || []
  } finally {
    loading.value = false
  }
}

const handleRespond = (threat) => {
  responseStore.openResponsePanel(threat)
}

const handleAnalyze = (threat) => {
  // TODO: Implement analyze functionality
  console.log('Analyzing threat:', threat.id)
}

const handleMonitor = (threat) => {
  // TODO: Implement monitor functionality
  console.log('Monitoring threat:', threat.id)
}

const getButtonText = (threat) => {
  const sentiment = threat.intelligence?.sentiment_label?.toLowerCase()
  const isCompetitor = threat.cluster_type === 'competitor'
  const isNegative = sentiment === 'negative'
  
  // Show "Opportunities" for competitor negative posts
  if (isCompetitor && isNegative) {
    return 'Opportunities'
  }
  
  return 'Respond'
}

const showAllThreatsModal = () => {
  showModal.value = true
}

const closeModal = () => {
  showModal.value = false
}

const handleThreatClick = (threat) => {
  closeModal()
  handleRespond(threat)
}

const getThreatLevelClass = (level) => {
  const levelClasses = {
    critical: 'bg-red-100 text-red-800',
    high: 'bg-red-100 text-red-800',
    medium: 'bg-orange-100 text-orange-800',
    low: 'bg-yellow-100 text-yellow-800'
  }
  return levelClasses[level?.toLowerCase()] || 'bg-red-100 text-red-800'
}

const getThreatBorderColor = (level) => {
  const borderClasses = {
    critical: 'border-l-4 border-l-red-500',
    high: 'border-l-4 border-l-red-500',
    medium: 'border-l-4 border-l-orange-500',
    low: 'border-l-4 border-l-yellow-500'
  }
  return borderClasses[level?.toLowerCase()] || 'border-l-4 border-l-red-500'
}

const getThreatTypeLabel = (threat) => {
  // Generate a threat type based on content or intelligence
  if (threat.intelligence?.campaign_type) {
    return threat.intelligence.campaign_type
  }
  
  // Fallback labels based on content
  if (threat.content?.toLowerCase().includes('campaign')) {
    return 'Viral Campaign'
  }
  if (threat.content?.toLowerCase().includes('news') || threat.content?.toLowerCase().includes('article')) {
    return 'News Article'
  }
  if (threat.author?.toLowerCase().includes('influencer') || threat.engagement_metrics?.followers > 10000) {
    return 'Influencer Post'
  }
  
  return 'Social Media Post'
}

const formatPlatformName = (platform) => {
  const platformNames = {
    'x': 'X (Twitter)',
    'twitter': 'X (Twitter)',
    'facebook': 'Facebook',
    'instagram': 'Instagram',
    'youtube': 'YouTube'
  }
  return platformNames[platform?.toLowerCase()] || platform
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
  
  if (minutes < 60) return `${minutes}h ago`
  if (hours < 24) return `${hours}h ago`
  if (days < 7) return `${days}h ago`
  
  return `${hours}h ago`
}

const openSourceLink = (threat) => {
  const url = threat.url || threat.post_url
  if (url) {
    window.open(url, '_blank', 'noopener,noreferrer')
  }
}

onMounted(() => {
  refreshThreats()
})
</script>

<style scoped>
.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>