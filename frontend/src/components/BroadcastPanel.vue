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
          <div v-if="loadingAccounts" class="text-sm text-gray-400 py-2">Loading connected accounts…</div>
          <div v-else class="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <label
              v-for="p in platforms"
              :key="p.id"
              class="flex flex-col items-center p-3 border-2 rounded-xl cursor-pointer transition-all"
              :class="[
                !getAccount(p.id) ? 'opacity-50 cursor-not-allowed' : '',
                selectedPlatforms.includes(p.id)
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              ]"
            >
              <input
                type="checkbox"
                :value="p.id"
                v-model="selectedPlatforms"
                :disabled="!getAccount(p.id)"
                class="sr-only"
              />
              <span class="w-10 h-10 mb-1 flex items-center justify-center rounded-xl" :style="{ background: p.bg }">
                <span class="w-6 h-6 flex items-center justify-center" v-html="p.svg"></span>
              </span>
              <span class="text-xs font-medium text-gray-700">{{ p.name }}</span>
              <span v-if="getAccount(p.id)" class="text-xs text-green-600 mt-0.5 truncate max-w-full">● Connected</span>
              <span v-else class="text-xs text-gray-400 mt-0.5">No account</span>
            </label>
          </div>

          <!-- Channel groups info -->
          <div v-if="!loadingAccounts && channelGroups.length === 0 && allAccounts.length > 0" class="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-xs text-yellow-800">
            Accounts are connected but no channel groups exist. Create a channel group in the
            <span class="font-semibold">Channels</span> tab to enable broadcasting.
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
          <span class="text-lg font-bold" :class="r.success ? 'text-green-600' : 'text-red-500'">{{ r.success ? '✓' : '✗' }}</span>
          <span class="w-7 h-7 flex items-center justify-center rounded-lg flex-shrink-0"
            :style="{ background: platforms.find(p=>p.id===r.platform)?.bg || '#6B7280' }"
            v-html="platforms.find(p=>p.id===r.platform)?.svg || ''"></span>
          <div>
            <p class="text-sm font-medium" :class="r.success ? 'text-green-800' : 'text-red-800'">
              {{ getPlatformLabel(r.platform) }}
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
import { ref, computed, onMounted } from 'vue'
import { smartPostApi } from '@/services/smartpost'
import MediaPanel from '@/components/MediaPanel.vue'

const form = ref({ title: '', content: '' })
const selectedPlatforms = ref([])
const publishing = ref(false)
const results = ref([])
const openScheduleModal = ref(false)
const openMediaPanel = ref(false)
const scheduleAt = ref('')
const attachedMedia = ref([])

const loadingAccounts = ref(false)
const allAccounts = ref([])     // from /v1/social-accounts/all
const channelGroups = ref([])   // from /v1/channel-groups

const platforms = [
  {
    id: 'twitter', name: 'X (Twitter)', bg: '#000000',
    svg: `<svg viewBox="0 0 24 24" fill="white" xmlns="http://www.w3.org/2000/svg" width="20" height="20"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.746l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>`,
  },
  {
    id: 'facebook', name: 'Facebook', bg: '#1877F2',
    svg: `<svg viewBox="0 0 24 24" fill="white" xmlns="http://www.w3.org/2000/svg" width="20" height="20"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>`,
  },
  {
    id: 'linkedin', name: 'LinkedIn', bg: '#0A66C2',
    svg: `<svg viewBox="0 0 24 24" fill="white" xmlns="http://www.w3.org/2000/svg" width="20" height="20"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>`,
  },
  {
    id: 'instagram', name: 'Instagram', bg: 'linear-gradient(135deg,#f09433,#e6683c 25%,#dc2743 50%,#cc2366 75%,#bc1888)',
    svg: `<svg viewBox="0 0 24 24" fill="white" xmlns="http://www.w3.org/2000/svg" width="20" height="20"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg>`,
  },
  {
    id: 'whatsapp', name: 'WhatsApp', bg: '#25D366',
    svg: `<svg viewBox="0 0 24 24" fill="white" xmlns="http://www.w3.org/2000/svg" width="20" height="20"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>`,
  },
]

const canPublish = computed(() =>
  form.value.content.trim().length > 0 && selectedPlatforms.value.length > 0
)

// Find a connected account for a platform ID
const getAccount = (id) =>
  allAccounts.value.find(a => a.platform?.toLowerCase() === id && a.status !== 'disconnected')

const getPlatformLabel = (id) =>
  platforms.find(p => p.id === id)?.name || id

function onMediaSelect(media) {
  attachedMedia.value.push(media)
  openMediaPanel.value = false
}

// Find channel group IDs that cover the selected platforms
function getMatchingGroupIds(platformIds) {
  const accountIds = new Set(
    platformIds.map(p => getAccount(p)?.id).filter(Boolean)
  )
  return channelGroups.value
    .filter(g => (g.social_account_ids || []).some(aid => accountIds.has(aid)))
    .map(g => g.id)
}

async function loadData() {
  loadingAccounts.value = true
  try {
    const [accountsRes, groupsRes] = await Promise.all([
      smartPostApi.getAllSocialAccounts(),
      smartPostApi.getChannelGroups(),
    ])
    allAccounts.value = Array.isArray(accountsRes.data)
      ? accountsRes.data
      : (accountsRes.data?.accounts ?? [])
    channelGroups.value = groupsRes.data?.channel_groups ?? []

    // Auto-select platforms that have connected accounts AND are in a channel group
    const coveredPlatforms = platforms
      .filter(p => getAccount(p.id))
      .map(p => p.id)
    selectedPlatforms.value = coveredPlatforms.slice(0, 2)
  } catch {
    allAccounts.value = []
    channelGroups.value = []
  } finally {
    loadingAccounts.value = false
  }
}

async function broadcast() {
  publishing.value = true
  results.value = []
  try {
    const groupIds = getMatchingGroupIds(selectedPlatforms.value)

    if (!groupIds.length) {
      // No channel groups cover the selected platforms
      results.value = selectedPlatforms.value.map(p => ({
        platform: p,
        success: false,
        message: getAccount(p)
          ? 'No channel group includes this account. Create one in the Channels tab.'
          : 'No connected account for this platform',
      }))
      return
    }

    const payload = {
      post_id: crypto.randomUUID(),
      title: form.value.title || form.value.content.slice(0, 50),
      content: form.value.content,
      channel_group_ids: groupIds,
      media_ids: attachedMedia.value.map(m => m.id),
      mode: 'text',
    }

    const res = await smartPostApi.publishNow(payload)
    const channelResults = res?.data?.channels

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
      message: e?.response?.data?.detail || 'Failed',
    }))
  } finally {
    publishing.value = false
  }
}

async function schedulePost() {
  publishing.value = true
  openScheduleModal.value = false
  try {
    const groupIds = getMatchingGroupIds(selectedPlatforms.value)
    const payload = {
      title: form.value.title || form.value.content.slice(0, 50),
      content: form.value.content,
      channel_group_ids: groupIds,
      mode: 'text',
      scheduled_at: scheduleAt.value,
    }
    await smartPostApi.publishNow(payload)
    results.value = [{
      platform: 'Scheduled',
      success: true,
      message: `Scheduled for ${new Date(scheduleAt.value).toLocaleString()}`,
    }]
  } catch (e) {
    results.value = [{
      platform: 'Schedule',
      success: false,
      message: e?.response?.data?.detail || 'Failed to schedule',
    }]
  } finally {
    publishing.value = false
    scheduleAt.value = ''
  }
}

onMounted(loadData)
</script>
