<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60">
    <div class="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto mx-4">
      <!-- Header -->
      <div class="flex items-center justify-between p-6 border-b border-gray-100">
        <div>
          <h2 class="text-xl font-bold text-gray-900">Generate News Card</h2>
          <p class="text-sm text-gray-500 mt-0.5">Create a shareable visual card from this post</p>
        </div>
        <button @click="emit('close')" class="text-gray-400 hover:text-gray-600 p-2 rounded-lg hover:bg-gray-100">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>

      <div class="p-6 space-y-5">
        <!-- Source post -->
        <div v-if="post" class="bg-gray-50 rounded-xl p-4 border border-gray-200">
          <p class="text-xs font-semibold text-gray-500 uppercase mb-1">Source Post</p>
          <p class="text-sm text-gray-700 line-clamp-3">{{ post.content }}</p>
          <p class="text-xs text-gray-400 mt-1">{{ post.platform }} · {{ post.author_username || post.author }}</p>
        </div>

        <!-- Card options -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Card Style</label>
            <select v-model="form.style" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="news">News Breaking</option>
              <option value="alert">Alert / Warning</option>
              <option value="update">Official Update</option>
              <option value="factcheck">Fact Check</option>
              <option value="statement">Statement</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Color Theme</label>
            <select v-model="form.theme" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="blue">Government Blue</option>
              <option value="dark">Dark Authoritative</option>
              <option value="red">Alert Red</option>
              <option value="green">Positive Green</option>
              <option value="neutral">Neutral Gray</option>
            </select>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Headline</label>
          <input
            v-model="form.headline"
            type="text"
            placeholder="Main headline for the card…"
            class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Key Message</label>
          <textarea
            v-model="form.message"
            rows="3"
            placeholder="Key message or fact to highlight…"
            class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Source / Attribution</label>
          <input
            v-model="form.attribution"
            type="text"
            placeholder="e.g. Ministry of Information"
            class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <!-- Generate button -->
        <button
          @click="generate"
          :disabled="generating"
          class="w-full bg-purple-600 hover:bg-purple-700 text-white text-sm py-2.5 rounded-xl font-medium disabled:opacity-50 transition-colors flex items-center justify-center space-x-2"
        >
          <svg v-if="generating" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
          </svg>
          <span>{{ generating ? 'Generating…' : '🗞 Generate News Card' }}</span>
        </button>

        <!-- Preview -->
        <div v-if="cardResult" class="space-y-4">
          <div class="border border-gray-200 rounded-xl overflow-hidden">
            <!-- Card preview render -->
            <div
              class="p-6 text-white relative"
              :class="themeClasses"
            >
              <div class="flex items-center space-x-2 mb-3">
                <span class="text-xs font-bold uppercase tracking-widest px-2 py-0.5 bg-white bg-opacity-20 rounded">
                  {{ styleLabels[form.style] || 'NEWS' }}
                </span>
                <span class="text-xs opacity-60">{{ formatDate(new Date()) }}</span>
              </div>
              <h3 class="text-xl font-black leading-tight mb-2">
                {{ cardResult.headline || form.headline || 'BREAKING NEWS' }}
              </h3>
              <p class="text-sm opacity-90 leading-relaxed">
                {{ cardResult.message || form.message || post?.content?.slice(0, 200) }}
              </p>
              <div class="mt-4 pt-3 border-t border-white border-opacity-30 flex items-center justify-between">
                <span class="text-xs opacity-70">{{ cardResult.attribution || form.attribution || 'Smart Radar' }}</span>
                <span class="text-xs opacity-50">smart-radar.gov</span>
              </div>
            </div>
          </div>

          <!-- Download / Share -->
          <div class="flex items-center space-x-3">
            <button
              v-if="cardResult.image_url"
              @click="download(cardResult.image_url)"
              class="flex-1 flex items-center justify-center space-x-2 text-sm border border-gray-200 px-4 py-2 rounded-lg hover:bg-gray-50"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              <span>Download</span>
            </button>
            <button
              @click="openPublish = true"
              class="flex-1 bg-green-600 hover:bg-green-700 text-white text-sm px-4 py-2 rounded-lg font-medium"
            >
              Share to Platforms
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <PublishModal
    :is-open="openPublish"
    :post="post"
    :initial-text="cardResult?.message || form.message || ''"
    @close="openPublish = false"
  />
</template>

<script setup>
import { ref, computed } from 'vue'
import { smartPostApi } from '@/services/smartpost'
import PublishModal from '@/components/PublishModal.vue'

const props = defineProps({ isOpen: Boolean, post: Object })
const emit = defineEmits(['close'])

const form = ref({ style: 'news', theme: 'blue', headline: '', message: '', attribution: '' })
const generating = ref(false)
const cardResult = ref(null)
const openPublish = ref(false)

const styleLabels = {
  news: 'BREAKING', alert: 'ALERT', update: 'UPDATE', factcheck: 'FACT CHECK', statement: 'STATEMENT'
}

const themeClasses = computed(() => {
  const map = {
    blue: 'bg-gradient-to-br from-blue-700 to-blue-900',
    dark: 'bg-gradient-to-br from-gray-800 to-gray-950',
    red: 'bg-gradient-to-br from-red-600 to-red-900',
    green: 'bg-gradient-to-br from-green-600 to-green-900',
    neutral: 'bg-gradient-to-br from-gray-500 to-gray-700',
  }
  return map[form.value.theme] || map.blue
})

const formatDate = (d) => d.toLocaleDateString('en', { year: 'numeric', month: 'long', day: 'numeric' })

async function generate() {
  generating.value = true
  cardResult.value = null
  try {
    const res = await smartPostApi.generateNewsCard({
      post_id: props.post?.id,
      source_content: props.post?.content,
      source_platform: props.post?.platform,
      headline: form.value.headline,
      message: form.value.message,
      attribution: form.value.attribution,
      style: form.value.style,
      theme: form.value.theme,
    })
    cardResult.value = res.data || {
      headline: form.value.headline || props.post?.content?.split('.')[0] || 'Breaking Update',
      message: form.value.message || props.post?.content?.slice(0, 200),
      attribution: form.value.attribution,
    }
  } catch {
    cardResult.value = {
      headline: form.value.headline || props.post?.content?.split('.')[0] || 'Breaking Update',
      message: form.value.message || props.post?.content?.slice(0, 200),
      attribution: form.value.attribution,
    }
  } finally {
    generating.value = false
  }
}

function download(url) {
  const a = document.createElement('a')
  a.href = url
  a.download = 'news-card.png'
  a.click()
}
</script>
