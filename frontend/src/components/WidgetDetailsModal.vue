<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4" @click.self="closeModal">

        <!-- Backdrop -->
        <div class="absolute inset-0 bg-gray-900/60 backdrop-blur-sm"></div>

        <!-- Panel -->
        <div class="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl flex flex-col max-h-[88vh] overflow-hidden">

          <!-- Colored top bar based on type -->
          <div class="h-1 w-full rounded-t-2xl" :class="accentBar"></div>

          <!-- Header -->
          <div class="flex items-start justify-between px-6 pt-5 pb-4 border-b border-gray-100">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" :class="iconBg">
                <!-- positive -->
                <svg v-if="widgetType === 'positive'" class="w-5 h-5" :class="iconColor" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <!-- negative -->
                <svg v-else-if="widgetType === 'negative'" class="w-5 h-5" :class="iconColor" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <!-- opportunities -->
                <svg v-else class="w-5 h-5" :class="iconColor" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
                </svg>
              </div>
              <div>
                <h2 class="text-lg font-bold text-gray-900 leading-tight">{{ modalTitle }}</h2>
                <p class="text-xs text-gray-500 mt-0.5">{{ modalSubtitle }}</p>
              </div>
            </div>
            <div class="flex items-center gap-2 ml-4 flex-shrink-0">
              <span class="text-xs font-semibold px-2.5 py-1 rounded-full" :class="countBadge">
                {{ posts.length }}{{ hasMore ? '+' : '' }} posts
              </span>
              <button @click="closeModal" class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors">
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>
          </div>

          <!-- Posts list -->
          <div class="flex-1 overflow-y-auto px-6 py-4 space-y-3">

            <!-- Loading first batch -->
            <div v-if="loading && posts.length === 0" class="flex flex-col items-center justify-center py-16 gap-3">
              <div class="w-10 h-10 rounded-full border-[3px] border-gray-200 border-t-blue-600 animate-spin"></div>
              <p class="text-sm text-gray-500">Loading posts…</p>
            </div>

            <!-- Empty -->
            <div v-else-if="!loading && posts.length === 0" class="flex flex-col items-center justify-center py-16 gap-2">
              <svg class="w-12 h-12 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              <p class="text-sm font-medium text-gray-500">No posts in this category</p>
            </div>

            <!-- Post cards -->
            <div v-for="post in posts" :key="post.id"
              class="group bg-white border border-gray-200 rounded-xl p-4 hover:border-gray-300 hover:shadow-sm transition-all"
              :class="cardLeftBorder(post.sentiment)">

              <!-- Card top row -->
              <div class="flex items-start justify-between gap-3 mb-3">
                <div class="flex items-center gap-2.5 min-w-0">
                  <!-- Platform avatar -->
                  <div class="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold flex-shrink-0"
                    :class="platformAvatar(post.platform)">
                    {{ platformInitial(post.platform) }}
                  </div>
                  <div class="min-w-0">
                    <p class="text-sm font-semibold text-gray-900 truncate">{{ post.author || 'Unknown' }}</p>
                    <p class="text-xs text-gray-400">{{ formatDate(post.posted_at) }} · <span class="capitalize">{{ post.platform || 'unknown' }}</span></p>
                  </div>
                </div>
                <!-- Sentiment pill -->
                <span class="flex-shrink-0 inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full" :class="sentimentPill(post.sentiment)">
                  <span class="w-1.5 h-1.5 rounded-full" :class="sentimentDot(post.sentiment)"></span>
                  {{ post.sentiment || 'neutral' }}
                </span>
              </div>

              <!-- Content -->
              <p class="text-sm text-gray-700 leading-relaxed mb-3 line-clamp-3">{{ post.content }}</p>

              <!-- Bottom row -->
              <div class="flex items-center justify-between pt-2 border-t border-gray-100">
                <!-- Engagement + Source -->
                <div class="flex items-center gap-3 text-xs text-gray-400 flex-wrap">
                  <span v-if="post.cluster_type" class="font-medium text-gray-500 capitalize">{{ post.cluster_type }}</span>
                  <span v-if="post.engagement_metrics?.likes" class="flex items-center gap-1">
                    <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z"/></svg>
                    {{ post.engagement_metrics.likes }}
                  </span>
                  <span v-if="post.engagement_metrics?.comments" class="flex items-center gap-1">
                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg>
                    {{ post.engagement_metrics.comments }}
                  </span>
                  <a v-if="post.url || post.post_url" :href="post.url || post.post_url" target="_blank" rel="noopener noreferrer"
                    class="flex items-center gap-1 text-blue-500 hover:text-blue-700 transition-colors font-medium">
                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                    </svg>
                    Source
                  </a>
                </div>

                <!-- Respond button — modern style -->
                <button @click="handleRespond(post)"
                  class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
                  :class="respondBtn">
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"/>
                  </svg>
                  Reply
                </button>
              </div>
            </div>
            <!-- Load More -->
            <div v-if="hasMore" class="pt-2 pb-1 text-center">
              <button
                @click="loadMore"
                :disabled="loadingMore"
                class="inline-flex items-center gap-2 px-5 py-2 text-sm font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-50 transition-colors"
              >
                <svg v-if="loadingMore" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
                {{ loadingMore ? 'Loading…' : `Load more posts` }}
              </button>
            </div>

            <!-- Loading more indicator at bottom -->
            <div v-if="loadingMore && posts.length > 0" class="py-2 text-center">
              <div class="w-6 h-6 rounded-full border-2 border-gray-200 border-t-blue-500 animate-spin mx-auto"></div>
            </div>
          </div>

        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useResponseStore } from '@/stores/response'

const responseStore = useResponseStore()

const props = defineProps({
  isOpen:     { type: Boolean, default: false },
  widgetType: { type: String, default: '', validator: v => ['positive','negative','opportunities',''].includes(v) }
})
const emit = defineEmits(['close'])

const PAGE = 50
const posts       = ref([])
const loading     = ref(false)
const loadingMore = ref(false)
const hasMore     = ref(false)
const skip        = ref(0)

// ── Type-based styling ─────────────────────────────────────────────
const accentBar = computed(() => ({
  positive:     'bg-emerald-500',
  negative:     'bg-rose-500',
  opportunities:'bg-violet-500',
}[props.widgetType] ?? 'bg-blue-500'))

const iconBg = computed(() => ({
  positive:     'bg-emerald-50',
  negative:     'bg-rose-50',
  opportunities:'bg-violet-50',
}[props.widgetType] ?? 'bg-gray-100'))

const iconColor = computed(() => ({
  positive:     'text-emerald-600',
  negative:     'text-rose-600',
  opportunities:'text-violet-600',
}[props.widgetType] ?? 'text-gray-500'))

const countBadge = computed(() => ({
  positive:     'bg-emerald-100 text-emerald-700',
  negative:     'bg-rose-100 text-rose-700',
  opportunities:'bg-violet-100 text-violet-700',
}[props.widgetType] ?? 'bg-gray-100 text-gray-600'))

const respondBtn = computed(() => ({
  positive:     'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200',
  negative:     'bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200',
  opportunities:'bg-violet-50 text-violet-700 hover:bg-violet-100 border border-violet-200',
}[props.widgetType] ?? 'bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200'))

const modalTitle = computed(() => ({
  positive:     'Positive Posts',
  negative:     'Negative Posts',
  opportunities:'Opportunities',
}[props.widgetType] ?? 'Posts'))

const modalSubtitle = computed(() => ({
  positive:     'Own posts with positive sentiment',
  negative:     'Own posts with negative sentiment requiring attention',
  opportunities:'Competitor posts with negative sentiment',
}[props.widgetType] ?? 'Post details'))

// ── Post card helpers ──────────────────────────────────────────────
const PLATFORM_COLORS = {
  twitter:   'bg-sky-100 text-sky-700',
  instagram: 'bg-pink-100 text-pink-700',
  facebook:  'bg-blue-100 text-blue-700',
  linkedin:  'bg-indigo-100 text-indigo-700',
  whatsapp:  'bg-green-100 text-green-700',
}
const platformAvatar  = (p) => PLATFORM_COLORS[p?.toLowerCase()] ?? 'bg-gray-100 text-gray-600'
const platformInitial = (p) => p?.charAt(0)?.toUpperCase() ?? 'P'

const cardLeftBorder = (sentiment) => ({
  positive: 'border-l-4 border-l-emerald-400',
  negative: 'border-l-4 border-l-rose-400',
  neutral:  'border-l-4 border-l-gray-300',
}[sentiment?.toLowerCase()] ?? '')

const sentimentPill = (s) => ({
  positive: 'bg-emerald-50 text-emerald-700',
  negative: 'bg-rose-50 text-rose-700',
  neutral:  'bg-gray-100 text-gray-600',
}[s?.toLowerCase()] ?? 'bg-gray-100 text-gray-600')

const sentimentDot = (s) => ({
  positive: 'bg-emerald-500',
  negative: 'bg-rose-500',
  neutral:  'bg-gray-400',
}[s?.toLowerCase()] ?? 'bg-gray-400')

const formatDate = (d) => {
  if (!d) return '—'
  const dt = new Date(d)
  return dt.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) + ' · ' +
    dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

// ── Actions ────────────────────────────────────────────────────────
const closeModal = () => emit('close')

const handleRespond = (post) => {
  responseStore.openResponsePanel(post)
  closeModal()
}

// Build query params for each widget type
function buildParams(skp) {
  const base = `limit=${PAGE}&skip=${skp}`
  if (props.widgetType === 'positive')      return `cluster_type=own&sentiment_label=Positive&${base}`
  if (props.widgetType === 'negative')      return `cluster_type=own&sentiment_label=Negative&${base}`
  if (props.widgetType === 'opportunities') return `cluster_type=competitor&sentiment_label=Negative&${base}`
  return base
}

const fetchPosts = async () => {
  if (!props.widgetType || !props.isOpen) return
  loading.value = true
  posts.value = []
  skip.value  = 0
  try {
    const apiBase = import.meta.env.VITE_API_URL || ''
    const res  = await fetch(`${apiBase}/api/v1/posts?${buildParams(0)}`)
    const data = await res.json()
    posts.value = Array.isArray(data) ? data : []
    hasMore.value = posts.value.length === PAGE
    skip.value = posts.value.length
  } catch {
    posts.value = []
    hasMore.value = false
  } finally {
    loading.value = false
  }
}

const loadMore = async () => {
  if (loadingMore.value || !hasMore.value) return
  loadingMore.value = true
  try {
    const apiBase = import.meta.env.VITE_API_URL || ''
    const res  = await fetch(`${apiBase}/api/v1/posts?${buildParams(skip.value)}`)
    const data = await res.json()
    const batch = Array.isArray(data) ? data : []
    posts.value.push(...batch)
    hasMore.value = batch.length === PAGE
    skip.value += batch.length
  } catch {
    hasMore.value = false
  } finally {
    loadingMore.value = false
  }
}

watch(() => [props.isOpen, props.widgetType], ([open]) => {
  open && props.widgetType ? fetchPosts() : (posts.value = [], hasMore.value = false)
}, { immediate: true })
</script>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; transform: scale(0.97); }

.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
