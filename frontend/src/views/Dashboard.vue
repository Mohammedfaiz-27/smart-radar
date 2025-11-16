<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm">
      <div class="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
        <!-- Main Header Row -->
        <div class="flex justify-between items-center py-6">
          <!-- Left Section: Logo and Status Indicators -->
          <div class="flex flex-col space-y-4">
            <!-- Smart Radar Logo with Status Toggle -->
            <div class="flex items-center space-x-4">
              <div class="w-14 h-14 bg-blue-600 rounded-full flex items-center justify-center shadow-lg">
                <svg class="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h1 class="text-4xl font-black text-gray-900 tracking-tight">SMART RADAR</h1>
              
              <!-- Status Toggle integrated with logo -->
              <div class="relative bg-green-500 hover:bg-green-600 transition-all duration-300 rounded-full px-4 py-2 shadow-lg animate-pulse ml-6" style="animation-duration: 2s; box-shadow: 0 0 20px rgba(34, 197, 94, 0.4), 0 0 40px rgba(34, 197, 94, 0.2);">
                <div class="w-4 h-4 bg-white rounded-full relative z-10"></div>
                <!-- Slow waving effect -->
                <div class="absolute inset-0 rounded-full bg-green-400 opacity-30 animate-ping" style="animation-duration: 3s;"></div>
              </div>
            </div>

            <!-- Status Indicators with Dots and Text in Left Bottom -->
            <div class="flex items-center space-x-6 ml-18">
              <div class="flex items-center space-x-1">
                <div class="w-2.5 h-2.5 bg-blue-500 rounded-full shadow-lg" style="box-shadow: 0 0 8px rgba(59, 130, 246, 0.6);"></div>
                <span class="text-xs font-semibold text-gray-700">Digital Command Center</span>
              </div>
              <div class="flex items-center space-x-1">
                <div class="w-2.5 h-2.5 bg-orange-500 rounded-full shadow-lg animate-pulse" style="box-shadow: 0 0 8px rgba(249, 115, 22, 0.6);"></div>
                <span class="text-xs font-semibold text-gray-700">{{ postsStore.threatPosts.length }} Active Threats</span>
              </div>
              <div class="flex items-center space-x-1">
                <div class="w-2.5 h-2.5 bg-green-500 rounded-full shadow-lg animate-pulse" style="box-shadow: 0 0 8px rgba(34, 197, 94, 0.6);"></div>
                <span class="text-xs font-semibold text-gray-700">Real-time Intelligence</span>
              </div>
            </div>
          </div>


          <!-- Right Section: System Time and Navigation -->
          <div class="flex flex-col items-end space-y-4">
            <!-- System Time -->
            <div class="text-right">
              <div class="text-sm text-gray-500 font-medium">System Time</div>
              <div class="text-xl font-bold text-gray-900">{{ currentTime }}</div>
              <div class="flex items-center justify-end space-x-2 mt-1">
                <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse" style="box-shadow: 0 0 6px rgba(34, 197, 94, 0.6);"></div>
                <span class="text-sm text-green-600 font-semibold">Live Monitoring</span>
              </div>
            </div>

            <!-- Navigation Tabs with Icons -->
            <nav class="flex space-x-6">
              <router-link 
                to="/" 
                class="flex items-center space-x-2 text-sm font-medium text-blue-600 border-b-2 border-blue-600 pb-1"
              >
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5a2 2 0 012-2h4a2 2 0 012 2v6H8V5z" />
                </svg>
                <span>Dashboard</span>
              </router-link>
              <router-link 
                to="/clusters" 
                class="flex items-center space-x-2 text-sm font-medium text-gray-500 hover:text-gray-700 pb-1"
              >
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
                <span>Clusters</span>
              </router-link>
              <router-link 
                to="/narratives" 
                class="flex items-center space-x-2 text-sm font-medium text-gray-500 hover:text-gray-700 pb-1"
              >
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>Narratives</span>
              </router-link>
            </nav>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <!-- Dashboard Widgets -->
      <DashboardWidgets />
      
      <!-- Dashboard Layout - 3 Column Grid with Equal Heights -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8 lg:grid-rows-1">
        <!-- Threat Monitor -->
        <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 flex flex-col">
          <ThreatAlerts class="flex-1" />
        </div>

        <!-- Own Sentiment Analysis -->
        <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 flex flex-col">
          <!-- Header -->
          <div class="flex items-center justify-between mb-6">
            <div>
              <h3 class="text-lg font-semibold text-gray-900">
                <span class="bg-blue-100 text-blue-800 px-2 py-1 rounded font-bold">Own</span> sentiment
              </h3>
              <p class="text-xs text-gray-500 mt-1">Organization sentiment analysis</p>
            </div>
            <span class="px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full font-medium">
              ↗ 3.2%
            </span>
          </div>
          
          <!-- Own sentiment breakdown -->
          <SentimentAnalysis 
            type="own"
            title="Organization"
            @openPlatformModal="openModal"
          />
        </div>

        <!-- Competitor Sentiment Analysis -->
        <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 flex flex-col">
          <!-- Header -->
          <div class="flex items-center justify-between mb-6">
            <div>
              <h3 class="text-lg font-semibold text-gray-900">
                <span class="bg-orange-100 text-orange-800 px-2 py-1 rounded font-bold">Competitor</span> sentiment
              </h3>
              <p class="text-xs text-gray-500 mt-1">Competitor sentiment analysis</p>
            </div>
            <span class="px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full font-medium">
              ↗ 3.2%
            </span>
          </div>
          
          <!-- Competitor sentiment breakdown -->
          <SentimentAnalysis 
            type="competitors"
            title="Competitors"
            @openPlatformModal="openModal"
          />
        </div>
      </div>

    </main>

    <!-- Response Panel Modal -->
    <ResponsePanel />

    <!-- Platform Data Modal -->
    <PlatformDataModal 
      :is-open="modalState.isOpen"
      :title="modalState.title"
      :posts="modalState.posts"
      :platform="modalState.platform"
      :loading="postsStore.loading"
      @close="closeModal"
    />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, onUnmounted, computed } from 'vue'
import { usePostsStore } from '@/stores/posts'
import { useClustersStore } from '@/stores/clusters'
import ThreatAlerts from '@/components/ThreatAlerts.vue'
import ResponsePanel from '@/components/ResponsePanel.vue'
import PlatformDataModal from '@/components/PlatformDataModal.vue'
import SentimentAnalysis from '@/components/SentimentAnalysis.vue'
import DashboardWidgets from '@/components/DashboardWidgets.vue'

const postsStore = usePostsStore()
const clustersStore = useClustersStore()

// Use cluster store computed properties
const ownClusters = computed(() => clustersStore.ownClusters)
const competitorClusters = computed(() => clustersStore.competitorClusters)

// Current time for header
const currentTime = ref('')
let timeInterval = null

const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('en-US', { 
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// Modal state
const modalState = reactive({
  isOpen: false,
  title: '',
  posts: [],
  platform: ''
})

const openModal = (modalData) => {
  modalState.isOpen = true
  modalState.title = modalData.title
  modalState.posts = modalData.posts
  modalState.platform = modalData.platform
}

const closeModal = () => {
  modalState.isOpen = false
  modalState.title = ''
  modalState.posts = []
  modalState.platform = ''
}

// Initialize cluster-based data loading
const initializeClusterData = async () => {
  try {
    console.log('🔄 Initializing cluster-based data...')
    
    // First load clusters
    await clustersStore.fetchClusters()
    
    // Then load posts with cluster filtering
    await postsStore.fetchPosts()
    
    console.log('✅ Cluster data initialized')
    console.log('Own clusters:', ownClusters.value.length)
    console.log('Competitor clusters:', competitorClusters.value.length)
    console.log('Total posts loaded:', postsStore.posts.length)
    
    // Log cluster keywords for debugging
    ownClusters.value.forEach(cluster => {
      console.log(`📊 Own cluster "${cluster.name}" keywords:`, cluster.keywords)
    })
    
    competitorClusters.value.forEach(cluster => {
      console.log(`📊 Competitor cluster "${cluster.name}" keywords:`, cluster.keywords)
    })
    
  } catch (error) {
    console.error('❌ Error initializing cluster data:', error)
  }
}

onMounted(async () => {
  // Initialize time and start timer
  updateTime()
  timeInterval = setInterval(updateTime, 1000)
  
  // Load cluster-based data
  await initializeClusterData()
})

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval)
  }
})
</script>