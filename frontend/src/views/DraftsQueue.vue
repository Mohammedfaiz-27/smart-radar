<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-2xl font-bold text-gray-900">Drafts & Approvals</h2>
        <p class="text-sm text-gray-500 mt-1">Review and approve posts before publishing</p>
      </div>
      <div class="flex items-center space-x-3">
        <button @click="loadDrafts" class="text-sm text-gray-600 border border-gray-200 px-4 py-2 rounded-lg hover:bg-gray-50 flex items-center space-x-2">
          <svg class="w-4 h-4" :class="loading && 'animate-spin'" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span>Refresh</span>
        </button>
      </div>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-3 gap-4 mb-6">
      <div class="bg-white rounded-xl border border-gray-200 p-4">
        <p class="text-xs text-gray-500 font-medium uppercase mb-1">Pending</p>
        <p class="text-2xl font-bold text-orange-600">{{ pending.length }}</p>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-4">
        <p class="text-xs text-gray-500 font-medium uppercase mb-1">Approved</p>
        <p class="text-2xl font-bold text-green-600">{{ approvedCount }}</p>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-4">
        <p class="text-xs text-gray-500 font-medium uppercase mb-1">Rejected</p>
        <p class="text-2xl font-bold text-red-600">{{ rejectedCount }}</p>
      </div>
    </div>

    <!-- Empty -->
    <div v-if="!loading && pending.length === 0" class="bg-white rounded-2xl border border-gray-200 p-12 text-center">
      <div class="text-4xl mb-3">✅</div>
      <p class="text-gray-600 font-medium">No pending drafts</p>
      <p class="text-sm text-gray-400 mt-1">Posts sent for approval will appear here</p>
    </div>

    <!-- Loading skeletons -->
    <div v-if="loading" class="space-y-4">
      <div v-for="i in 3" :key="i" class="bg-white rounded-xl border border-gray-200 p-5 animate-pulse">
        <div class="h-4 bg-gray-100 rounded w-1/3 mb-3"></div>
        <div class="h-3 bg-gray-100 rounded w-full mb-2"></div>
        <div class="h-3 bg-gray-100 rounded w-2/3"></div>
      </div>
    </div>

    <!-- Draft cards -->
    <div v-if="!loading" class="space-y-4">
      <div v-for="draft in pending" :key="draft.id" class="bg-white rounded-xl border border-gray-200 p-5">
        <div class="flex items-start justify-between mb-3">
          <div class="flex-1 min-w-0">
            <div class="flex items-center space-x-2 mb-1">
              <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-800">
                Pending Review
              </span>
              <span class="text-xs text-gray-400">{{ formatDate(draft.created_at) }}</span>
            </div>
            <p class="text-sm font-medium text-gray-900 truncate">{{ draft.final_headline || draft.generated_headline || 'Untitled Draft' }}</p>
          </div>
          <div class="flex items-center space-x-2 ml-4 flex-shrink-0">
            <button
              @click="openRejectModal(draft)"
              class="text-xs px-3 py-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 transition-colors"
            >
              Reject
            </button>
            <button
              @click="approve(draft)"
              :disabled="actionLoading === draft.id"
              class="text-xs px-3 py-1.5 rounded-lg bg-green-600 hover:bg-green-700 text-white font-medium disabled:opacity-50"
            >
              {{ actionLoading === draft.id ? '…' : 'Approve' }}
            </button>
            <button
              @click="publishDraft(draft)"
              :disabled="actionLoading === draft.id"
              class="text-xs px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium disabled:opacity-50"
            >
              Publish Now
            </button>
          </div>
        </div>

        <div class="bg-gray-50 rounded-lg p-3 mb-3">
          <p class="text-sm text-gray-700 line-clamp-3">{{ draft.final_content || draft.generated_content || '—' }}</p>
        </div>

        <div v-if="draft.social_accounts" class="flex items-center space-x-2">
          <span class="text-xs text-gray-500">Account:</span>
          <span class="text-xs px-2 py-0.5 bg-gray-100 rounded text-gray-700">
            {{ getPlatformIcon(draft.social_accounts?.platform) }}
            {{ draft.social_accounts?.account_name || draft.social_accounts?.platform || '' }}
          </span>
        </div>
      </div>
    </div>

  </div>

  <!-- Reject modal -->
  <div v-if="rejectModal.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
    <div class="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
      <h3 class="text-lg font-semibold text-gray-900 mb-3">Reject Draft</h3>
      <textarea
        v-model="rejectModal.reason"
        rows="3"
        placeholder="Reason for rejection (optional)"
        class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400 resize-none mb-4"
      />
      <div class="flex justify-end space-x-3">
        <button @click="rejectModal.open = false" class="text-sm text-gray-500 px-4 py-2 hover:bg-gray-100 rounded-lg">Cancel</button>
        <button @click="confirmReject" :disabled="!!actionLoading" class="text-sm bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50">
          Confirm Reject
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useSmartPostStore } from '@/stores/smartpost'
import { smartPostApi } from '@/services/smartpost'

const store = useSmartPostStore()
const smartPostStore = store
const loading = ref(false)
const actionLoading = ref(null)
const pending = ref([])
const approvedCount = ref(0)
const rejectedCount = ref(0)
const rejectModal = ref({ open: false, draft: null, reason: '' })

const platformIcons = { twitter: '🐦', facebook: '📘', linkedin: '💼', instagram: '📷', whatsapp: '💬' }
const getPlatformIcon = (id) => platformIcons[id] || '📣'

async function loadDrafts() {
  loading.value = true
  try {
    const res = await smartPostApi.getPendingDrafts()
    pending.value = res.data?.items ?? res.data ?? []
    smartPostStore.pendingDrafts = pending.value
  } catch {
    pending.value = []
  } finally {
    loading.value = false
  }
}

async function approve(draft) {
  actionLoading.value = draft.id
  try {
    await smartPostApi.approveDraft(draft.id)
    pending.value = pending.value.filter(d => d.id !== draft.id)
    smartPostStore.pendingDrafts = pending.value
    approvedCount.value++
  } finally {
    actionLoading.value = null
  }
}

async function publishDraft(draft) {
  actionLoading.value = draft.id
  try {
    await smartPostApi.publishDraft(draft.id)
    pending.value = pending.value.filter(d => d.id !== draft.id)
    smartPostStore.pendingDrafts = pending.value
    approvedCount.value++
  } finally {
    actionLoading.value = null
  }
}

function openRejectModal(draft) {
  rejectModal.value = { open: true, draft, reason: '' }
}

async function confirmReject() {
  const draft = rejectModal.value.draft
  if (!draft) return
  actionLoading.value = draft.id
  try {
    await smartPostApi.rejectDraft(draft.id, rejectModal.value.reason)
    pending.value = pending.value.filter(d => d.id !== draft.id)
    smartPostStore.pendingDrafts = pending.value
    rejectedCount.value++
    rejectModal.value.open = false
  } catch {
    // keep modal open if rejection fails
  } finally {
    actionLoading.value = null
  }
}

function formatDate(d) {
  if (!d) return ''
  const date = new Date(d)
  const diff = Date.now() - date
  const h = Math.floor(diff / 3600000)
  if (h < 1) return 'Just now'
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

onMounted(loadDrafts)
</script>
