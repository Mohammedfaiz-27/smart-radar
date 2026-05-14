<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-gray-900">Posts</h2>
        <p class="text-sm text-gray-600 mt-1">Manage and track your published social media content</p>
      </div>
      <router-link
        to="/post-creator"
        class="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg shadow-sm transition-colors"
      >
        <svg class="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        Create Post
      </router-link>
    </div>

    <!-- Filters -->
    <div class="bg-white rounded-lg shadow border border-gray-200 p-4">
      <div class="flex flex-wrap gap-4 items-end">
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">Status</label>
          <select v-model="filters.status" class="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500">
            <option value="">All Status</option>
            <option value="draft">Draft</option>
            <option value="scheduled">Scheduled</option>
            <option value="published">Published</option>
            <option value="failed">Failed</option>
            <option value="pending">Pending Review</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">Platform</label>
          <select v-model="filters.platform" class="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500">
            <option value="">All Platforms</option>
            <option value="twitter">Twitter / X</option>
            <option value="facebook">Facebook</option>
            <option value="linkedin">LinkedIn</option>
            <option value="instagram">Instagram</option>
            <option value="whatsapp">WhatsApp</option>
          </select>
        </div>
        <div class="flex items-end space-x-2">
          <button @click="load" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors">
            Apply
          </button>
          <button @click="resetFilters" class="px-3 py-2 text-sm text-gray-600 hover:text-gray-900">
            Reset
          </button>
        </div>
      </div>
    </div>

    <!-- Posts list -->
    <div class="bg-white rounded-lg shadow border border-gray-200">

      <!-- Loading -->
      <div v-if="loading" class="p-8 text-center">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p class="mt-2 text-sm text-gray-600">Loading posts...</p>
      </div>

      <!-- Empty -->
      <div v-else-if="posts.length === 0" class="p-12 text-center">
        <svg class="mx-auto h-12 w-12 text-gray-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
        <h3 class="text-sm font-semibold text-gray-900">
          {{ filtersActive ? 'No posts match your filters' : 'No posts yet' }}
        </h3>
        <p class="mt-1 text-sm text-gray-500">
          {{ filtersActive ? 'Try adjusting your filter criteria.' : 'Get started by creating your first post.' }}
        </p>
        <router-link
          v-if="!filtersActive"
          to="/post-creator"
          class="mt-4 inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md"
        >
          Create Post
        </router-link>
      </div>

      <!-- List -->
      <div v-else class="divide-y divide-gray-200">
        <div
          v-for="post in posts"
          :key="post.id ?? post.post_id"
          class="p-6 hover:bg-gray-50 transition-colors"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1 min-w-0">
              <h3 class="text-sm font-semibold text-gray-900 truncate">{{ post.title || 'Untitled' }}</h3>
              <p class="text-sm text-gray-600 mt-1 line-clamp-2">{{ getPostText(post) }}</p>

              <div class="mt-3 flex items-center flex-wrap gap-3 text-xs text-gray-500">
                <!-- Date -->
                <span class="flex items-center space-x-1">
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                  </svg>
                  <span>{{ formatDate(post.scheduled_at || post.published_at || post.created_at) }}</span>
                </span>

                <!-- Channels -->
                <span v-if="post.channels?.length" class="flex items-center space-x-1">
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"/>
                  </svg>
                  <span>{{ post.channels.length }} channels</span>
                </span>

                <!-- Platform icons -->
                <span v-if="post.platforms?.length" class="flex space-x-0.5">
                  <span v-for="p in post.platforms" :key="p" :title="p">{{ getPlatformIcon(p) }}</span>
                </span>
              </div>
            </div>

            <div class="ml-4 flex-shrink-0 flex flex-col items-end space-y-2">
              <span
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize"
                :class="statusClass(post.status)"
              >{{ post.status || 'draft' }}</span>

              <div class="flex space-x-2">
                <button
                  v-if="post.status === 'pending'"
                  @click="approve(post.id ?? post.post_id)"
                  class="text-xs px-2 py-1 bg-green-50 text-green-700 border border-green-200 rounded hover:bg-green-100 transition-colors"
                >
                  Approve
                </button>
                <button
                  v-if="post.status === 'pending'"
                  @click="reject(post.id ?? post.post_id)"
                  class="text-xs px-2 py-1 bg-red-50 text-red-700 border border-red-200 rounded hover:bg-red-100 transition-colors"
                >
                  Reject
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Load more -->
      <div v-if="!loading && posts.length > 0" class="px-6 py-4 border-t border-gray-200 text-center">
        <button
          @click="loadMore"
          :disabled="loadingMore || !hasMore"
          class="text-sm text-blue-600 hover:underline disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {{ loadingMore ? 'Loading…' : hasMore ? 'Load more' : 'All posts loaded' }}
        </button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { smartPostApi } from '@/services/smartpost'

const loading = ref(false)
const loadingMore = ref(false)
const posts = ref([])
const page = ref(1)
const hasMore = ref(true)
const PAGE_SIZE = 20

const filters = ref({ status: '', platform: '' })
const filtersActive = computed(() => !!filters.value.status || !!filters.value.platform)

const platformIcons = { twitter: '🐦', facebook: '📘', linkedin: '💼', instagram: '📷', whatsapp: '💬' }
const getPlatformIcon = (id) => platformIcons[id?.toLowerCase()] || '📣'

function statusClass(s) {
  return {
    'bg-blue-100 text-blue-800': s === 'scheduled',
    'bg-green-100 text-green-800': s === 'published',
    'bg-gray-100 text-gray-800': s === 'draft',
    'bg-red-100 text-red-800': s === 'failed',
    'bg-orange-100 text-orange-800': s === 'pending',
  }
}

function getPostText(post) {
  if (typeof post.content === 'string') return post.content
  if (post.content?.text) return post.content.text
  return ''
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

async function load() {
  loading.value = true
  page.value = 1
  posts.value = []
  try {
    const params = { page: 1, limit: PAGE_SIZE }
    if (filters.value.status) params.status = filters.value.status
    const res = await smartPostApi.getPosts(params)
    const items = res.data?.posts ?? res.data?.items ?? []
    posts.value = filters.value.platform
      ? items.filter(p => p.channels?.some(c => c.platform === filters.value.platform) || p.platforms?.includes(filters.value.platform))
      : items
    hasMore.value = items.length === PAGE_SIZE
  } catch (e) {
    posts.value = []
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  loadingMore.value = true
  page.value++
  try {
    const params = { page: page.value, limit: PAGE_SIZE }
    if (filters.value.status) params.status = filters.value.status
    const res = await smartPostApi.getPosts(params)
    const items = res.data?.posts ?? res.data?.items ?? []
    const filtered = filters.value.platform
      ? items.filter(p => p.channels?.some(c => c.platform === filters.value.platform) || p.platforms?.includes(filters.value.platform))
      : items
    posts.value.push(...filtered)
    hasMore.value = items.length === PAGE_SIZE
  } catch {
    hasMore.value = false
  } finally {
    loadingMore.value = false
  }
}

function resetFilters() {
  filters.value = { status: '', platform: '' }
  load()
}

async function approve(id) {
  try {
    await smartPostApi.approveDraft(id)
    posts.value = posts.value.map(p => (p.id === id || p.post_id === id) ? { ...p, status: 'approved' } : p)
  } catch { /* ignore */ }
}

async function reject(id) {
  try {
    await smartPostApi.rejectDraft(id)
    posts.value = posts.value.map(p => (p.id === id || p.post_id === id) ? { ...p, status: 'rejected' } : p)
  } catch { /* ignore */ }
}

onMounted(load)
</script>
