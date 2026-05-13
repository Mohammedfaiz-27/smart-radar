<template>
  <div class="p-6 max-w-6xl mx-auto">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Content Scraper</h1>
        <p class="text-gray-500 mt-1">Manage web scraper jobs and monitor their run history.</p>
      </div>
      <!-- Stats chips -->
      <div class="flex items-center gap-2 flex-wrap">
        <span class="bg-blue-100 text-blue-700 text-xs font-medium px-3 py-1 rounded-full">
          {{ jobs.length }} Total
        </span>
        <span class="bg-green-100 text-green-700 text-xs font-medium px-3 py-1 rounded-full">
          {{ activeJobs }} Active
        </span>
        <span class="bg-yellow-100 text-yellow-700 text-xs font-medium px-3 py-1 rounded-full">
          {{ runningJobs }} Running
        </span>
      </div>
    </div>

    <!-- Error Banner -->
    <div v-if="error" class="mb-5 bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
      <span class="text-red-500">⚠️</span>
      <span class="text-red-700 text-sm">{{ error }}</span>
      <button @click="error = null" class="ml-auto text-red-400 hover:text-red-600">✕</button>
    </div>

    <!-- Create button -->
    <div class="mb-5 flex justify-end">
      <button @click="openCreateModal"
        class="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors">
        + New Scraper Job
      </button>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="bg-white rounded-2xl border border-gray-200 p-5 animate-pulse">
        <div class="flex items-start gap-4">
          <div class="flex-1 space-y-2">
            <div class="h-5 bg-gray-200 rounded w-1/3"></div>
            <div class="h-3 bg-gray-100 rounded w-1/2"></div>
          </div>
          <div class="h-8 bg-gray-100 rounded w-24"></div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="jobs.length === 0" class="flex flex-col items-center py-20 text-center">
      <span class="text-5xl mb-4">🕷️</span>
      <p class="text-gray-600 font-medium">No scraper jobs yet</p>
      <p class="text-gray-400 text-sm mt-1">Create your first job to start scraping content.</p>
    </div>

    <!-- Job cards -->
    <div v-else class="space-y-3">
      <div
        v-for="job in jobs"
        :key="job.id ?? job._id"
        class="bg-white rounded-2xl border border-gray-200 shadow-sm p-5"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <h3 class="font-semibold text-gray-900 text-sm truncate">{{ job.name }}</h3>
              <span :class="statusBadge(job.status ?? ((job.is_enabled ?? job.is_active) ? 'active' : 'disabled'))">
                {{ capitalize(job.status ?? ((job.is_enabled ?? job.is_active) ? 'active' : 'disabled')) }}
              </span>
            </div>
            <p v-if="job.platforms?.length" class="text-xs text-gray-400 truncate mb-1">
              Platforms: {{ (job.platforms || []).join(', ') }}
            </p>
            <div class="flex items-center gap-3 text-xs text-gray-400">
              <span v-if="job.schedule_cron ?? job.schedule">Schedule: <span class="font-mono">{{ job.schedule_cron ?? job.schedule }}</span></span>
              <span v-if="job.last_run_at ?? job.last_run">Last run: {{ formatDate(job.last_run_at ?? job.last_run) }}</span>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-1.5 flex-wrap shrink-0">
            <button
              @click="handleRun(job.id ?? job._id)"
              :disabled="!!actioning[job.id ?? job._id]"
              class="text-xs bg-blue-50 hover:bg-blue-100 text-blue-700 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
            >{{ actioning[(job.id ?? job._id)] === 'run' ? 'Running…' : 'Run Now' }}</button>

            <button
              v-if="(job.is_enabled ?? job.is_active) !== false"
              @click="handleDisable(job.id ?? job._id)"
              :disabled="!!actioning[job.id ?? job._id]"
              class="text-xs bg-yellow-50 hover:bg-yellow-100 text-yellow-700 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
            >{{ actioning[(job.id ?? job._id)] === 'disable' ? '…' : 'Disable' }}</button>

            <button
              v-else
              @click="handleEnable(job.id ?? job._id)"
              :disabled="!!actioning[job.id ?? job._id]"
              class="text-xs bg-green-50 hover:bg-green-100 text-green-700 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
            >{{ actioning[(job.id ?? job._id)] === 'enable' ? '…' : 'Enable' }}</button>

            <button
              @click="openRunsModal(job)"
              class="text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 px-3 py-1.5 rounded-lg transition-colors"
            >View Runs</button>

            <button
              @click="handleDelete(job.id ?? job._id)"
              :disabled="!!actioning[job.id ?? job._id]"
              class="text-xs bg-red-50 hover:bg-red-100 text-red-600 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
            >{{ actioning[(job.id ?? job._id)] === 'delete' ? '…' : 'Delete' }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════ CREATE JOB MODAL ═══════════════════════ -->
    <div v-if="showCreateModal" class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md">
        <div class="p-5 border-b border-gray-100 flex items-center justify-between">
          <h2 class="text-base font-semibold text-gray-900">New Scraper Job</h2>
          <button @click="closeCreateModal" class="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <form @submit.prevent="handleCreate" class="p-5 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Job Name</label>
            <input v-model="createForm.name" required placeholder="e.g. Tech Blog Scraper"
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Platforms</label>
            <div class="flex flex-wrap gap-2">
              <label v-for="p in ['facebook','twitter','instagram']" :key="p" class="flex items-center gap-1.5 text-sm text-gray-700">
                <input type="checkbox" :value="p" v-model="createForm.platforms" class="rounded border-gray-300 text-blue-600" />
                {{ p.charAt(0).toUpperCase() + p.slice(1) }}
              </label>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Keywords (comma-separated)</label>
            <input v-model="createForm.keywords" placeholder="e.g. technology, startup, AI"
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Schedule (cron expression)</label>
            <input v-model="createForm.schedule_cron" placeholder="e.g. */30 * * * *"
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500" />
            <p class="text-xs text-gray-400 mt-1">Default: every 30 minutes.</p>
          </div>
          <div v-if="createModalError" class="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
            {{ createModalError }}
          </div>
          <div class="flex gap-3 pt-1">
            <button type="button" @click="closeCreateModal"
              class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium py-2 rounded-lg">Cancel</button>
            <button type="submit" :disabled="creating"
              class="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium py-2 rounded-lg disabled:opacity-50">
              {{ creating ? 'Creating…' : 'Create Job' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- ═══════════════════════ RUNS MODAL ═══════════════════════ -->
    <div v-if="showRunsModal" class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        <div class="p-5 border-b border-gray-100 flex items-center justify-between shrink-0">
          <div>
            <h2 class="text-base font-semibold text-gray-900">Run History</h2>
            <p class="text-xs text-gray-400 mt-0.5">{{ viewingJob?.name }}</p>
          </div>
          <button @click="closeRunsModal" class="text-gray-400 hover:text-gray-600">✕</button>
        </div>

        <div class="flex-1 overflow-y-auto p-5">
          <!-- Loading runs -->
          <div v-if="runsLoading" class="space-y-2">
            <div v-for="i in 4" :key="i" class="h-12 bg-gray-100 rounded-lg animate-pulse"></div>
          </div>

          <!-- Empty state -->
          <div v-else-if="runs.length === 0" class="flex flex-col items-center py-12 text-center">
            <span class="text-4xl mb-3">📋</span>
            <p class="text-gray-500 text-sm">No runs recorded yet.</p>
          </div>

          <!-- Runs list -->
          <div v-else class="space-y-2">
            <div
              v-for="run in runs"
              :key="run.id ?? run._id"
              class="flex items-center gap-4 bg-gray-50 rounded-xl px-4 py-3 text-sm"
            >
              <span class="font-mono text-xs text-gray-400 w-24 truncate">{{ (run.id ?? run._id)?.slice(-8) }}</span>
              <span :class="runStatusBadge(run.status)">{{ capitalize(run.status ?? 'unknown') }}</span>
              <span class="text-gray-500 flex-1">{{ formatDate(run.started_at ?? run.created_at) }}</span>
              <span v-if="(run.posts_found ?? run.items_scraped) != null" class="text-gray-600 font-medium shrink-0">
                {{ run.posts_found ?? run.items_scraped }} items
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { smartPostApi } from '@/services/smartpost.js'

const jobs    = ref([])
const loading = ref(false)
const error   = ref(null)
const actioning = ref({})

const activeJobs  = computed(() => jobs.value.filter(j => (j.is_enabled ?? j.is_active) !== false).length)
const runningJobs = computed(() => jobs.value.filter(j => j.status === 'running').length)

// Create modal
const showCreateModal  = ref(false)
const creating         = ref(false)
const createModalError = ref(null)
const createForm = ref({ name: '', platforms: ['facebook'], schedule_cron: '*/30 * * * *', keywords: '' })

// Runs modal
const showRunsModal = ref(false)
const viewingJob    = ref(null)
const runs          = ref([])
const runsLoading   = ref(false)

async function fetchJobs() {
  loading.value = true
  error.value = null
  try {
    const res = await smartPostApi.getScraperJobs()
    jobs.value = res.data?.jobs ?? (Array.isArray(res.data) ? res.data : [])
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Failed to load scraper jobs.'
  } finally {
    loading.value = false
  }
}

function openCreateModal() {
  createModalError.value = null
  createForm.value = { name: '', platforms: ['facebook'], schedule_cron: '*/30 * * * *', keywords: '' }
  showCreateModal.value = true
}

function closeCreateModal() {
  showCreateModal.value = false
}

async function handleCreate() {
  creating.value = true
  createModalError.value = null
  try {
    const keywords = createForm.value.keywords
      ? createForm.value.keywords.split(',').map(k => k.trim()).filter(Boolean)
      : []
    const payload = {
      name: createForm.value.name,
      platforms: createForm.value.platforms,
      schedule_cron: createForm.value.schedule_cron || '*/30 * * * *',
      keywords,
      is_enabled: true,
    }
    await smartPostApi.createScraperJob(payload)
    await fetchJobs()
    closeCreateModal()
  } catch (e) {
    createModalError.value = e.response?.data?.detail ?? 'Failed to create scraper job.'
  } finally {
    creating.value = false
  }
}

async function handleRun(id) {
  actioning.value = { ...actioning.value, [id]: 'run' }
  try {
    await smartPostApi.runScraperJob(id)
    const job = jobs.value.find(j => (j.id ?? j._id) === id)
    if (job) job.status = 'running'
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Failed to start job.'
  } finally {
    const copy = { ...actioning.value }
    delete copy[id]
    actioning.value = copy
  }
}

async function handleEnable(id) {
  actioning.value = { ...actioning.value, [id]: 'enable' }
  try {
    await smartPostApi.enableScraperJob(id)
    const job = jobs.value.find(j => (j.id ?? j._id) === id)
    if (job) { job.is_enabled = true; job.is_active = true }
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Failed to enable job.'
  } finally {
    const copy = { ...actioning.value }
    delete copy[id]
    actioning.value = copy
  }
}

async function handleDisable(id) {
  actioning.value = { ...actioning.value, [id]: 'disable' }
  try {
    await smartPostApi.disableScraperJob(id)
    const job = jobs.value.find(j => (j.id ?? j._id) === id)
    if (job) { job.is_enabled = false; job.is_active = false }
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Failed to disable job.'
  } finally {
    const copy = { ...actioning.value }
    delete copy[id]
    actioning.value = copy
  }
}

async function handleDelete(id) {
  if (!confirm('Delete this scraper job?')) return
  actioning.value = { ...actioning.value, [id]: 'delete' }
  try {
    await smartPostApi.deleteScraperJob(id)
    jobs.value = jobs.value.filter(j => (j.id ?? j._id) !== id)
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Failed to delete job.'
  } finally {
    const copy = { ...actioning.value }
    delete copy[id]
    actioning.value = copy
  }
}

async function openRunsModal(job) {
  viewingJob.value = job
  runs.value = []
  showRunsModal.value = true
  runsLoading.value = true
  try {
    const res = await smartPostApi.getScraperRuns(job.id ?? job._id)
    runs.value = res.data?.runs ?? res.data ?? []
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Failed to load run history.'
  } finally {
    runsLoading.value = false
  }
}

function closeRunsModal() {
  showRunsModal.value = false
  viewingJob.value = null
  runs.value = []
}

function statusBadge(status) {
  const base = 'text-xs font-medium px-2 py-0.5 rounded-full'
  const map = {
    active:   `${base} bg-green-100 text-green-700`,
    running:  `${base} bg-blue-100 text-blue-700`,
    disabled: `${base} bg-gray-100 text-gray-500`,
    error:    `${base} bg-red-100 text-red-600`,
  }
  return map[status] ?? `${base} bg-gray-100 text-gray-500`
}

function runStatusBadge(status) {
  const base = 'text-xs font-medium px-2 py-0.5 rounded-full shrink-0'
  const map = {
    completed: `${base} bg-green-100 text-green-700`,
    running:   `${base} bg-blue-100 text-blue-700`,
    failed:    `${base} bg-red-100 text-red-600`,
    pending:   `${base} bg-yellow-100 text-yellow-700`,
  }
  return map[status] ?? `${base} bg-gray-100 text-gray-500`
}

function capitalize(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : ''
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

onMounted(fetchJobs)
</script>
