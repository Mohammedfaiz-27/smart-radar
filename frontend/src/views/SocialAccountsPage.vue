<template>
  <div class="p-6 max-w-6xl mx-auto">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-gray-900">Social Accounts</h1>
      <p class="text-gray-500 mt-1">Connect and manage your social media accounts for publishing.</p>
    </div>

    <!-- Error Banner -->
    <div v-if="error" class="mb-6 bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
      <span class="text-red-500 text-lg">⚠️</span>
      <span class="text-red-700 text-sm">{{ error }}</span>
      <button @click="error = null" class="ml-auto text-red-400 hover:text-red-600">✕</button>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="i in 5" :key="i" class="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 animate-pulse">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-12 h-12 bg-gray-200 rounded-xl"></div>
          <div>
            <div class="h-4 bg-gray-200 rounded w-24 mb-2"></div>
            <div class="h-3 bg-gray-100 rounded w-16"></div>
          </div>
        </div>
        <div class="h-8 bg-gray-100 rounded-lg"></div>
      </div>
    </div>

    <!-- Platform Grid -->
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="platform in platforms"
        :key="platform.key"
        class="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 hover:shadow-md transition-shadow"
      >
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-3">
            <div :class="['w-12 h-12 rounded-xl flex items-center justify-center text-2xl', platform.bgColor]">
              {{ platform.icon }}
            </div>
            <div>
              <h3 class="font-semibold text-gray-900">{{ platform.label }}</h3>
              <p v-if="getAccount(platform.key)" class="text-xs text-gray-500 truncate max-w-[120px]">
                {{ getAccount(platform.key).account_name || getAccount(platform.key).account_id }}
              </p>
            </div>
          </div>
          <!-- Status Badge -->
          <span
            :class="[
              'text-xs font-medium px-2 py-1 rounded-full',
              getAccount(platform.key)
                ? 'bg-green-100 text-green-700'
                : 'bg-gray-100 text-gray-500'
            ]"
          >
            {{ getAccount(platform.key) ? 'Connected' : 'Disconnected' }}
          </span>
        </div>

        <!-- Action Button -->
        <button
          v-if="!getAccount(platform.key)"
          @click="openConnectModal(platform)"
          class="w-full bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium py-2 rounded-lg transition-colors"
        >
          Connect
        </button>
        <button
          v-else
          @click="handleDisconnect(getAccount(platform.key).id)"
          :disabled="disconnecting === getAccount(platform.key).id"
          class="w-full bg-gray-100 hover:bg-red-50 hover:text-red-600 hover:border-red-200 border border-gray-200 text-gray-700 text-sm font-medium py-2 rounded-lg transition-colors disabled:opacity-50"
        >
          {{ disconnecting === getAccount(platform.key).id ? 'Disconnecting…' : 'Disconnect' }}
        </button>
      </div>
    </div>

    <!-- Connect Modal -->
    <div v-if="showModal" class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md">
        <div class="p-6 border-b border-gray-100">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <span :class="['w-10 h-10 rounded-xl flex items-center justify-center text-xl', selectedPlatform?.bgColor]">
                {{ selectedPlatform?.icon }}
              </span>
              <h2 class="text-lg font-semibold text-gray-900">Connect {{ selectedPlatform?.label }}</h2>
            </div>
            <button @click="closeModal" class="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
          </div>
        </div>

        <form @submit.prevent="handleConnect" class="p-6 space-y-4">
          <!-- Facebook / Instagram -->
          <template v-if="selectedPlatform?.key === 'facebook' || selectedPlatform?.key === 'instagram'">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Access Token</label>
              <input
                v-model="form.access_token"
                type="password"
                required
                placeholder="Paste your access token"
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Account ID / Page ID</label>
              <input
                v-model="form.account_id"
                required
                placeholder="e.g. 123456789"
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </template>

          <!-- Twitter / X -->
          <template v-else-if="selectedPlatform?.key === 'twitter'">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">API Key</label>
              <input v-model="form.api_key" type="password" required placeholder="API Key"
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">API Secret</label>
              <input v-model="form.api_secret" type="password" required placeholder="API Secret"
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Access Token</label>
              <input v-model="form.access_token" type="password" required placeholder="Access Token"
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Access Token Secret</label>
              <input v-model="form.token_secret" type="password" required placeholder="Token Secret"
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </template>

          <!-- LinkedIn -->
          <template v-else-if="selectedPlatform?.key === 'linkedin'">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Access Token</label>
              <input v-model="form.access_token" type="password" required placeholder="OAuth Access Token"
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Account / Organization ID</label>
              <input v-model="form.account_id" required placeholder="urn:li:organization:..."
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </template>

          <!-- WhatsApp -->
          <template v-else-if="selectedPlatform?.key === 'whatsapp'">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Phone Number ID</label>
              <input v-model="form.phone_number_id" required placeholder="WhatsApp Phone Number ID"
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Access Token</label>
              <input v-model="form.access_token" type="password" required placeholder="Cloud API Access Token"
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </template>

          <!-- Modal error -->
          <div v-if="modalError" class="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
            {{ modalError }}
          </div>

          <div class="flex gap-3 pt-2">
            <button type="button" @click="closeModal"
              class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2 rounded-lg text-sm transition-colors">
              Cancel
            </button>
            <button type="submit" :disabled="connecting"
              class="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 rounded-lg text-sm transition-colors disabled:opacity-50">
              {{ connecting ? 'Connecting…' : 'Connect' }}
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

const platforms = [
  { key: 'facebook',  label: 'Facebook',    icon: '📘', bgColor: 'bg-blue-100'   },
  { key: 'instagram', label: 'Instagram',   icon: '📸', bgColor: 'bg-pink-100'   },
  { key: 'twitter',   label: 'Twitter / X', icon: '🐦', bgColor: 'bg-sky-100'    },
  { key: 'linkedin',  label: 'LinkedIn',    icon: '💼', bgColor: 'bg-indigo-100' },
  { key: 'whatsapp',  label: 'WhatsApp',    icon: '💬', bgColor: 'bg-green-100'  },
]

const accounts     = ref([])
const loading      = ref(false)
const error        = ref(null)
const connecting   = ref(false)
const disconnecting = ref(null)
const showModal    = ref(false)
const modalError   = ref(null)
const selectedPlatform = ref(null)
const form = ref({})

function getAccount(platformKey) {
  return accounts.value.find(a => a.platform === platformKey) || null
}

async function fetchAccounts() {
  loading.value = true
  error.value = null
  try {
    const res = await smartPostApi.getSocialAccounts()
    accounts.value = res.data?.accounts ?? res.data ?? []
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Failed to load social accounts.'
  } finally {
    loading.value = false
  }
}

function openConnectModal(platform) {
  selectedPlatform.value = platform
  form.value = {}
  modalError.value = null
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  selectedPlatform.value = null
  form.value = {}
  modalError.value = null
}

async function handleConnect() {
  connecting.value = true
  modalError.value = null
  try {
    const platformKey = selectedPlatform.value.key
    const payload = {
      platform: platformKey,
      connection_method: 'manual',
      account_name: form.value.account_id || form.value.phone_number_id || form.value.access_token?.slice(0, 16) || platformKey,
      access_token: form.value.access_token,
      // Platform-specific fields
      ...(platformKey === 'facebook' ? { page_id: form.value.account_id } : {}),
      ...(platformKey === 'whatsapp' ? { periskope_id: form.value.phone_number_id } : {}),
    }
    await smartPostApi.connectSocialAccount(payload)
    await fetchAccounts()
    closeModal()
  } catch (e) {
    modalError.value = e.response?.data?.detail ?? 'Connection failed. Please check your credentials.'
  } finally {
    connecting.value = false
  }
}

async function handleDisconnect(id) {
  disconnecting.value = id
  error.value = null
  try {
    await smartPostApi.disconnectSocialAccount(id)
    await fetchAccounts()
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Failed to disconnect account.'
  } finally {
    disconnecting.value = null
  }
}

onMounted(fetchAccounts)
</script>
