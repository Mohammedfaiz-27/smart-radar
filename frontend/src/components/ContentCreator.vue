<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60">
    <div class="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[93vh] overflow-y-auto mx-4">

      <!-- Header -->
      <div class="flex items-center justify-between p-6 border-b border-gray-100">
        <div>
          <h2 class="text-xl font-bold text-gray-900">Create Post from Intelligence</h2>
          <p class="text-sm text-gray-500 mt-0.5">AI-powered response based on live analysis</p>
        </div>
        <button @click="emit('close')" class="text-gray-400 hover:text-gray-600 p-2 rounded-lg hover:bg-gray-100">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>

      <div class="p-6 space-y-5">

        <!-- Source post + AI intelligence -->
        <div v-if="post" class="rounded-xl border border-gray-200 overflow-hidden">
          <!-- Source post -->
          <div class="bg-gray-50 p-4">
            <div class="flex items-center space-x-2 mb-2">
              <span class="text-xs font-semibold text-gray-500 uppercase">Source Post</span>
              <span class="text-xs px-2 py-0.5 rounded-full bg-gray-200 text-gray-600">{{ post.platform }}</span>
              <span class="text-xs text-gray-400">{{ post.author_username || post.author }}</span>
            </div>
            <p class="text-sm text-gray-800 line-clamp-3">{{ post.content }}</p>
          </div>

          <!-- AI intelligence strip -->
          <div class="bg-white border-t border-gray-100 px-4 py-3 flex flex-wrap gap-3">
            <!-- Sentiment -->
            <div class="flex items-center space-x-1.5">
              <span class="text-xs text-gray-500">Sentiment:</span>
              <span class="text-xs font-semibold px-2 py-0.5 rounded-full"
                :class="sentimentClass(post.intelligence?.sentiment_label)">
                {{ post.intelligence?.sentiment_label || 'Unknown' }}
                ({{ (post.intelligence?.sentiment_score || 0).toFixed(2) }})
              </span>
            </div>

            <!-- Threat -->
            <div v-if="post.intelligence?.is_threat" class="flex items-center space-x-1.5">
              <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-red-100 text-red-700">
                ⚠ Threat Detected
              </span>
            </div>

            <!-- Urgency -->
            <div v-if="post.intelligence?.threat_level" class="flex items-center space-x-1.5">
              <span class="text-xs text-gray-500">Urgency:</span>
              <span class="text-xs font-semibold px-2 py-0.5 rounded-full"
                :class="urgencyClass(post.intelligence.threat_level)">
                {{ post.intelligence.threat_level.toUpperCase() }}
              </span>
            </div>

            <!-- Engagement -->
            <div class="flex items-center space-x-1.5 ml-auto">
              <span class="text-xs text-gray-400">
                {{ post.engagement_metrics?.likes || 0 }} likes ·
                {{ post.engagement_metrics?.shares || 0 }} shares
              </span>
            </div>
          </div>

          <!-- Entity sentiments if present -->
          <div v-if="hasEntities" class="border-t border-gray-100 px-4 py-3 flex flex-wrap gap-2">
            <span class="text-xs text-gray-500 self-center">Entities:</span>
            <span
              v-for="(s, entity) in post.entity_sentiments"
              :key="entity"
              class="text-xs px-2 py-0.5 rounded-lg border font-medium"
              :class="sentimentClass(s.label)"
            >
              {{ entity }}: {{ s.score > 0 ? '+' : '' }}{{ s.score.toFixed(2) }}
            </span>
          </div>
        </div>

        <!-- AI recommended tone (auto-set based on intelligence) -->
        <div class="bg-blue-50 border border-blue-100 rounded-xl p-4 flex items-start space-x-3">
          <span class="text-blue-500 text-lg">🤖</span>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-semibold text-blue-800 mb-0.5">AI Recommendation</p>
            <p class="text-xs text-blue-700">{{ aiRecommendation }}</p>
          </div>
        </div>

        <!-- Controls -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1 uppercase">Tone</label>
            <select v-model="selectedTone" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option v-for="t in tones" :key="t" :value="t">{{ t }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1 uppercase">Mode</label>
            <select v-model="selectedMode" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="counter-narrative">Counter Narrative</option>
              <option value="direct-reply">Direct Reply</option>
              <option value="informational">Informational</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1 uppercase">Platforms</label>
            <div class="flex flex-wrap gap-2 pt-1">
              <label v-for="p in platforms" :key="p.id" class="flex items-center space-x-1 cursor-pointer">
                <input type="checkbox" :value="p.id" v-model="selectedPlatforms" class="rounded" />
                <span class="text-sm">{{ p.icon }}</span>
              </label>
            </div>
          </div>
        </div>

        <!-- Generate -->
        <button
          @click="generate"
          :disabled="generating || !selectedPlatforms.length"
          class="w-full bg-blue-600 hover:bg-blue-700 text-white text-sm py-2.5 rounded-xl font-medium disabled:opacity-50 transition-colors flex items-center justify-center space-x-2"
        >
          <svg v-if="generating" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
          </svg>
          <span>{{ generating ? 'Generating with AI…' : '✨ Generate AI Content' }}</span>
        </button>

        <!-- Generated content -->
        <div v-if="suggestions.length" class="space-y-4">
          <h3 class="text-sm font-semibold text-gray-700">Generated Content</h3>
          <div v-for="s in suggestions" :key="s.platform" class="border border-gray-200 rounded-xl p-4">
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-medium text-gray-900">{{ getPlatformIcon(s.platform) }} {{ s.platform }}</span>
              <span class="text-xs text-gray-400">{{ s.content?.length || 0 }} chars</span>
            </div>
            <textarea
              v-model="s.content"
              rows="3"
              class="w-full text-sm text-gray-700 bg-gray-50 border border-gray-100 rounded-lg p-2 resize-none focus:outline-none focus:ring-1 focus:ring-blue-400"
            />
          </div>
        </div>

        <!-- Actions -->
        <div v-if="suggestions.length" class="flex items-center justify-between pt-2 border-t border-gray-100">
          <button @click="saveDraft" :disabled="savingDraft" class="text-sm text-gray-600 border border-gray-200 px-4 py-2 rounded-lg hover:bg-gray-50 disabled:opacity-50">
            {{ savingDraft ? 'Saving…' : 'Save as Draft' }}
          </button>
          <button @click="openPublishModal = true" class="bg-green-600 hover:bg-green-700 text-white text-sm px-6 py-2 rounded-lg font-medium">
            Publish Now
          </button>
        </div>

      </div>
    </div>
  </div>

  <PublishModal
    :is-open="openPublishModal"
    :post="post"
    :initial-text="combinedText"
    @close="openPublishModal = false"
  />
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { smartPostApi } from '@/services/smartpost'
import PublishModal from '@/components/PublishModal.vue'

const props = defineProps({ isOpen: Boolean, post: Object })
const emit = defineEmits(['close'])

const selectedTone = ref('formal')
const selectedMode = ref('counter-narrative')
const selectedPlatforms = ref(['twitter', 'facebook'])
const suggestions = ref([])
const generating = ref(false)
const savingDraft = ref(false)
const openPublishModal = ref(false)
const combinedText = ref('')

const tones = [
  'formal', 'urgent', 'empathetic', 'confident', 'neutral', 'assertive',
  'professional', 'authoritative', 'transparent', 'calm', 'decisive',
  'measured', 'concerned', 'informative', 'diplomatic', 'firm',
  'reassuring', 'factual', 'objective', 'constructive', 'responsive',
]

const platforms = [
  { id: 'twitter', icon: '🐦' },
  { id: 'facebook', icon: '📘' },
  { id: 'linkedin', icon: '💼' },
  { id: 'instagram', icon: '📷' },
]

const getPlatformIcon = (id) => platforms.find(p => p.id === id)?.icon || '📣'

const hasEntities = computed(() =>
  props.post?.entity_sentiments && Object.keys(props.post.entity_sentiments).length > 0
)

// Auto-set recommended tone based on intelligence
const aiRecommendation = computed(() => {
  if (!props.post) return 'Select tone and mode, then generate AI content.'
  const sentiment = props.post.intelligence?.sentiment_label?.toLowerCase()
  const isThreat = props.post.intelligence?.is_threat
  const level = props.post.intelligence?.threat_level

  if (isThreat || level === 'critical' || level === 'high') {
    return 'High-urgency post detected. Recommend "urgent" tone with "counter-narrative" mode for rapid response.'
  }
  if (sentiment === 'negative') {
    return 'Negative sentiment detected. Recommend "empathetic" or "reassuring" tone to address concerns directly.'
  }
  if (sentiment === 'positive') {
    return 'Positive sentiment detected. Recommend "confident" or "engaging" tone to amplify the message.'
  }
  return 'Neutral content detected. Use "informational" mode to provide accurate context and facts.'
})

// Auto-select tone based on post intelligence when modal opens
watch(() => props.isOpen, (open) => {
  if (!open) return
  suggestions.value = []
  const sentiment = props.post?.intelligence?.sentiment_label?.toLowerCase()
  const isThreat = props.post?.intelligence?.is_threat
  const level = props.post?.intelligence?.threat_level

  if (isThreat || level === 'critical' || level === 'high') {
    selectedTone.value = 'urgent'
    selectedMode.value = 'counter-narrative'
  } else if (sentiment === 'negative') {
    selectedTone.value = 'empathetic'
    selectedMode.value = 'direct-reply'
  } else if (sentiment === 'positive') {
    selectedTone.value = 'confident'
    selectedMode.value = 'informational'
  } else {
    selectedTone.value = 'formal'
    selectedMode.value = 'informational'
  }
})

function sentimentClass(label) {
  const l = label?.toLowerCase()
  if (l === 'positive') return 'bg-green-100 text-green-800'
  if (l === 'negative') return 'bg-red-100 text-red-800'
  return 'bg-gray-100 text-gray-700'
}

function urgencyClass(level) {
  const l = level?.toLowerCase()
  if (l === 'critical') return 'bg-red-100 text-red-800'
  if (l === 'high') return 'bg-orange-100 text-orange-800'
  if (l === 'medium') return 'bg-yellow-100 text-yellow-800'
  return 'bg-gray-100 text-gray-700'
}

async function generate() {
  generating.value = true
  try {
    const res = await smartPostApi.getContentSuggestions({
      context: {
        platform: props.post?.platform,
        author: props.post?.author,
        text: props.post?.content,
        sentiment: props.post?.intelligence?.sentiment_label,
        threat_level: props.post?.intelligence?.threat_level,
        is_threat: props.post?.intelligence?.is_threat,
      },
      tone: selectedTone.value,
      mode: selectedMode.value,
      platforms: selectedPlatforms.value,
    })
    suggestions.value = res.data?.suggestions || selectedPlatforms.value.map(p => ({
      platform: p,
      content: res.data?.content || `[AI content for ${p}]`,
    }))
  } catch {
    suggestions.value = selectedPlatforms.value.map(p => ({
      platform: p,
      content: `Response to: "${props.post?.content?.slice(0, 80)}…"`,
    }))
  } finally {
    generating.value = false
  }
}

async function saveDraft() {
  savingDraft.value = true
  try {
    await smartPostApi.createDraft({
      title: props.post?.content?.slice(0, 60) || 'Draft',
      content: { text: suggestions.value.map(s => s.content).join('\n\n---\n\n') },
      channels: selectedPlatforms.value.map(p => ({ platform: p, account_id: p })),
    })
    emit('close')
  } catch {
    alert('Failed to save draft')
  } finally {
    savingDraft.value = false
  }
}

function openPublish() {
  combinedText.value = suggestions.value.map(s => s.content).join('\n\n---\n\n')
  openPublishModal.value = true
}
</script>
