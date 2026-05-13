<template>
  <div class="max-w-md">
    <div class="bg-white rounded-2xl border border-gray-200 p-8 shadow-sm">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
          </svg>
        </div>
        <div>
          <h3 class="text-lg font-semibold text-gray-900">Connect Publishing Account</h3>
          <p class="text-xs text-gray-500">Sign in to enable cross-platform publishing</p>
        </div>
      </div>

      <div class="space-y-3">
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Email</label>
          <input
            v-model="email"
            type="email"
            placeholder="your@email.com"
            @keydown.enter="signin"
            class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Password</label>
          <input
            v-model="password"
            type="password"
            placeholder="••••••••"
            @keydown.enter="signin"
            class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button
          @click="signin"
          :disabled="store.loading || !email || !password"
          class="w-full bg-blue-600 hover:bg-blue-700 text-white text-sm py-2.5 rounded-lg font-medium disabled:opacity-50 transition-colors flex items-center justify-center space-x-2"
        >
          <svg v-if="store.loading" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
          </svg>
          <span>{{ store.loading ? 'Connecting…' : 'Connect Account' }}</span>
        </button>
        <p v-if="store.error" class="text-xs text-red-500 text-center">{{ store.error }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useSmartPostStore } from '@/stores/smartpost'

const store = useSmartPostStore()
const email    = ref('')
const password = ref('')

async function signin() {
  if (!email.value || !password.value) return
  await store.signin(email.value, password.value)
}
</script>
