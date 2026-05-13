<template>
  <div class="p-6 max-w-6xl mx-auto">
    <!-- Header -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Automation</h1>
      <p class="text-gray-500 mt-1">Schedule jobs, manage news pipelines, and configure automatic collection.</p>
    </div>

    <!-- Error Banner -->
    <div v-if="error" class="mb-5 bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
      <span class="text-red-500">⚠️</span>
      <span class="text-red-700 text-sm">{{ error }}</span>
      <button @click="error = null" class="ml-auto text-red-400 hover:text-red-600">✕</button>
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit mb-6">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        @click="activeTab = tab.key"
        :class="[
          'px-5 py-2 rounded-lg text-sm font-medium transition-colors',
          activeTab === tab.key ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
        ]"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- ═══════════════════════ CRON JOBS TAB ═══════════════════════ -->
    <div v-if="activeTab === 'cron'">
      <div class="flex items-center justify-between mb-4">
        <p class="text-sm text-gray-500">{{ cronJobs.length }} scheduled job{{ cronJobs.length !== 1 ? 's' : '' }}</p>
        <button @click="openCronModal()" class="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors">
          + New Cron Job
        </button>
      </div>

      <!-- Loading -->
      <div v-if="cronLoading" class="space-y-3">
        <div v-for="i in 3" :key="i" class="bg-white rounded-2xl border border-gray-200 p-5 animate-pulse">
          <div class="flex items-center gap-4">
            <div class="h-5 bg-gray-200 rounded w-1/4"></div>
            <div class="h-5 bg-gray-100 rounded w-1/3"></div>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-else-if="cronJobs.length === 0" class="flex flex-col items-center py-16 text-center">
        <span class="text-5xl mb-3">⏰</span>
        <p class="text-gray-600 font-medium">No cron jobs yet</p>
        <p class="text-gray-400 text-sm mt-1">Create your first scheduled job to get started.</p>
      </div>

      <!-- Job cards -->
      <div v-else class="space-y-3">
        <div
          v-for="job in cronJobs"
          :key="job.id ?? job._id"
          class="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 flex items-center gap-4"
        >
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <h3 class="font-semibold text-gray-900 text-sm truncate">{{ job.name }}</h3>
              <span
                :class="[
                  'text-xs px-2 py-0.5 rounded-full font-medium',
                  (job.is_enabled ?? job.is_active) !== false ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                ]"
              >{{ (job.is_enabled ?? job.is_active) !== false ? 'Active' : 'Paused' }}</span>
            </div>
            <div class="flex items-center gap-4 text-xs text-gray-400">
              <span class="font-mono bg-gray-50 px-2 py-0.5 rounded">{{ job.schedule ?? job.cron_expression }}</span>
              <span v-if="job.task_type ?? job.job_type">Type: {{ job.task_type ?? job.job_type }}</span>
              <span v-if="job.last_run">Last run: {{ formatDate(job.last_run) }}</span>
            </div>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button
              @click="openCronModal(job)"
              class="text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 px-3 py-1.5 rounded-lg transition-colors"
            >Edit</button>
            <button
              @click="handleDeleteCron(job.id ?? job._id)"
              :disabled="deletingCron === (job.id ?? job._id)"
              class="text-xs bg-red-50 hover:bg-red-100 text-red-600 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
            >{{ deletingCron === (job.id ?? job._id) ? '…' : 'Delete' }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════ PIPELINES TAB ═══════════════════════ -->
    <div v-if="activeTab === 'pipelines'">
      <div class="flex items-center justify-between mb-4">
        <p class="text-sm text-gray-500">{{ pipelines.length }} pipeline{{ pipelines.length !== 1 ? 's' : '' }}</p>
        <button @click="openPipelineModal()" class="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors">
          + New Pipeline
        </button>
      </div>

      <!-- Loading -->
      <div v-if="pipelineLoading" class="space-y-3">
        <div v-for="i in 3" :key="i" class="bg-white rounded-2xl border border-gray-200 p-5 animate-pulse h-24"></div>
      </div>

      <!-- Empty state -->
      <div v-else-if="pipelines.length === 0" class="flex flex-col items-center py-16 text-center">
        <span class="text-5xl mb-3">🔗</span>
        <p class="text-gray-600 font-medium">No pipelines configured</p>
        <p class="text-gray-400 text-sm mt-1">Add a news pipeline to start pulling content automatically.</p>
      </div>

      <!-- Pipeline cards -->
      <div v-else class="space-y-3">
        <div
          v-for="pl in pipelines"
          :key="pl.id ?? pl._id"
          class="bg-white rounded-2xl border border-gray-200 shadow-sm p-5"
        >
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <h3 class="font-semibold text-gray-900 text-sm truncate">{{ pl.name }}</h3>
                <span v-if="pl.news_count != null"
                  class="text-xs bg-blue-100 text-blue-700 font-medium px-2 py-0.5 rounded-full">
                  {{ pl.news_count }} items
                </span>
              </div>
              <p v-if="pl.description" class="text-xs text-gray-400 truncate mb-1">{{ pl.description }}</p>
              <p v-if="getPipelineKeywords(pl).length" class="text-xs text-gray-400">
                Keywords: {{ getPipelineKeywords(pl).join(', ') }}
              </p>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <button
                @click="handleFetchPipeline(pl.id ?? pl._id)"
                :disabled="fetchingPipeline === (pl.id ?? pl._id)"
                class="text-xs bg-blue-50 hover:bg-blue-100 text-blue-700 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
              >{{ fetchingPipeline === (pl.id ?? pl._id) ? 'Fetching…' : 'Fetch Now' }}</button>
              <button
                @click="handleDeletePipeline(pl.id ?? pl._id)"
                :disabled="deletingPipeline === (pl.id ?? pl._id)"
                class="text-xs bg-red-50 hover:bg-red-100 text-red-600 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
              >{{ deletingPipeline === (pl.id ?? pl._id) ? '…' : 'Delete' }}</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════ NEWS SETTINGS TAB ═══════════════════════ -->
    <div v-if="activeTab === 'settings'">
      <div v-if="settingsLoading" class="bg-white rounded-2xl border border-gray-200 p-8 animate-pulse space-y-4">
        <div v-for="i in 4" :key="i" class="h-10 bg-gray-100 rounded"></div>
      </div>

      <div v-else class="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 max-w-lg">
        <h2 class="text-base font-semibold text-gray-900 mb-5">News Collection Settings</h2>

        <div class="space-y-5">
          <!-- Auto-fetch toggle -->
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-800">Auto-fetch enabled</p>
              <p class="text-xs text-gray-400">Automatically fetch news on schedule</p>
            </div>
            <button
              @click="settings.enabled = !settings.enabled"
              :class="[
                'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                settings.enabled ? 'bg-blue-600' : 'bg-gray-200'
              ]"
            >
              <span
                :class="[
                  'inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform',
                  settings.enabled ? 'translate-x-6' : 'translate-x-1'
                ]"
              ></span>
            </button>
          </div>

          <!-- Max articles per run -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Max Articles Per Run</label>
            <input
              v-model.number="settings.max_articles_per_run"
              type="number"
              min="1"
              max="50"
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <!-- Auto-publish toggle -->
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-800">Auto-publish approved news</p>
              <p class="text-xs text-gray-400">Publish approved items immediately</p>
            </div>
            <button
              @click="settings.auto_publish = !settings.auto_publish"
              :class="[
                'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                settings.auto_publish ? 'bg-blue-600' : 'bg-gray-200'
              ]"
            >
              <span
                :class="[
                  'inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform',
                  settings.auto_publish ? 'translate-x-6' : 'translate-x-1'
                ]"
              ></span>
            </button>
          </div>

          <!-- Categories -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Categories (comma-separated)</label>
            <input
              v-model="contentFiltersRaw"
              type="text"
              placeholder="e.g. technology, politics, sports"
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div class="flex gap-3 mt-6">
          <button
            @click="handleSaveSettings"
            :disabled="savingSettings"
            class="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-5 py-2 rounded-lg transition-colors disabled:opacity-50"
          >{{ savingSettings ? 'Saving…' : 'Save Settings' }}</button>
          <button
            @click="handleTestFetch"
            :disabled="testFetching"
            class="bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium px-5 py-2 rounded-lg transition-colors disabled:opacity-50"
          >{{ testFetching ? 'Fetching…' : 'Test Fetch' }}</button>
        </div>

        <div v-if="settingsSaved" class="mt-4 bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-700">
          Settings saved successfully.
        </div>
      </div>
    </div>

    <!-- ═══════════════════════ CRON JOB MODAL ═══════════════════════ -->
    <div v-if="showCronModal" class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md">
        <div class="p-5 border-b border-gray-100 flex items-center justify-between">
          <h2 class="text-base font-semibold text-gray-900">{{ editingCron ? 'Edit' : 'New' }} Cron Job</h2>
          <button @click="closeCronModal" class="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <form @submit.prevent="handleSaveCron" class="p-5 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Job Name</label>
            <input v-model="cronForm.name" required placeholder="e.g. Daily News Fetch"
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Cron Expression</label>
            <input v-model="cronForm.schedule" required placeholder="e.g. 0 */6 * * *"
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500" />
            <p class="text-xs text-gray-400 mt-1">Format: minute hour day month weekday</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Task Type</label>
            <select v-model="cronForm.task_type"
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="news_fetch">Fetch News</option>
              <option value="scheduled_posts">Scheduled Posts</option>
              <option value="analytics_sync">Analytics Sync</option>
            </select>
          </div>
          <div v-if="cronModalError" class="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
            {{ cronModalError }}
          </div>
          <div class="flex gap-3 pt-1">
            <button type="button" @click="closeCronModal"
              class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium py-2 rounded-lg">Cancel</button>
            <button type="submit" :disabled="savingCron"
              class="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium py-2 rounded-lg disabled:opacity-50">
              {{ savingCron ? 'Saving…' : 'Save' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- ═══════════════════════ PIPELINE MODAL ═══════════════════════ -->
    <div v-if="showPipelineModal" class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md">
        <div class="p-5 border-b border-gray-100 flex items-center justify-between">
          <h2 class="text-base font-semibold text-gray-900">New News Pipeline</h2>
          <button @click="closePipelineModal" class="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <form @submit.prevent="handleSavePipeline" class="p-5 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Pipeline Name</label>
            <input v-model="pipelineForm.name" required placeholder="e.g. Tech News RSS"
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Source URL</label>
            <input v-model="pipelineForm.source_url" required type="url" placeholder="https://example.com/rss"
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Keywords (comma-separated)</label>
            <input v-model="pipelineForm.keywords_raw" placeholder="e.g. AI, technology, startup"
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div v-if="pipelineModalError" class="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
            {{ pipelineModalError }}
          </div>
          <div class="flex gap-3 pt-1">
            <button type="button" @click="closePipelineModal"
              class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium py-2 rounded-lg">Cancel</button>
            <button type="submit" :disabled="savingPipeline"
              class="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium py-2 rounded-lg disabled:opacity-50">
              {{ savingPipeline ? 'Creating…' : 'Create' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { smartPostApi } from '@/services/smartpost.js'

const tabs = [
  { key: 'cron',      label: 'Cron Jobs'       },
  { key: 'pipelines', label: 'News Pipelines'  },
  { key: 'settings',  label: 'News Settings'   },
]
const activeTab = ref('cron')
const error = ref(null)

// ── Cron Jobs ────────────────────────────────────────────────────────────────
const cronJobs    = ref([])
const cronLoading = ref(false)
const deletingCron = ref(null)
const showCronModal = ref(false)
const editingCron   = ref(null)
const savingCron    = ref(false)
const cronModalError = ref(null)
const cronForm = ref({ name: '', schedule: '', task_type: 'news_fetch' })

async function fetchCronJobs() {
  cronLoading.value = true
  try {
    const res = await smartPostApi.getCronJobs()
    cronJobs.value = res.data?.jobs ?? res.data ?? []
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Failed to load cron jobs.'
  } finally {
    cronLoading.value = false
  }
}

function openCronModal(job = null) {
  editingCron.value = job
  cronModalError.value = null
  cronForm.value = job
    ? { name: job.name, schedule: job.schedule ?? job.cron_expression ?? '', task_type: job.task_type ?? job.job_type ?? 'news_fetch' }
    : { name: '', schedule: '', task_type: 'news_fetch' }
  showCronModal.value = true
}

function closeCronModal() {
  showCronModal.value = false
  editingCron.value = null
}

async function handleSaveCron() {
  savingCron.value = true
  cronModalError.value = null
  try {
    if (editingCron.value) {
      await smartPostApi.updateCronJob(editingCron.value.id ?? editingCron.value._id, cronForm.value)
    } else {
      await smartPostApi.createCronJob(cronForm.value)
    }
    await fetchCronJobs()
    closeCronModal()
  } catch (e) {
    cronModalError.value = e.response?.data?.detail ?? 'Failed to save cron job.'
  } finally {
    savingCron.value = false
  }
}

async function handleDeleteCron(id) {
  if (!confirm('Delete this cron job?')) return
  deletingCron.value = id
  try {
    await smartPostApi.deleteCronJob(id)
    cronJobs.value = cronJobs.value.filter(j => (j.id ?? j._id) !== id)
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Failed to delete cron job.'
  } finally {
    deletingCron.value = null
  }
}

// ── Pipelines ────────────────────────────────────────────────────────────────
const pipelines        = ref([])
const pipelineLoading  = ref(false)
const fetchingPipeline = ref(null)
const deletingPipeline = ref(null)
const showPipelineModal = ref(false)
const savingPipeline    = ref(false)
const pipelineModalError = ref(null)
const pipelineForm = ref({ name: '', source_url: '', keywords_raw: '' })

async function fetchPipelines() {
  pipelineLoading.value = true
  try {
    const res = await smartPostApi.getPipelines()
    pipelines.value = res.data?.pipelines ?? res.data ?? []
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Failed to load pipelines.'
  } finally {
    pipelineLoading.value = false
  }
}

function getPipelineKeywords(pl) {
  // Keywords may be in config.input_channels[0].config.keywords
  try {
    return pl.config?.input_channels?.[0]?.config?.keywords ?? pl.keywords ?? []
  } catch {
    return []
  }
}

function openPipelineModal() {
  pipelineModalError.value = null
  pipelineForm.value = { name: '', source_url: '', keywords_raw: '' }
  showPipelineModal.value = true
}

function closePipelineModal() {
  showPipelineModal.value = false
}

async function handleSavePipeline() {
  savingPipeline.value = true
  pipelineModalError.value = null
  try {
    const keywords = pipelineForm.value.keywords_raw
      ? pipelineForm.value.keywords_raw.split(',').map(k => k.trim()).filter(Boolean)
      : []
    const payload = {
      name: pipelineForm.value.name,
      description: pipelineForm.value.source_url ? `Source: ${pipelineForm.value.source_url}` : undefined,
      config: {
        input_channels: [{
          name: 'rss_input',
          type: 'input',
          platform: 'rss',
          config: {
            source_url: pipelineForm.value.source_url,
            keywords,
          },
        }],
        output_channels: [],
        processing_steps: ['text'],
        moderation_enabled: true,
        auto_publish: false,
      },
    }
    await smartPostApi.createPipeline(payload)
    await fetchPipelines()
    closePipelineModal()
  } catch (e) {
    pipelineModalError.value = e.response?.data?.detail ?? 'Failed to create pipeline.'
  } finally {
    savingPipeline.value = false
  }
}

async function handleFetchPipeline(id) {
  fetchingPipeline.value = id
  try {
    await smartPostApi.fetchPipelineNews(id)
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Fetch failed.'
  } finally {
    fetchingPipeline.value = null
  }
}

async function handleDeletePipeline(id) {
  if (!confirm('Delete this pipeline?')) return
  deletingPipeline.value = id
  try {
    await smartPostApi.deletePipeline(id)
    pipelines.value = pipelines.value.filter(p => (p.id ?? p._id) !== id)
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Failed to delete pipeline.'
  } finally {
    deletingPipeline.value = null
  }
}

// ── News Settings ────────────────────────────────────────────────────────────
const settings = ref({
  enabled: true,
  auto_publish: false,
  categories: [],
  max_articles_per_run: 5,
  schedule: '0 */2 * * *',
})
const contentFiltersRaw = ref('')
const settingsLoading = ref(false)
const savingSettings  = ref(false)
const testFetching    = ref(false)
const settingsSaved   = ref(false)

async function fetchNewsSettings() {
  settingsLoading.value = true
  try {
    const res = await smartPostApi.getNewsSettings()
    const data = res.data ?? {}
    settings.value = {
      enabled: data.enabled ?? data.auto_fetch_enabled ?? true,
      auto_publish: data.auto_publish ?? false,
      categories: data.categories ?? [],
      max_articles_per_run: data.max_articles_per_run ?? 5,
      schedule: data.schedule ?? '0 */2 * * *',
    }
    contentFiltersRaw.value = (settings.value.categories ?? []).join(', ')
  } catch {
    // silently handle — default values are already set
  } finally {
    settingsLoading.value = false
  }
}

async function handleSaveSettings() {
  savingSettings.value = true
  settingsSaved.value = false
  try {
    const payload = {
      enabled: settings.value.enabled,
      auto_publish: settings.value.auto_publish,
      categories: contentFiltersRaw.value
        ? contentFiltersRaw.value.split(',').map(k => k.trim()).filter(Boolean)
        : [],
      max_articles_per_run: settings.value.max_articles_per_run,
      schedule: settings.value.schedule,
    }
    await smartPostApi.updateNewsSettings(payload)
    settingsSaved.value = true
    setTimeout(() => { settingsSaved.value = false }, 3000)
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Failed to save settings.'
  } finally {
    savingSettings.value = false
  }
}

async function handleTestFetch() {
  testFetching.value = true
  try {
    await smartPostApi.fetchNews()
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Test fetch failed.'
  } finally {
    testFetching.value = false
  }
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

onMounted(() => {
  fetchCronJobs()
  fetchPipelines()
  fetchNewsSettings()
})
</script>
