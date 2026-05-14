<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-gray-900">Content Calendar</h2>
        <p class="text-sm text-gray-600 mt-1">View and manage your scheduled content</p>
      </div>
      <router-link
        to="/post-creator"
        class="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg shadow-sm transition-colors"
      >
        <svg class="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        Schedule Post
      </router-link>
    </div>

    <!-- Calendar placeholder -->
    <div class="bg-white rounded-lg shadow p-8 text-center border border-gray-200">
      <div class="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg class="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
        </svg>
      </div>
      <h3 class="text-lg font-semibold text-gray-900 mb-2">Visual Calendar Coming Soon</h3>
      <p class="text-gray-600 text-sm mb-6">Your scheduled content will appear here in a visual calendar format.</p>
      <router-link
        to="/post-creator"
        class="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md transition-colors"
      >
        <svg class="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        Schedule Your First Post
      </router-link>
    </div>

    <!-- Summary Stats -->
    <div v-if="summary" class="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-5 text-center">
        <p class="text-2xl font-bold text-gray-900">{{ summary.total_posts }}</p>
        <p class="text-xs text-gray-500 mt-1">Total Posts</p>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-5 text-center">
        <p class="text-2xl font-bold text-blue-600">{{ summary.scheduled }}</p>
        <p class="text-xs text-gray-500 mt-1">Scheduled</p>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-5 text-center">
        <p class="text-2xl font-bold text-green-600">{{ summary.published }}</p>
        <p class="text-xs text-gray-500 mt-1">Published</p>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-5 text-center">
        <p class="text-2xl font-bold text-red-600">{{ summary.failed }}</p>
        <p class="text-xs text-gray-500 mt-1">Failed</p>
      </div>
    </div>

    <!-- Upcoming Posts -->
    <div class="bg-white rounded-lg shadow border border-gray-200">
      <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <h3 class="text-base font-semibold text-gray-900">Upcoming Scheduled Posts</h3>
        <button @click="load" class="text-xs text-blue-600 hover:underline flex items-center space-x-1">
          <svg class="w-3 h-3" :class="loading && 'animate-spin'" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
          <span>Refresh</span>
        </button>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="p-8 text-center">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p class="mt-2 text-sm text-gray-600">Loading calendar...</p>
      </div>

      <!-- Empty -->
      <div v-else-if="scheduledPosts.length === 0" class="p-8 text-center">
        <svg class="mx-auto h-12 w-12 text-gray-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
        </svg>
        <p class="text-gray-500 text-sm">No scheduled posts yet.</p>
      </div>

      <!-- Posts list -->
      <div v-else class="divide-y divide-gray-200">
        <div
          v-for="post in scheduledPosts"
          :key="post.id"
          class="p-6 hover:bg-gray-50 transition-colors"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1 min-w-0">
              <h4 class="text-sm font-semibold text-gray-900 truncate">{{ post.title || 'Untitled' }}</h4>
              <p class="text-sm text-gray-600 mt-1 line-clamp-2">{{ post.content?.text || post.content || '' }}</p>
              <div class="mt-2 flex items-center space-x-3 text-xs text-gray-500">
                <span class="flex items-center space-x-1">
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                  </svg>
                  <span>{{ formatDate(post.scheduled_at) }}</span>
                </span>
                <span v-if="post.platforms?.length" class="flex items-center space-x-1">
                  <span v-for="p in post.platforms" :key="p">{{ getPlatformIcon(p) }}</span>
                </span>
                <span v-else-if="post.channels?.length" class="flex items-center space-x-1">
                  <span v-for="c in post.channels" :key="c.platform">{{ getPlatformIcon(c.platform) }}</span>
                </span>
              </div>
            </div>
            <span
              class="ml-4 flex-shrink-0 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize"
              :class="{
                'bg-blue-100 text-blue-800': post.status === 'scheduled',
                'bg-gray-100 text-gray-800': post.status === 'draft',
                'bg-green-100 text-green-800': post.status === 'published',
                'bg-red-100 text-red-800': post.status === 'failed',
              }"
            >{{ post.status || 'scheduled' }}</span>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { smartPostApi } from '@/services/smartpost'

const loading = ref(false)
const calendarData = ref(null)

const platformIcons = { twitter: '🐦', facebook: '📘', linkedin: '💼', instagram: '📷', whatsapp: '💬' }
const getPlatformIcon = (id) => platformIcons[id?.toLowerCase()] || '📣'

const summary = computed(() => calendarData.value?.summary ?? null)

const scheduledPosts = computed(() => {
  if (!calendarData.value) return []
  const events = calendarData.value.events ?? calendarData.value.items ?? (Array.isArray(calendarData.value) ? calendarData.value : [])
  return events
    .filter(e => e.scheduled_at || e.status === 'scheduled')
    .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))
})

const formatDate = (d) => {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

async function load() {
  loading.value = true
  try {
    const res = await smartPostApi.getCalendar()
    calendarData.value = res.data
  } catch {
    calendarData.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
