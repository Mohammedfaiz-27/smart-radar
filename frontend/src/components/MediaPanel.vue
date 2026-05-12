<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60">
    <div class="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto mx-4">
      <!-- Header -->
      <div class="flex items-center justify-between p-6 border-b border-gray-100">
        <div>
          <h2 class="text-xl font-bold text-gray-900">Media Library</h2>
          <p class="text-sm text-gray-500 mt-0.5">Upload or search for images to attach</p>
        </div>
        <button @click="emit('close')" class="text-gray-400 hover:text-gray-600 p-2 rounded-lg hover:bg-gray-100">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>

      <div class="p-6 space-y-5">
        <!-- Tabs -->
        <div class="flex space-x-1 bg-gray-100 rounded-xl p-1 w-fit">
          <button
            v-for="tab in ['upload', 'library', 'search']"
            :key="tab"
            @click="activeTab = tab"
            class="px-4 py-1.5 text-sm font-medium rounded-lg capitalize transition-all"
            :class="activeTab === tab ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'"
          >
            {{ tab }}
          </button>
        </div>

        <!-- Upload tab -->
        <div v-if="activeTab === 'upload'">
          <label
            class="flex flex-col items-center justify-center w-full h-40 border-2 border-dashed rounded-xl cursor-pointer transition-colors"
            :class="dragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400'"
            @dragover.prevent="dragOver = true"
            @dragleave="dragOver = false"
            @drop.prevent="onDrop"
          >
            <svg class="w-10 h-10 text-gray-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            <p class="text-sm text-gray-500">Drop files here or <span class="text-blue-600 font-medium">browse</span></p>
            <p class="text-xs text-gray-400 mt-1">PNG, JPG, GIF up to 10MB</p>
            <input type="file" accept="image/*" class="hidden" @change="onFileSelect" multiple />
          </label>

          <div v-if="uploading" class="mt-3 flex items-center space-x-2 text-sm text-blue-600">
            <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            <span>Uploading…</span>
          </div>

          <p v-if="uploadError" class="mt-2 text-sm text-red-500">{{ uploadError }}</p>
        </div>

        <!-- Library tab -->
        <div v-if="activeTab === 'library'">
          <div v-if="loadingMedia" class="grid grid-cols-3 gap-3">
            <div v-for="i in 6" :key="i" class="aspect-square bg-gray-100 rounded-xl animate-pulse"></div>
          </div>
          <div v-else-if="mediaItems.length === 0" class="py-10 text-center text-gray-400 text-sm">
            No media uploaded yet
          </div>
          <div v-else class="grid grid-cols-3 gap-3">
            <div
              v-for="item in mediaItems"
              :key="item.id"
              class="relative aspect-square rounded-xl overflow-hidden cursor-pointer group border-2 transition-all"
              :class="selectedMedia?.id === item.id ? 'border-blue-500' : 'border-transparent hover:border-gray-300'"
              @click="selectedMedia = item"
            >
              <img :src="item.url || item.thumbnail_url" :alt="item.filename" class="w-full h-full object-cover" />
              <div v-if="selectedMedia?.id === item.id" class="absolute inset-0 bg-blue-600 bg-opacity-20 flex items-center justify-center">
                <div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                  <svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Image search tab -->
        <div v-if="activeTab === 'search'">
          <div class="flex space-x-2 mb-4">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search images…"
              class="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              @keydown.enter="searchImages"
            />
            <button @click="searchImages" :disabled="searching || !searchQuery" class="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-50">
              Search
            </button>
          </div>
          <div v-if="searching" class="grid grid-cols-3 gap-3">
            <div v-for="i in 6" :key="i" class="aspect-square bg-gray-100 rounded-xl animate-pulse"></div>
          </div>
          <div v-else class="grid grid-cols-3 gap-3">
            <div
              v-for="item in searchResults"
              :key="item.id || item.url"
              class="relative aspect-square rounded-xl overflow-hidden cursor-pointer border-2 transition-all"
              :class="selectedMedia?.url === item.url ? 'border-blue-500' : 'border-transparent hover:border-gray-300'"
              @click="selectedMedia = item"
            >
              <img :src="item.thumbnail_url || item.url" :alt="item.alt || ''" class="w-full h-full object-cover" />
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex justify-between items-center pt-2 border-t border-gray-100">
          <span class="text-sm text-gray-400">{{ selectedMedia ? '1 selected' : 'Select an image' }}</span>
          <div class="flex space-x-3">
            <button @click="emit('close')" class="text-sm text-gray-500 px-4 py-2 hover:bg-gray-100 rounded-lg">Cancel</button>
            <button
              @click="confirmSelect"
              :disabled="!selectedMedia"
              class="text-sm bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50"
            >
              Attach
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { smartPostApi } from '@/services/smartpost'

const emit = defineEmits(['close', 'select'])

const activeTab = ref('upload')
const selectedMedia = ref(null)
const mediaItems = ref([])
const loadingMedia = ref(false)
const uploading = ref(false)
const uploadError = ref('')
const dragOver = ref(false)
const searchQuery = ref('')
const searchResults = ref([])
const searching = ref(false)

async function loadLibrary() {
  loadingMedia.value = true
  try {
    const res = await smartPostApi.getMedia()
    mediaItems.value = res.data?.items || res.data || []
  } catch {
    mediaItems.value = []
  } finally {
    loadingMedia.value = false
  }
}

async function uploadFiles(files) {
  if (!files.length) return
  uploading.value = true
  uploadError.value = ''
  try {
    const formData = new FormData()
    Array.from(files).forEach(f => formData.append('files', f))
    const res = await smartPostApi.uploadMedia(formData)
    const uploaded = res.data?.items || res.data || []
    if (uploaded.length) {
      selectedMedia.value = uploaded[0]
      emit('select', uploaded[0])
    }
  } catch {
    uploadError.value = 'Upload failed. Check file size and format.'
  } finally {
    uploading.value = false
  }
}

function onFileSelect(e) { uploadFiles(e.target.files) }
function onDrop(e) { dragOver.value = false; uploadFiles(e.dataTransfer.files) }

async function searchImages() {
  if (!searchQuery.value.trim()) return
  searching.value = true
  try {
    const res = await smartPostApi.searchImages(searchQuery.value)
    searchResults.value = res.data?.results || res.data || []
  } catch {
    searchResults.value = []
  } finally {
    searching.value = false
  }
}

function confirmSelect() {
  if (selectedMedia.value) {
    emit('select', selectedMedia.value)
  }
}

onMounted(loadLibrary)
</script>
