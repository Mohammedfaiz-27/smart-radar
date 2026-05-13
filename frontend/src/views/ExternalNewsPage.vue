<template>
  <div class="p-6 max-w-5xl mx-auto">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">External News</h1>
        <p class="text-gray-500 mt-1">Review and publish news items collected from external sources.</p>
      </div>
      <!-- Status count chips -->
      <div class="flex items-center gap-2 flex-wrap">
        <span class="bg-yellow-100 text-yellow-700 text-xs font-medium px-3 py-1 rounded-full">
          {{ counts.pending }} Pending
        </span>
        <span class="bg-green-100 text-green-700 text-xs font-medium px-3 py-1 rounded-full">
          {{ counts.approved }} Approved
        </span>
        <span class="bg-red-100 text-red-700 text-xs font-medium px-3 py-1 rounded-full">
          {{ counts.rejected }} Rejected
        </span>
      </div>
    </div>

    <!-- Error Banner -->
    <div v-if="error" class="mb-5 bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
      <span class="text-red-500">⚠️</span>
      <span class="text-red-700 text-sm">{{ error }}</span>
      <button @click="error = null" class="ml-auto text-red-400 hover:text-red-600">✕</button>
    </div>

    <!-- Filter tabs -->
    <div class="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit mb-6">
      <button
        v-for="tab in filterTabs"
        :key="tab.key"
        @click="activeFilter = tab.key; applyFilter()"
        :class="[
          'px-4 py-1.5 rounded-lg text-sm font-medium transition-colors',
          activeFilter === tab.key ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
        ]"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 4" :key="i" class="bg-white rounded-2xl border border-gray-200 p-5 animate-pulse">
        <div class="h-5 bg-gray-200 rounded w-2/3 mb-2"></div>
        <div class="h-3 bg-gray-100 rounded w-1/3 mb-3"></div>
        <div class="h-12 bg-gray-100 rounded mb-3"></div>
        <div class="flex gap-2">
          <div class="h-8 bg-gray-100 rounded w-20"></div>
          <div class="h-8 bg-gray-100 rounded w-20"></div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="items.length === 0" class="flex flex-col items-center py-20 text-center">
      <span class="text-5xl mb-4">📰</span>
      <p class="text-gray-600 font-medium">No news items found</p>
      <p class="text-gray-400 text-sm mt-1">Check back later or switch filters.</p>
    </div>

    <!-- News cards -->
    <div v-else class="space-y-4">
      <div
        v-for="item in items"
        :key="item.id ?? item._id"
        class="bg-white rounded-2xl border border-gray-200 shadow-sm p-5"
      >
        <div class="flex items-start justify-between gap-4 mb-2">
          <h3 class="font-semibold text-gray-900 leading-snug flex-1">{{ item.title ?? item.headline }}</h3>
          <span
            :class="[
              'text-xs font-medium px-2 py-0.5 rounded-full shrink-0',
              item.approval_status === 'pending'  ? 'bg-yellow-100 text-yellow-700' :
              item.approval_status === 'approved' ? 'bg-green-100 text-green-700'   :
              item.approval_status === 'rejected' ? 'bg-red-100 text-red-700'       :
              'bg-gray-100 text-gray-500'
            ]"
          >{{ capitalize(item.approval_status ?? 'pending') }}</span>
        </div>

        <div class="flex items-center gap-3 text-xs text-gray-400 mb-3">
          <span v-if="item.source_name ?? item.external_source">{{ item.source_name ?? item.external_source }}</span>
          <span v-if="(item.source_name ?? item.external_source) && item.fetched_at">·</span>
          <span v-if="item.fetched_at ?? item.created_at">{{ formatDate(item.fetched_at ?? item.created_at) }}</span>
        </div>

        <p class="text-sm text-gray-600 line-clamp-2 mb-4">{{ item.content ?? item.summary ?? '' }}</p>

        <!-- Actions -->
        <div class="flex flex-wrap gap-2">
          <!-- Pending actions -->
          <template v-if="item.approval_status === 'pending'">
            <button
              @click="handleApprove(item.id ?? item._id)"
              :disabled="actioning === (item.id ?? item._id)"
              class="bg-green-600 hover:bg-green-700 text-white text-xs font-medium px-4 py-1.5 rounded-lg transition-colors disabled:opacity-50"
            >Approve</button>
            <button
              @click="openRejectModal(item)"
              :disabled="actioning === (item.id ?? item._id)"
              class="bg-red-600 hover:bg-red-700 text-white text-xs font-medium px-4 py-1.5 rounded-lg transition-colors disabled:opacity-50"
            >Reject</button>
          </template>

          <!-- Approved actions -->
          <template v-else-if="item.approval_status === 'approved'">
            <button
              @click="handlePublish(item.id ?? item._id)"
              :disabled="actioning === (item.id ?? item._id)"
              class="bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium px-4 py-1.5 rounded-lg transition-colors disabled:opacity-50"
            >Publish</button>
          </template>

          <!-- Actioning spinner -->
          <span v-if="actioning === (item.id ?? item._id)" class="text-xs text-gray-400 flex items-center">Processing…</span>
        </div>
      </div>
    </div>

    <!-- Pagination hint -->
    <div v-if="items.length > 0" class="mt-6 text-center text-xs text-gray-400">
      Showing {{ items.length }} items · Auto-refreshes every 30 s
    </div>

    <!-- Reject Modal -->
    <div v-if="showRejectModal" class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md">
        <div class="p-5 border-b border-gray-100 flex items-center justify-between">
          <h2 class="text-base font-semibold text-gray-900">Reject News Item</h2>
          <button @click="closeRejectModal" class="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <div class="p-5 space-y-4">
          <p class="text-sm text-gray-600 line-clamp-2 font-medium">
            {{ rejectingItem?.title ?? rejectingItem?.headline }}
          </p>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Reason (optional)</label>
            <textarea
              v-model="rejectReason"
              rows="3"
              placeholder="Explain why this item is being rejected…"
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400 resize-none"
            ></textarea>
          </div>
          <div class="flex gap-3">
            <button @click="closeRejectModal"
              class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium py-2 rounded-lg">Cancel</button>
            <button @click="handleReject" :disabled="actioning === (rejectingItem?.id ?? rejectingItem?._id)"
              class="flex-1 bg-red-600 hover:bg-red-700 text-white text-sm font-medium py-2 rounded-lg disabled:opacity-50">
              {{ actioning === (rejectingItem?.id ?? rejectingItem?._id) ? 'Rejecting…' : 'Reject' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { smartPostApi } from '@/services/smartpost.js'

const filterTabs = [
  { key: 'pending',  label: 'Pending'  },
  { key: 'approved', label: 'Approved' },
  { key: 'rejected', label: 'Rejected' },
  { key: '',         label: 'All'      },
]

const activeFilter   = ref('pending')
const allItems       = ref([])  // unfiltered master list — source for counts
const items          = ref([])  // filtered list — source for display
const loading        = ref(false)
const error          = ref(null)
const actioning      = ref(null)
const showRejectModal = ref(false)
const rejectingItem  = ref(null)
const rejectReason   = ref('')
let autoRefreshTimer = null

// Counts always reflect the full dataset, regardless of active tab
const counts = computed(() => ({
  pending:  allItems.value.filter(i => (i.approval_status ?? i.status) === 'pending').length,
  approved: allItems.value.filter(i => (i.approval_status ?? i.status) === 'approved').length,
  rejected: allItems.value.filter(i => (i.approval_status ?? i.status) === 'rejected').length,
}))

function applyFilter() {
  items.value = activeFilter.value
    ? allItems.value.filter(i => (i.approval_status ?? i.status) === activeFilter.value)
    : allItems.value
}

async function fetchItems() {
  loading.value = true
  error.value = null
  try {
    // Always fetch all items so counts are accurate across tabs
    const res = await smartPostApi.getExternalNews({})
    allItems.value = res.data?.items ?? res.data ?? []
    applyFilter()
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Failed to load news items.'
  } finally {
    loading.value = false
  }
}

async function handleApprove(id) {
  actioning.value = id
  try {
    await smartPostApi.approveExternalNews(id)
    // Update master list (keeps counts correct)
    const masterItem = allItems.value.find(i => (i.id ?? i._id) === id)
    if (masterItem) masterItem.approval_status = 'approved'
    // Remove from current filtered view if it no longer matches
    if (activeFilter.value === 'pending') items.value = items.value.filter(i => (i.id ?? i._id) !== id)
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Approval failed.'
  } finally {
    actioning.value = null
  }
}

function openRejectModal(item) {
  rejectingItem.value = item
  rejectReason.value = ''
  showRejectModal.value = true
}

function closeRejectModal() {
  showRejectModal.value = false
  rejectingItem.value = null
  rejectReason.value = ''
}

async function handleReject() {
  const id = rejectingItem.value?.id ?? rejectingItem.value?._id
  if (!id) return
  actioning.value = id
  try {
    await smartPostApi.rejectExternalNews(id, rejectReason.value)
    // Update master list (keeps counts correct)
    const masterItem = allItems.value.find(i => (i.id ?? i._id) === id)
    if (masterItem) masterItem.approval_status = 'rejected'
    // Remove from current filtered view if it no longer matches
    if (activeFilter.value === 'pending') items.value = items.value.filter(i => (i.id ?? i._id) !== id)
    closeRejectModal()
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Rejection failed.'
  } finally {
    actioning.value = null
  }
}

async function handlePublish(id) {
  actioning.value = id
  try {
    await smartPostApi.publishExternalNews(id)
    const item = items.value.find(i => (i.id ?? i._id) === id)
    if (item) item.status = 'published'
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Publish failed.'
  } finally {
    actioning.value = null
  }
}

function capitalize(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : ''
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString()
}

onMounted(() => {
  fetchItems()
  autoRefreshTimer = setInterval(fetchItems, 30_000)
})

onUnmounted(() => {
  clearInterval(autoRefreshTimer)
})
</script>
