<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <p class="text-sm text-gray-500">Group social accounts to publish to multiple channels at once.</p>
      <button @click="showCreate = true" class="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-lg font-medium">
        + New Group
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="bg-white rounded-xl border border-gray-200 p-4 animate-pulse h-16"></div>
    </div>

    <!-- Empty -->
    <div v-else-if="groups.length === 0" class="bg-white rounded-2xl border border-gray-200 p-12 text-center">
      <div class="text-4xl mb-3">📣</div>
      <p class="text-gray-600 font-medium">No channel groups yet</p>
      <p class="text-sm text-gray-400 mt-1">Create groups to broadcast to multiple accounts at once</p>
    </div>

    <!-- Groups -->
    <div v-else class="space-y-3">
      <div v-for="group in groups" :key="group.id" class="bg-white rounded-xl border border-gray-200 p-4 flex items-center justify-between">
        <div>
          <p class="font-medium text-gray-900 text-sm">{{ group.name }}</p>
          <p class="text-xs text-gray-400 mt-0.5">{{ group.description || 'No description' }}</p>
          <div class="flex flex-wrap gap-1 mt-2">
            <span v-for="ch in (group.channels || [])" :key="ch" class="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
              {{ ch }}
            </span>
          </div>
        </div>
        <button @click="deleteGroup(group.id)" class="text-xs text-red-400 hover:text-red-600 ml-4">Delete</button>
      </div>
    </div>
  </div>

  <!-- Create Modal -->
  <div v-if="showCreate" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
    <div class="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
      <h3 class="text-lg font-semibold text-gray-900 mb-4">New Channel Group</h3>
      <div class="space-y-3">
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Group Name</label>
          <input v-model="form.name" placeholder="e.g. Tamil Nadu Channels" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Description</label>
          <input v-model="form.description" placeholder="Optional description" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
      </div>
      <div class="flex justify-end space-x-3 mt-5">
        <button @click="showCreate = false" class="text-sm text-gray-500 px-4 py-2 hover:bg-gray-100 rounded-lg">Cancel</button>
        <button @click="createGroup" :disabled="!form.name || saving" class="text-sm bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50">
          {{ saving ? 'Creating…' : 'Create' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { smartPostApi } from '@/services/smartpost'

const groups = ref([])
const loading = ref(false)
const saving = ref(false)
const showCreate = ref(false)
const form = ref({ name: '', description: '' })

async function load() {
  loading.value = true
  try {
    const res = await smartPostApi.getChannelGroups()
    groups.value = res.data || []
  } catch { groups.value = [] }
  finally { loading.value = false }
}

async function createGroup() {
  if (!form.value.name) return
  saving.value = true
  try {
    await smartPostApi.createChannelGroup({ name: form.value.name, description: form.value.description })
    showCreate.value = false
    form.value = { name: '', description: '' }
    await load()
  } finally { saving.value = false }
}

async function deleteGroup(id) {
  await smartPostApi.deleteChannelGroup(id)
  groups.value = groups.value.filter(g => g.id !== id)
}

onMounted(load)
</script>
