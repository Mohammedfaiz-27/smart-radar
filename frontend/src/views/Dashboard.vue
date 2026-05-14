<template>
  <div>
    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">


      <!-- Dashboard Widgets -->
      <DashboardWidgets />
      
      <!-- Dashboard Layout - Dynamic Grid with Equal Heights -->
      <div :class="[
        'grid grid-cols-1 gap-6 mb-8 lg:grid-rows-1',
        competitorClusters.length > 0 ? 'lg:grid-cols-3' : 'lg:grid-cols-2'
      ]">
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

        <!-- Competitor Sentiment Analysis - Only show if competitor clusters exist -->
        <div
          v-if="competitorClusters.length > 0"
          class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 flex flex-col"
        >
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
import { reactive, computed, ref } from 'vue'
import { usePostsStore } from '@/stores/posts'
import { useClustersStore } from '@/stores/clusters'
import ThreatAlerts from '@/components/ThreatAlerts.vue'
import PlatformDataModal from '@/components/PlatformDataModal.vue'
import SentimentAnalysis from '@/components/SentimentAnalysis.vue'
import DashboardWidgets from '@/components/DashboardWidgets.vue'

const postsStore = usePostsStore()
const clustersStore = useClustersStore()

// Manual collection trigger
const collectStatus = ref('idle')  // idle | running | done | error
const collectResult = ref('')
const collectStatusText = computed(() => {
  if (collectStatus.value === 'running') return 'Fetching latest posts from all clusters…'
  if (collectStatus.value === 'done') return 'Collection complete — refresh feed to see new posts'
  if (collectStatus.value === 'error') return 'Collection failed — check backend logs'
  return 'Manually trigger a full data collection run across all active clusters'
})

async function triggerCollectAll() {
  const clusters = clustersStore.activeClusters
  if (!clusters.length) {
    collectResult.value = 'No active clusters'
    return
  }
  collectStatus.value = 'running'
  collectResult.value = ''
  try {
    const ids = clusters.map(c => c.id)
    const apiBase = import.meta.env.VITE_API_URL || ''
    const res = await fetch(`${apiBase}/api/v1/collection/collect/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cluster_ids: ids })
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw { response: { data: err } }
    }
    const results = await res.json()
    const total = results.reduce((sum, r) => sum + (r.collected_posts || 0), 0)
    collectResult.value = `${total} new posts collected`
    collectStatus.value = 'done'
    // Refresh the feed
    await postsStore.fetchPosts()
  } catch (e) {
    collectStatus.value = 'error'
    collectResult.value = e.response?.data?.detail || 'Error'
  }
}

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