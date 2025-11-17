<template>
  <div>
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
import { reactive, computed } from 'vue'
import { usePostsStore } from '@/stores/posts'
import { useClustersStore } from '@/stores/clusters'
import ThreatAlerts from '@/components/ThreatAlerts.vue'
import PlatformDataModal from '@/components/PlatformDataModal.vue'
import SentimentAnalysis from '@/components/SentimentAnalysis.vue'
import DashboardWidgets from '@/components/DashboardWidgets.vue'

const postsStore = usePostsStore()
const clustersStore = useClustersStore()

// Use cluster store computed properties
const ownClusters = computed(() => clustersStore.ownClusters)
const competitorClusters = computed(() => clustersStore.competitorClusters)

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

// Data is already loaded by MainLayout, no need to fetch again
// The stores will use cached data when components mount
</script>