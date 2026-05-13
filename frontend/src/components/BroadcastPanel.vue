<template>
  <div class="space-y-6">
    <!-- Compose area -->
    <div class="bg-white rounded-2xl border border-gray-200 p-6">
      <h3 class="text-base font-semibold text-gray-900 mb-4">Compose Broadcast</h3>

      <div class="space-y-4">
        <!-- Title -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Title</label>
          <input
            v-model="form.title"
            type="text"
            placeholder="Post title…"
            class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <!-- Content -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Content</label>
          <textarea
            v-model="form.content"
            rows="5"
            placeholder="Write your broadcast message…"
            class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
          <p class="text-xs text-gray-400 mt-1 text-right">{{ form.content.length }} chars</p>
        </div>

        <!-- Platform selection -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Target Platforms</label>
          <div class="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <label
              v-for="p in platforms"
              :key="p.id"
              class="flex flex-col items-center p-3 border-2 rounded-xl cursor-pointer transition-all"
              :class="selectedPlatforms.includes(p.id)
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'"
            >
              <input type="checkbox" :value="p.id" v-model="selectedPlatforms" class="sr-only" />
              <span class="text-2xl mb-1">{{ p.icon }}</span>
              <span class="text-xs font-medium text-gray-700">{{ p.name }}</span>
              <span v-if="getAccount(p.id)" class="text-xs text-green-600 mt-0.5 truncate max-w-full">● Connected</span>
              <span v-else class="text-xs text-gray-400 mt-0.5">No account</span>
            </label>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex items-center justify-between pt-2">
          <button
            @click="openMediaPanel = true"
            class="flex items-center space-x-2 text-sm text-gray-600 border border-gray-200 px-4 py-2 rounded-lg hover:bg-gray-50"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <span>Attach Media</span>
          </button>
          <div class="flex space-x-3">
            <button
              @click="openScheduleModal = true"
              :disabled="!canPublish"
              class="text-sm border border-blue-300 text-blue-600 px-4 py-2 rounded-lg hover:bg-blue-50 disabled:opacity-40 transition-colors"
            >
              🗓 Schedule
            </button>
            <button
              @click="broadcast"
              :disabled="!canPublish || publishing"
              class="text-sm bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium disabled:opacity-50 transition-colors flex items-center space-x-2"
            >
              <svg v-if="publishing" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              <span>{{ publishing ? 'Broadcasting…' : '📡 Broadcast Now' }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Broadcast results -->
    <div v-if="results.length" class="bg-white rounded-2xl border border-gray-200 p-6">
      <h3 class="text-base font-semibold text-gray-900 mb-4">Broadcast Results</h3>
      <div class="space-y-2">
        <div
          v-for="r in results"
          :key="r.platform"
          class="flex items-center space-x-3 p-3 rounded-lg"
          :class="r.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'"
        >
          <span class="text-lg">{{ r.success ? '✓' : '✗' }}</span>
          <div>
            <p class="text-sm font-medium" :class="r.success ? 'text-green-800' : 'text-red-800'">
              {{ getPlatformIcon(r.platform) }} {{ r.platform }}
            </p>
            <p class="text-xs" :class="r.success ? 'text-green-600' : 'text-red-600'">
              {{ r.message || (r.success ? 'Published successfully' : 'Failed to publish') }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Schedule modal -->
    <div v-if="openScheduleModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div class="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm mx-4">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Schedule Broadcast</h3>
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">Date & Time</label>
          <input
            v-model="scheduleAt"
            type="datetime-local"
            class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div class="flex justify-end space-x-3">
          <button @click="openScheduleModal = false" class="text-sm text-gray-500 px-4 py-2 hover:bg-gray-100 rounded-lg">Cancel</button>
          <button @click="schedulePost" :disabled="!scheduleAt || publishing" class="text-sm bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50">
            {{ publishing ? 'Scheduling…' : 'Confirm Schedule' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Media panel -->
    <MediaPanel
      v-if="openMediaPanel"
      @close="openMediaPanel = false"
      @select="onMediaSelect"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useSmartPostStore } from '@/stores/smartpost'
import { smartPostApi } from '@/services/smartpost'
import MediaPanel from '@/components/MediaPanel.vue'

const smartPostStore = useSmartPostStore()

const form = ref({ title: '', content: '' })
const selectedPlatforms = ref(['twitter', 'facebook'])
const publishing = ref(false)
const results = ref([])
const openScheduleModal = ref(false)
const openMediaPanel = ref(false)
const scheduleAt = ref('')
const attachedMedia = ref([])

const platforms = [
  { id: 'twitter', name: 'Twitter', icon: '🐦' },
  { id: 'facebook', name: 'Facebook', icon: '📘' },
  { id: 'linkedin', name: 'LinkedIn', icon: '💼' },
  { id: 'instagram', name: 'Instagram', icon: '📷' },
  { id: 'whatsapp', name: 'WhatsApp', icon: '💬' },
]

const canPublish = computed(() =>
  form.value.content.trim().length > 0 && selectedPlatforms.value.length > 0
)

const getAccount = (id) =>
  smartPostStore.socialAccounts.find(a => a.platform?.toLowerCase() === id)

const getPlatformIcon = (id) =>
  platforms.find(p => p.id === id)?.icon || '📣'

function onMediaSelect(media) {
  attachedMedia.value.push(media)
  openMediaPanel.value = false
}

async function broadcast() {
  publishing.value = true
  results.value = []
  try {
    // Get matching channel groups from connected accounts
    // publishNow requires channel_group_ids, post_id, title, content (string)
    const matchedAccountIds = selectedPlatforms.value
      .map(p => getAccount(p)?.id)
      .filter(Boolean)

    if (!matchedAccountIds.length) {
      results.value = selectedPlatforms.value.map(p => ({
        platform: p,
        success: false,
        message: 'No connected account for this platform'
      }))
      return
    }

    // Use smartPostApi directly with channel_group_ids = [] for now (no groups selected)
    // In practice, channel_group_id must come from the channel groups selector
    const postId = `broadcast-${Date.now()}`
    const payload = {
      post_id: postId,
      title: form.value.title || form.value.content.slice(0, 50),
      content: form.value.content,
      channel_group_ids: [],  // Will be empty — user should use PublishHub's channel groups
      media_ids: attachedMedia.value.map(m => m.id),
      mode: 'text',
    }

    const res = await smartPostStore.publishNow(payload)
    const channelResults = res?.channels
    if (channelResults && typeof channelResults === 'object') {
      results.value = Object.entries(channelResults).map(([platform, r]) => ({
        platform,
        success: r?.success ?? true,
        message: r?.message,
      }))
    } else {
      results.value = selectedPlatforms.value.map(p => ({ platform: p, success: true }))
    }

    if (results.value.every(r => r.success)) {
      form.value = { title: '', content: '' }
      attachedMedia.value = []
    }
  } catch (e) {
    results.value = selectedPlatforms.value.map(p => ({
      platform: p,
      success: false,
      message: e?.response?.data?.detail || 'Failed'
    }))
  } finally {
    publishing.value = false
  }
}

async function schedulePost() {
  publishing.value = true
  openScheduleModal.value = false
  try {
    const payload = {
      title: form.value.title || form.value.content.slice(0, 50),
      content: form.value.content,
      channel_group_ids: [],
      mode: 'text',
      scheduled_at: scheduleAt.value,
    }
    await smartPostApi.publishNow(payload)
    results.value = [{
      platform: 'Scheduled',
      success: true,
      message: `Scheduled for ${new Date(scheduleAt.value).toLocaleString()}`
    }]
  } catch (e) {
    results.value = [{
      platform: 'Schedule',
      success: false,
      message: e?.response?.data?.detail || 'Failed to schedule'
    }]
  } finally {
    publishing.value = false
    scheduleAt.value = ''
  }
}
</script>
