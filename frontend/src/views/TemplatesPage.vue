<template>
  <div class="p-6 max-w-6xl mx-auto">
    <!-- Header -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900">News Card Templates</h1>
      <p class="text-gray-500 mt-1">Browse and manage your news card design templates.</p>
    </div>

    <!-- Error Banner -->
    <div v-if="error" class="mb-5 bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
      <span class="text-red-500">⚠️</span>
      <span class="text-red-700 text-sm">{{ error }}</span>
      <button @click="error = null" class="ml-auto text-red-400 hover:text-red-600">✕</button>
    </div>

    <!-- Toolbar -->
    <div class="flex flex-col sm:flex-row gap-3 mb-6">
      <!-- Search -->
      <div class="relative flex-1 max-w-sm">
        <span class="absolute inset-y-0 left-3 flex items-center text-gray-400">🔍</span>
        <input
          v-model="search"
          type="text"
          placeholder="Search templates…"
          class="w-full border border-gray-200 rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <!-- Status filter -->
      <div class="flex rounded-lg border border-gray-200 overflow-hidden text-sm">
        <button
          v-for="f in statusFilters"
          :key="f.value"
          @click="statusFilter = f.value"
          :class="[
            'px-4 py-2 font-medium transition-colors',
            statusFilter === f.value
              ? 'bg-blue-600 text-white'
              : 'bg-white text-gray-600 hover:bg-gray-50'
          ]"
        >
          {{ f.label }}
        </button>
      </div>

      <!-- Bulk activate -->
      <button
        v-if="selectedIds.length > 0"
        @click="handleBulkActivate"
        :disabled="bulkLoading"
        class="bg-green-600 hover:bg-green-700 text-white text-sm font-medium px-4 py-2 rounded-lg disabled:opacity-50 transition-colors"
      >
        {{ bulkLoading ? 'Activating…' : `Activate (${selectedIds.length})` }}
      </button>
    </div>

    <!-- Summary line -->
    <div class="mb-4 text-sm text-gray-500" v-if="!loading">
      Showing <strong class="text-gray-700">{{ filtered.length }}</strong> of
      <strong class="text-gray-700">{{ templates.length }}</strong> templates
      <span v-if="activeCount > 0"> · <span class="text-green-600 font-medium">{{ activeCount }} active</span></span>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      <div v-for="i in 8" :key="i" class="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 animate-pulse">
        <div class="h-5 bg-gray-200 rounded w-3/4 mb-3"></div>
        <div class="h-4 bg-gray-100 rounded w-1/2 mb-4"></div>
        <div class="h-8 bg-gray-100 rounded-lg"></div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="filtered.length === 0" class="flex flex-col items-center justify-center py-20 text-center">
      <span class="text-5xl mb-4">🗂️</span>
      <p class="text-gray-600 font-medium">No templates found</p>
      <p class="text-gray-400 text-sm mt-1">Try adjusting your search or filter.</p>
    </div>

    <!-- Template Grid -->
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      <div
        v-for="tpl in filtered"
        :key="tpl.id ?? tpl._id"
        :class="[
          'bg-white rounded-2xl border shadow-sm p-5 flex flex-col gap-3 hover:shadow-md transition-shadow cursor-pointer',
          selectedIds.includes(tpl.id ?? tpl._id) ? 'border-blue-400 ring-1 ring-blue-400' : 'border-gray-200'
        ]"
        @click="toggleSelect(tpl.id ?? tpl._id)"
      >
        <!-- Template name -->
        <div class="flex-1">
          <h3 class="font-semibold text-gray-900 text-sm leading-snug">
            {{ tpl.template_display_name || cleanName(tpl.template_name || tpl.name || '') }}
          </h3>
          <p v-if="tpl.description" class="text-xs text-gray-400 mt-1 line-clamp-2">{{ tpl.description }}</p>
        </div>

        <!-- Status badge -->
        <div class="flex items-center justify-between">
          <span
            :class="[
              'text-xs font-medium px-2 py-0.5 rounded-full',
              tpl.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
            ]"
          >
            {{ tpl.is_active ? 'Active' : 'Inactive' }}
          </span>
          <input
            type="checkbox"
            :checked="selectedIds.includes(tpl.id ?? tpl._id)"
            @click.stop
            @change="toggleSelect(tpl.id ?? tpl._id)"
            class="rounded border-gray-300 text-blue-600"
          />
        </div>

        <!-- Toggle button -->
        <button
          @click.stop="handleToggle(tpl.id ?? tpl._id)"
          :disabled="toggling === (tpl.id ?? tpl._id)"
          :class="[
            'w-full text-sm font-medium py-1.5 rounded-lg transition-colors disabled:opacity-50',
            tpl.is_active
              ? 'bg-gray-100 hover:bg-gray-200 text-gray-700'
              : 'bg-blue-600 hover:bg-blue-700 text-white'
          ]"
        >
          {{ toggling === (tpl.id ?? tpl._id) ? '…' : (tpl.is_active ? 'Deactivate' : 'Activate') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { smartPostApi } from '@/services/smartpost.js'

const templates   = ref([])
const loading     = ref(false)
const error       = ref(null)
const search      = ref('')
const statusFilter = ref('all')
const toggling    = ref(null)
const bulkLoading = ref(false)
const selectedIds = ref([])

const statusFilters = [
  { label: 'All',      value: 'all'      },
  { label: 'Active',   value: 'active'   },
  { label: 'Inactive', value: 'inactive' },
]

const activeCount = computed(() => templates.value.filter(t => t.is_active).length)

const filtered = computed(() => {
  return templates.value.filter(t => {
    const displayName = t.template_display_name || t.name || ''
    const matchesSearch = !search.value ||
      displayName.toLowerCase().includes(search.value.toLowerCase()) ||
      cleanName(t.template_name || t.name || '').toLowerCase().includes(search.value.toLowerCase())
    const matchesStatus =
      statusFilter.value === 'all' ||
      (statusFilter.value === 'active' && t.is_active) ||
      (statusFilter.value === 'inactive' && !t.is_active)
    return matchesSearch && matchesStatus
  })
})

function cleanName(name = '') {
  // Remove common prefixes like "template_", "news_card_", etc.
  return name
    .replace(/^(template_|news_card_|card_)/i, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function toggleSelect(id) {
  const idx = selectedIds.value.indexOf(id)
  if (idx === -1) selectedIds.value.push(id)
  else selectedIds.value.splice(idx, 1)
}

async function fetchTemplates() {
  loading.value = true
  error.value = null
  try {
    const res = await smartPostApi.getTemplates()
    templates.value = res.data?.templates ?? res.data ?? []
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Failed to load templates.'
  } finally {
    loading.value = false
  }
}

async function handleToggle(id) {
  toggling.value = id
  try {
    const tpl = templates.value.find(t => (t.id ?? t._id) === id)
    if (!tpl) return
    const newActive = !tpl.is_active
    await smartPostApi.toggleTemplateStatus(id, newActive)
    tpl.is_active = newActive
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Failed to update template status.'
  } finally {
    toggling.value = null
  }
}

async function handleBulkActivate() {
  bulkLoading.value = true
  try {
    await smartPostApi.bulkActivateTemplates(selectedIds.value)
    selectedIds.value.forEach(id => {
      const tpl = templates.value.find(t => (t.id ?? t._id) === id)
      if (tpl) tpl.is_active = true
    })
    selectedIds.value = []
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Bulk activate failed.'
  } finally {
    bulkLoading.value = false
  }
}

onMounted(fetchTemplates)
</script>
