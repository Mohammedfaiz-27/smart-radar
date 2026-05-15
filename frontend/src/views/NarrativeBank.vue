<template>
  <div>
    <!-- Page Header -->
    <div class="max-w-7xl mx-auto px-6 py-6 bg-white border-b">
      <div class="flex justify-between items-start">
        <div>
          <h1 class="text-3xl font-bold text-gray-900">Narrative Bank</h1>
          <p class="text-gray-600 mt-1">Ready-to-use messaging templates for brand communication and response management</p>
        </div>
        <button
          @click="openAddModal"
          class="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg font-medium flex items-center"
        >
          <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
          </svg>
          Add Narrative
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="max-w-7xl mx-auto px-6 py-6">
      <div class="bg-white rounded-lg shadow-sm border p-4 mb-6">
        <div class="flex flex-wrap gap-4 items-center">
          <!-- Search -->
          <div class="flex-1 min-w-64">
            <div class="relative">
              <svg class="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
              </svg>
              <input
                v-model="searchQuery"
                type="text"
                placeholder="Search narratives..."
                class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
            </div>
          </div>

          <!-- Category Filter -->
          <div class="flex items-center gap-2">
            <label class="text-sm font-medium text-gray-700">Category:</label>
            <select
              v-model="selectedCategory"
              class="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Categories</option>
              <option value="brand">Brand Response</option>
              <option value="crisis">Crisis Management</option>
              <option value="executive">Executive Quote</option>
              <option value="achievement">Company Achievement</option>
              <option value="product">Product Update</option>
              <option value="customer">Customer Success</option>
            </select>
          </div>

          <!-- Priority Filter -->
          <div class="flex items-center gap-2">
            <label class="text-sm font-medium text-gray-700">Priority:</label>
            <select
              v-model="selectedPriority"
              class="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Priorities</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          <!-- Clear Filters -->
          <button
            @click="clearFilters"
            class="text-blue-600 hover:text-blue-800 font-medium text-sm flex items-center"
          >
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707v4.586a1 1 0 01-1.447.894l-4-2A1 1 0 018 15.586V11.414a1 1 0 00-.293-.707L1.293 4.293A1 1 0 011 3.586V2a1 1 0 011-1z"/>
            </svg>
            Clear Filters
          </button>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="flex justify-center py-16">
        <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-red-600"></div>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="text-center py-16 text-red-500">{{ error }}</div>

      <!-- Empty -->
      <div v-else-if="filteredNarratives.length === 0" class="text-center py-16 text-gray-500">
        <svg class="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
        <p class="text-lg font-medium">No narratives found</p>
        <p class="text-sm mt-1">Add your first narrative using the button above.</p>
      </div>

      <!-- Narratives Grid -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <div
          v-for="narrative in displayedNarratives"
          :key="narrative.id"
          class="bg-white rounded-lg shadow-sm border overflow-hidden hover:shadow-md transition-shadow"
          :class="getBorderClass(narrative.priority)"
        >
          <!-- Card Header -->
          <div class="p-4 pb-3">
            <div class="flex items-start justify-between mb-3">
              <div class="flex items-center">
                <div class="p-2 rounded-lg mr-3" :class="getIconBgClass(narrative.category)">
                  <component :is="getIcon(narrative.category)" class="w-5 h-5" :class="getIconColorClass(narrative.category)" />
                </div>
                <div>
                  <h3 class="font-semibold text-gray-900 text-base">{{ narrative.title }}</h3>
                  <p class="text-sm text-gray-600 capitalize">{{ narrative.category }}</p>
                </div>
              </div>
              <span
                class="px-2 py-1 text-xs font-medium rounded uppercase"
                :class="getPriorityClass(narrative.priority)"
              >
                {{ narrative.priority }}
              </span>
            </div>

            <!-- Description -->
            <p class="text-sm text-gray-700 leading-relaxed mb-4">{{ narrative.description }}</p>

            <!-- Tags -->
            <div class="flex flex-wrap gap-1 mb-4">
              <span
                v-for="tag in (narrative.tags || [])"
                :key="tag"
                class="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded font-medium"
              >
                {{ tag }}
              </span>
            </div>
          </div>

          <!-- Card Footer -->
          <div class="px-4 pb-4">
            <div class="flex items-center justify-between text-sm text-gray-600 mb-3">
              <span>Used {{ narrative.usage_count || 0 }} times</span>
              <span>{{ formatLastUsed(narrative.last_used) }}</span>
            </div>
            <div class="flex items-center justify-between">
              <button
                @click="handleUseNarrative(narrative)"
                class="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded font-medium text-sm flex items-center"
              >
                <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z"/>
                </svg>
                Use Now
              </button>
              <div class="flex items-center space-x-2">
                <button @click="openEditModal(narrative)" class="p-2 text-gray-400 hover:text-gray-600" title="Edit">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                  </svg>
                </button>
                <button @click="confirmDelete(narrative)" class="p-2 text-gray-400 hover:text-red-600" title="Delete">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Load More -->
      <div v-if="hasMore" class="text-center">
        <button
          @click="loadMore"
          class="bg-white border border-gray-300 text-gray-700 px-6 py-3 rounded-lg font-medium hover:bg-gray-50 transition-colors"
        >
          <svg class="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
          </svg>
          Load More Narratives
        </button>
      </div>
    </div>

    <!-- Add / Edit Modal -->
    <div v-if="showModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl shadow-2xl w-full max-w-lg">
        <div class="flex items-center justify-between p-6 border-b">
          <h2 class="text-xl font-bold text-gray-900">{{ editingNarrative ? 'Edit Narrative' : 'Add Narrative' }}</h2>
          <button @click="closeModal" class="text-gray-400 hover:text-gray-600">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <div class="p-6 space-y-4">
          <!-- Category & Priority (top so AI knows context when generating) -->
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <select v-model="form.category" class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                <option value="brand">Brand Response</option>
                <option value="crisis">Crisis Management</option>
                <option value="executive">Executive Quote</option>
                <option value="achievement">Company Achievement</option>
                <option value="product">Product Update</option>
                <option value="customer">Customer Success</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Priority</label>
              <select v-model="form.priority" class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-red-500 focus:border-transparent">
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>

          <!-- Title with Generate button -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Headline / Title *</label>
            <div class="flex gap-2">
              <input
                v-model="form.title"
                @keydown.enter.prevent="generateContent"
                type="text"
                placeholder="e.g. Our platform achieves 99.9% uptime for enterprise clients"
                class="flex-1 border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-red-500 focus:border-transparent"
              />
              <button
                @click="generateContent"
                :disabled="!form.title.trim() || generating"
                class="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium disabled:opacity-40 flex items-center gap-1 whitespace-nowrap"
              >
                <svg v-if="generating" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
                <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                </svg>
                {{ generating ? 'Generating...' : 'AI Generate' }}
              </button>
            </div>
            <p class="text-xs text-gray-400 mt-1">Enter headline then click "AI Generate" to auto-fill content</p>
          </div>

          <!-- AI-Generated Description -->
          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="block text-sm font-medium text-gray-700">Content</label>
              <span v-if="aiGenerated" class="text-xs text-blue-600 flex items-center gap-1">
                <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
                AI Generated
              </span>
            </div>
            <textarea
              v-model="form.description"
              rows="4"
              placeholder="Content will be AI-generated from your headline..."
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none"
              :class="aiGenerated ? 'bg-blue-50 border-blue-200' : ''"
            ></textarea>
          </div>

          <!-- Tags -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Tags (comma-separated)</label>
            <input
              v-model="tagsInput"
              type="text"
              placeholder="#BrandReputation, #CustomerSuccess, #ProductUpdate, ..."
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-red-500 focus:border-transparent"
            />
          </div>

          <!-- Modal error -->
          <p v-if="modalError" class="text-red-500 text-sm">{{ modalError }}</p>
        </div>

        <div class="flex justify-end gap-3 p-6 border-t">
          <button @click="closeModal" class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">Cancel</button>
          <button
            @click="saveNarrative"
            :disabled="saving"
            class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium disabled:opacity-50"
          >
            {{ saving ? 'Saving...' : (editingNarrative ? 'Update' : 'Create') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Delete Confirm Modal -->
    <div v-if="deletingNarrative" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl shadow-2xl w-full max-w-sm p-6">
        <h2 class="text-lg font-bold text-gray-900 mb-2">Delete Narrative?</h2>
        <p class="text-gray-600 text-sm mb-6">
          "<strong>{{ deletingNarrative.title }}</strong>" will be removed from your narrative bank.
        </p>
        <div class="flex justify-end gap-3">
          <button @click="deletingNarrative = null" class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">Cancel</button>
          <button
            @click="doDelete"
            :disabled="saving"
            class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium disabled:opacity-50"
          >
            {{ saving ? 'Deleting...' : 'Delete' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  TruckIcon,
  ChatBubbleLeftRightIcon,
  AcademicCapIcon,
  TrophyIcon,
  ShieldCheckIcon,
  HeartIcon
} from '@heroicons/vue/24/outline'
import { smartPostApi } from '@/services/smartpost.js'

// ── State ──────────────────────────────────────────────────────────────────
const narratives    = ref([])
const loading       = ref(false)
const error         = ref(null)
const searchQuery   = ref('')
const selectedCategory = ref('')
const selectedPriority = ref('')
const displayLimit  = ref(6)

// Modal
const showModal        = ref(false)
const editingNarrative = ref(null)
const deletingNarrative = ref(null)
const saving           = ref(false)
const generating       = ref(false)
const aiGenerated      = ref(false)
const modalError       = ref('')
const form             = ref({ title: '', description: '', category: 'brand', priority: 'medium', tags: [] })
const tagsInput        = ref('')

// ── Fetch ──────────────────────────────────────────────────────────────────
async function fetchNarratives() {
  loading.value = true
  error.value = null
  try {
    const res = await smartPostApi.getNarratives({ limit: 200 })
    narratives.value = res.data?.narratives || []
  } catch (e) {
    error.value = 'Failed to load narratives. Please try again.'
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchNarratives)

// ── Computed ───────────────────────────────────────────────────────────────
const filteredNarratives = computed(() => {
  let list = narratives.value
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(n =>
      n.title?.toLowerCase().includes(q) ||
      n.description?.toLowerCase().includes(q)
    )
  }
  if (selectedCategory.value) list = list.filter(n => n.category === selectedCategory.value)
  if (selectedPriority.value) list = list.filter(n => n.priority === selectedPriority.value)
  return list
})

const displayedNarratives = computed(() => filteredNarratives.value.slice(0, displayLimit.value))
const hasMore = computed(() => displayLimit.value < filteredNarratives.value.length)

// ── Actions ────────────────────────────────────────────────────────────────
function clearFilters() {
  searchQuery.value = ''
  selectedCategory.value = ''
  selectedPriority.value = ''
}

function loadMore() { displayLimit.value += 6 }

async function handleUseNarrative(narrative) {
  try {
    const res = await smartPostApi.useNarrative(narrative.id)
    const updated = res.data?.narrative
    if (updated) {
      const idx = narratives.value.findIndex(n => n.id === narrative.id)
      if (idx !== -1) narratives.value[idx] = updated
    }
  } catch (e) {
    console.error('Failed to record usage', e)
  }
}

// ── Modal helpers ──────────────────────────────────────────────────────────
function openAddModal() {
  editingNarrative.value = null
  form.value = { title: '', description: '', category: 'brand', priority: 'medium', tags: [] }
  tagsInput.value = ''
  modalError.value = ''
  aiGenerated.value = false
  showModal.value = true
}

function openEditModal(narrative) {
  editingNarrative.value = narrative
  form.value = {
    title:       narrative.title,
    description: narrative.description,
    category:    narrative.category,
    priority:    narrative.priority,
    tags:        narrative.tags || [],
  }
  tagsInput.value = (narrative.tags || []).join(', ')
  modalError.value = ''
  aiGenerated.value = false
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  editingNarrative.value = null
  aiGenerated.value = false
  modalError.value = ''
}

async function generateContent() {
  if (!form.value.title.trim() || generating.value) return
  generating.value = true
  modalError.value = ''
  try {
    const res = await smartPostApi.generateNarrativeContent(
      form.value.title.trim(),
      form.value.category
    )
    form.value.description = res.data?.description || ''
    aiGenerated.value = true
  } catch (e) {
    modalError.value = 'AI generation failed. Please write the content manually.'
  } finally {
    generating.value = false
  }
}

function parseTags(raw) {
  return raw.split(',').map(t => t.trim()).filter(Boolean)
}

async function saveNarrative() {
  if (!form.value.title.trim()) {
    modalError.value = 'Title is required.'
    return
  }
  if (!form.value.description.trim()) {
    modalError.value = 'Click "AI Generate" to generate content, or type it manually.'
    return
  }
  saving.value = true
  modalError.value = ''
  try {
    const payload = {
      title:       form.value.title.trim(),
      description: form.value.description.trim(),
      category:    form.value.category,
      priority:    form.value.priority,
      tags:        parseTags(tagsInput.value),
    }
    if (editingNarrative.value) {
      const res = await smartPostApi.updateNarrative(editingNarrative.value.id, payload)
      const updated = res.data?.narrative
      if (updated) {
        const idx = narratives.value.findIndex(n => n.id === editingNarrative.value.id)
        if (idx !== -1) narratives.value[idx] = updated
      }
    } else {
      const res = await smartPostApi.createNarrative(payload)
      const created = res.data?.narrative
      if (created) narratives.value.unshift(created)
    }
    closeModal()
  } catch (e) {
    modalError.value = e?.response?.data?.detail || 'Failed to save. Please try again.'
  } finally {
    saving.value = false
  }
}

function confirmDelete(narrative) { deletingNarrative.value = narrative }

async function doDelete() {
  if (!deletingNarrative.value) return
  saving.value = true
  try {
    await smartPostApi.deleteNarrative(deletingNarrative.value.id)
    narratives.value = narratives.value.filter(n => n.id !== deletingNarrative.value.id)
    deletingNarrative.value = null
  } catch (e) {
    console.error('Delete failed', e)
  } finally {
    saving.value = false
  }
}

// ── Display helpers ────────────────────────────────────────────────────────
function formatLastUsed(ts) {
  if (!ts) return 'Never used'
  const d = new Date(ts)
  const now = new Date()
  const diffMs = now - d
  const mins  = Math.floor(diffMs / 60000)
  const hours = Math.floor(diffMs / 3600000)
  const days  = Math.floor(diffMs / 86400000)
  if (mins < 60)  return `${mins}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days === 1) return '1 day ago'
  if (days < 30)  return `${days} days ago`
  return d.toLocaleDateString()
}

const getBorderClass = (priority) => ({
  high:   'border-l-4 border-l-green-500',
  medium: 'border-l-4 border-l-yellow-500',
  low:    'border-l-4 border-l-red-500',
}[priority] || 'border-l-4 border-l-gray-300')

const getPriorityClass = (priority) => ({
  high:   'bg-green-100 text-green-800',
  medium: 'bg-yellow-100 text-yellow-800',
  low:    'bg-red-100 text-red-800',
}[priority] || 'bg-gray-100 text-gray-800')

const getIcon = (category) => ({
  brand:       ShieldCheckIcon,
  crisis:      ShieldCheckIcon,
  executive:   ChatBubbleLeftRightIcon,
  achievement: TrophyIcon,
  product:     TruckIcon,
  customer:    HeartIcon,
}[category] || ChatBubbleLeftRightIcon)

const getIconBgClass = (category) => ({
  brand:       'bg-blue-100',
  crisis:      'bg-red-100',
  executive:   'bg-purple-100',
  achievement: 'bg-yellow-100',
  product:     'bg-green-100',
  customer:    'bg-teal-100',
}[category] || 'bg-gray-100')

const getIconColorClass = (category) => ({
  brand:       'text-blue-600',
  crisis:      'text-red-600',
  executive:   'text-purple-600',
  achievement: 'text-yellow-600',
  product:     'text-green-600',
  customer:    'text-teal-600',
}[category] || 'text-gray-600')
</script>
