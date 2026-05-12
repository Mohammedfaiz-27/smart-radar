import { defineStore } from 'pinia'
import { ref } from 'vue'
import { smartPostApi } from '@/services/smartpost'

export const useSmartPostStore = defineStore('smartpost', () => {
  const socialAccounts = ref([])
  const pendingDrafts = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchSocialAccounts() {
    try {
      const res = await smartPostApi.getSocialAccounts()
      socialAccounts.value = res.data || []
    } catch {
      socialAccounts.value = []
    }
  }

  async function publishNow(payload) {
    loading.value = true
    error.value = null
    try {
      const res = await smartPostApi.publishNow(payload)
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Publish failed'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchPendingDrafts() {
    try {
      const res = await smartPostApi.getPendingDrafts()
      pendingDrafts.value = res.data || []
    } catch {
      pendingDrafts.value = []
    }
  }

  return {
    socialAccounts, pendingDrafts, loading, error,
    fetchSocialAccounts, publishNow, fetchPendingDrafts,
  }
})
