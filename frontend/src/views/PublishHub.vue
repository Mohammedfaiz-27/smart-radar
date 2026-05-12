<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
    <div class="mb-6">
      <h2 class="text-2xl font-bold text-gray-900">Publish Hub</h2>
      <p class="text-sm text-gray-500 mt-1">Broadcast, schedule, and track your responses across platforms</p>
    </div>

    <!-- Tabs -->
    <div class="flex space-x-1 bg-gray-100 rounded-xl p-1 mb-6 w-fit">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        @click="activeTab = tab.id"
        class="px-4 py-2 text-sm font-medium rounded-lg transition-all"
        :class="activeTab === tab.id ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'"
      >
        {{ tab.label }}
      </button>
    </div>

    <div v-if="activeTab === 'broadcast'"><BroadcastPanel /></div>
    <div v-if="activeTab === 'schedule'"><SchedulePanel /></div>
    <div v-if="activeTab === 'analytics'"><AnalyticsPanel /></div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useSmartPostStore } from '@/stores/smartpost'
import BroadcastPanel from '@/components/BroadcastPanel.vue'
import SchedulePanel from '@/components/SchedulePanel.vue'
import AnalyticsPanel from '@/components/AnalyticsPanel.vue'

const smartPostStore = useSmartPostStore()
const activeTab = ref('broadcast')

const tabs = [
  { id: 'broadcast', label: '📡 Broadcast' },
  { id: 'schedule',  label: '🗓 Schedule' },
  { id: 'analytics', label: '📊 Analytics' },
]

onMounted(() => smartPostStore.fetchSocialAccounts())
</script>
