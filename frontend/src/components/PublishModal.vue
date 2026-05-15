<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60">
    <div class="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto mx-4">

      <!-- Header -->
      <div class="flex items-center justify-between p-6 border-b border-gray-100">
        <div>
          <h2 class="text-xl font-bold text-gray-900">Publish Response</h2>
          <p class="text-sm text-gray-500 mt-0.5">Choose platforms and publish your response</p>
        </div>
        <button @click="emit('close')" class="text-gray-400 hover:text-gray-600 p-2 rounded-lg hover:bg-gray-100">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>

      <div class="p-6 space-y-5">

        <!-- Source context -->
        <div v-if="post" class="bg-gray-50 rounded-xl p-3 border border-gray-200">
          <p class="text-xs text-gray-500 font-semibold uppercase mb-1">Responding to</p>
          <p class="text-sm text-gray-700 line-clamp-2">{{ post.content }}</p>
          <p class="text-xs text-gray-400 mt-1">{{ post.platform }} · {{ post.author_username || post.author }}</p>
        </div>

        <!-- Response text -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Response Text</label>
          <textarea
            v-model="responseText"
            rows="5"
            class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            placeholder="Enter your response…"
          />
          <p class="text-xs text-gray-400 mt-1 text-right">{{ responseText.length }} chars</p>
        </div>

        <!-- Platform selection -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-3">Select Platforms</label>
          <div class="grid grid-cols-2 gap-3">
            <label
              v-for="platform in platforms"
              :key="platform.id"
              class="flex items-center space-x-3 p-3 border-2 rounded-xl cursor-pointer transition-all"
              :class="selectedPlatforms.includes(platform.id)
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'"
            >
              <input type="checkbox" :value="platform.id" v-model="selectedPlatforms" class="sr-only" />
              <span class="text-xl">{{ platform.icon }}</span>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-900">{{ platform.name }}</p>
              </div>
              <div v-if="selectedPlatforms.includes(platform.id)"
                class="w-4 h-4 bg-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
                <svg class="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                </svg>
              </div>
            </label>
          </div>
        </div>

        <!-- Publish results -->
        <div v-if="publishResults.length" class="space-y-2">
          <label class="block text-sm font-medium text-gray-700">Publish Results</label>
          <div
            v-for="r in publishResults"
            :key="r.platform"
            class="flex items-center space-x-3 p-3 rounded-lg"
            :class="r.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'"
          >
            <span class="text-lg" :class="r.success ? 'text-green-600' : 'text-red-600'">
              {{ r.success ? '✓' : '✗' }}
            </span>
            <div>
              <p class="text-sm font-medium" :class="r.success ? 'text-green-800' : 'text-red-800'">
                {{ r.platform }}
              </p>
              <p class="text-xs" :class="r.success ? 'text-green-600' : 'text-red-600'">
                {{ r.message || (r.success ? 'Logged successfully' : 'Failed') }}
              </p>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex items-center justify-between pt-2">
          <button
            @click="saveDraft"
            :disabled="loading || !responseText.trim()"
            class="text-sm text-gray-600 hover:text-gray-800 border border-gray-200 px-4 py-2 rounded-lg hover:bg-gray-50 disabled:opacity-40 transition-colors"
          >
            Send for Approval
          </button>
          <div class="flex space-x-3">
            <button @click="emit('close')" class="text-sm text-gray-500 px-4 py-2 rounded-lg hover:bg-gray-100">
              Cancel
            </button>
            <button
              @click="publishNow"
              :disabled="!selectedPlatforms.length || !responseText.trim() || loading"
              class="bg-blue-600 hover:bg-blue-700 text-white text-sm px-6 py-2 rounded-lg font-medium disabled:opacity-50 transition-colors flex items-center space-x-2"
            >
              <svg v-if="loading" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              <span>{{ loading ? 'Publishing…' : 'Publish Now' }}</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { smartPostApi } from '@/services/smartpost'

const props = defineProps({
  isOpen: Boolean,
  post: Object,
  initialText: { type: String, default: '' },
})
const emit = defineEmits(['close'])

const responseText = ref('')
const selectedPlatforms = ref(['twitter', 'facebook'])
const publishResults = ref([])
const loading = ref(false)

const platforms = [
  { id: 'facebook',  name: 'Facebook',    icon: '📘' },
  { id: 'twitter',   name: 'Twitter / X', icon: '🐦' },
  { id: 'linkedin',  name: 'LinkedIn',    icon: '💼' },
  { id: 'instagram', name: 'Instagram',   icon: '📷' },
  { id: 'whatsapp',  name: 'WhatsApp',    icon: '💬' },
]

watch(() => props.isOpen, (open) => {
  if (open) {
    responseText.value = props.initialText || ''
    publishResults.value = []
    selectedPlatforms.value = ['twitter', 'facebook']
  }
})

async function publishNow() {
  loading.value = true
  publishResults.value = []
  const channels = selectedPlatforms.value.map(p => ({ platform: p, account_id: p }))
  try {
    const res = await smartPostApi.publishNow({
      title: props.post?.content?.slice(0, 60) || responseText.value.slice(0, 60),
      content: { text: responseText.value },
      channels,
    })
    publishResults.value = res?.results || channels.map(c => ({ platform: c.platform, success: true }))
  } catch {
    publishResults.value = channels.map(c => ({ platform: c.platform, success: false, message: 'Publish failed' }))
  } finally {
    loading.value = false
  }
}

async function saveDraft() {
  loading.value = true
  try {
    await smartPostApi.createDraft({
      title: props.post?.content?.slice(0, 60) || 'Draft',
      content: { text: responseText.value },
      channels: selectedPlatforms.value.map(p => ({ platform: p, account_id: p })),
    })
    emit('close')
  } catch {
    // silently fail
  } finally {
    loading.value = false
  }
}
</script>
