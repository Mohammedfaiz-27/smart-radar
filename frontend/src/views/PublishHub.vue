<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
    <div class="mb-6">
      <h2 class="text-2xl font-bold text-gray-900">Publish Hub</h2>
      <p class="text-sm text-gray-500 mt-1">Broadcast, schedule, and track your responses across platforms</p>
    </div>

    <div class="flex items-center justify-between mb-6">
      <div class="flex flex-wrap gap-1 bg-gray-100 rounded-xl p-1 w-fit">
        <button
          v-for="tab in tabs" :key="tab.id"
          @click="activeTab = tab.id"
          class="px-4 py-2 text-sm font-medium rounded-lg transition-all"
          :class="activeTab === tab.id ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'"
        >{{ tab.label }}</button>
      </div>
    </div>

    <div v-if="activeTab === 'broadcast'"><BroadcastPanel /></div>
    <div v-if="activeTab === 'schedule'"><SchedulePanel /></div>
    <div v-if="activeTab === 'analytics'"><AnalyticsPanel /></div>
    <div v-if="activeTab === 'channel-groups'"><ChannelGroupsPanel /></div>
    <div v-if="activeTab === 'workflows'"><WorkflowsPanel /></div>
    <div v-if="activeTab === 'media'"><MediaPanel /></div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useSmartPostStore } from '@/stores/smartpost'
import BroadcastPanel from '@/components/BroadcastPanel.vue'
import SchedulePanel from '@/components/SchedulePanel.vue'
import AnalyticsPanel from '@/components/AnalyticsPanel.vue'
import ChannelGroupsPanel from '@/components/ChannelGroupsPanel.vue'
import WorkflowsPanel from '@/components/WorkflowsPanel.vue'
import MediaPanel from '@/components/MediaPanel.vue'

const store = useSmartPostStore()
const activeTab = ref('broadcast')

const tabs = [
  { id: 'broadcast',      label: '📡 Broadcast' },
  { id: 'schedule',       label: '🗓 Schedule' },
  { id: 'analytics',      label: '📊 Analytics' },
  { id: 'channel-groups', label: '📣 Channels' },
  { id: 'workflows',      label: '⚙️ Workflows' },
  { id: 'media',          label: '🖼 Media' },
]

onMounted(() => { store.fetchSocialAccounts() })
</script>
