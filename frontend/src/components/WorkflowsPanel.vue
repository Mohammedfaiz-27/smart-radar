<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <p class="text-sm text-gray-500">Define approval workflows for your content before publishing.</p>
      <button @click="showCreate = true" class="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-lg font-medium">
        + New Workflow
      </button>
    </div>

    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="bg-white rounded-xl border border-gray-200 p-4 animate-pulse h-20"></div>
    </div>

    <div v-else-if="workflows.length === 0" class="bg-white rounded-2xl border border-gray-200 p-12 text-center">
      <div class="text-4xl mb-3">⚙️</div>
      <p class="text-gray-600 font-medium">No workflows configured</p>
      <p class="text-sm text-gray-400 mt-1">Create workflows to enforce content approval before publishing</p>
    </div>

    <div v-else class="space-y-3">
      <div v-for="wf in workflows" :key="wf.id" class="bg-white rounded-xl border border-gray-200 p-4">
        <div class="flex items-center justify-between">
          <div>
            <div class="flex items-center space-x-2">
              <p class="font-medium text-gray-900 text-sm">{{ wf.name }}</p>
              <span v-if="wf.is_default" class="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Default</span>
            </div>
            <p class="text-xs text-gray-400 mt-0.5">{{ wf.description || 'No description' }}</p>
            <div class="flex items-center space-x-2 mt-2">
              <span class="text-xs text-gray-500">Steps:</span>
              <span v-for="(step, i) in (wf.steps || [])" :key="i" class="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                {{ step.name || step }}
              </span>
            </div>
          </div>
          <div class="flex items-center space-x-2 ml-4">
            <button v-if="!wf.is_default" @click="setDefault(wf.id)" class="text-xs text-blue-500 hover:text-blue-700 border border-blue-200 px-2 py-1 rounded">
              Set Default
            </button>
            <button @click="deleteWf(wf.id)" class="text-xs text-red-400 hover:text-red-600">Delete</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Create Modal -->
  <div v-if="showCreate" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
    <div class="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
      <h3 class="text-lg font-semibold text-gray-900 mb-4">New Workflow</h3>
      <div class="space-y-3">
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Name</label>
          <input v-model="form.name" placeholder="e.g. Editorial Review" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Description</label>
          <input v-model="form.description" placeholder="Optional description" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Approval Steps (comma-separated)</label>
          <input v-model="form.stepsRaw" placeholder="e.g. Editor Review, Manager Approval" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
      </div>
      <div class="flex justify-end space-x-3 mt-5">
        <button @click="showCreate = false" class="text-sm text-gray-500 px-4 py-2 hover:bg-gray-100 rounded-lg">Cancel</button>
        <button @click="createWf" :disabled="!form.name || saving" class="text-sm bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50">
          {{ saving ? 'Creating…' : 'Create' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { smartPostApi } from '@/services/smartpost'

const workflows = ref([])
const loading = ref(false)
const saving = ref(false)
const showCreate = ref(false)
const form = ref({ name: '', description: '', stepsRaw: '' })

async function load() {
  loading.value = true
  try {
    const res = await smartPostApi.getWorkflows()
    workflows.value = res.data?.workflows || res.data || []
  } catch { workflows.value = [] }
  finally { loading.value = false }
}

async function createWf() {
  saving.value = true
  try {
    const steps = form.value.stepsRaw.split(',').map(s => s.trim()).filter(Boolean)
    await smartPostApi.createWorkflow({ name: form.value.name, description: form.value.description, steps })
    showCreate.value = false
    form.value = { name: '', description: '', stepsRaw: '' }
    await load()
  } finally { saving.value = false }
}

async function setDefault(id) {
  await smartPostApi.setDefaultWorkflow(id)
  await load()
}

async function deleteWf(id) {
  await smartPostApi.deleteWorkflow(id)
  workflows.value = workflows.value.filter(w => w.id !== id)
}

onMounted(load)
</script>
