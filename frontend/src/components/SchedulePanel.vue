<template>
  <div class="space-y-6">
    <div class="bg-white rounded-2xl border border-gray-200 p-6">
      <div class="flex items-center justify-between mb-5">
        <h3 class="text-base font-semibold text-gray-900">Content Calendar</h3>
        <button @click="loadCalendar" class="text-sm text-gray-500 hover:text-gray-700">
          <svg class="w-4 h-4" :class="loading && 'animate-spin'" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="space-y-3">
        <div v-for="i in 4" :key="i" class="h-16 bg-gray-50 rounded-xl animate-pulse"></div>
      </div>

      <!-- Empty -->
      <div v-else-if="items.length === 0" class="py-12 text-center">
        <div class="text-4xl mb-3">🗓</div>
        <p class="text-gray-500 font-medium">No scheduled posts</p>
        <p class="text-sm text-gray-400 mt-1">Use the Broadcast tab to schedule posts</p>
      </div>

      <!-- Calendar items -->
      <div v-else class="space-y-3">
        <div
          v-for="item in items"
          :key="item.id"
          class="flex items-start space-x-4 p-4 bg-gray-50 rounded-xl"
        >
          <!-- Date block -->
          <div class="bg-blue-600 text-white rounded-lg p-2 text-center min-w-12 flex-shrink-0">
            <div class="text-xs font-medium">{{ formatMonth(item.scheduled_at) }}</div>
            <div class="text-xl font-bold leading-none">{{ formatDay(item.scheduled_at) }}</div>
          </div>

          <div class="flex-1 min-w-0">
            <div class="flex items-center space-x-2 mb-1">
              <span class="text-sm font-medium text-gray-900 truncate">{{ item.title || 'Untitled' }}</span>
              <span class="text-xs text-gray-400">{{ formatTime(item.scheduled_at) }}</span>
            </div>
            <p class="text-xs text-gray-500 line-clamp-2">{{ item.content?.text || item.content || '' }}</p>
            <div v-if="item.channels?.length" class="flex items-center space-x-1 mt-1">
              <span v-for="ch in item.channels" :key="ch.platform" class="text-xs">
                {{ getPlatformIcon(ch.platform) }}
              </span>
            </div>
          </div>

          <div class="flex-shrink-0">
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
              :class="getStatusClass(item.status)">
              {{ item.status || 'scheduled' }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { smartPostApi } from '@/services/smartpost'

const loading = ref(false)
const items = ref([])

const platformIcons = { twitter: '🐦', facebook: '📘', linkedin: '💼', instagram: '📷', whatsapp: '💬' }
const getPlatformIcon = (id) => platformIcons[id] || '📣'

const formatMonth = (d) => d ? new Date(d).toLocaleDateString('en', { month: 'short' }) : ''
const formatDay = (d) => d ? new Date(d).getDate() : ''
const formatTime = (d) => d ? new Date(d).toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' }) : ''

const getStatusClass = (status) => {
  const map = {
    scheduled: 'bg-blue-100 text-blue-800',
    published: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    draft: 'bg-gray-100 text-gray-700',
  }
  return map[status] || map.draft
}

async function loadCalendar() {
  loading.value = true
  try {
    const res = await smartPostApi.getCalendar()
    items.value = res.data?.items || res.data || []
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadCalendar)
</script>
