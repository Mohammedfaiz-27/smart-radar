import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { smartPostApi } from '@/services/smartpost'

const AUTO_EMAIL    = import.meta.env.VITE_OMNIPUSH_AUTO_EMAIL
const AUTO_PASSWORD = import.meta.env.VITE_OMNIPUSH_AUTO_PASSWORD

export const useSmartPostStore = defineStore('smartpost', () => {
  const token         = ref(localStorage.getItem('op_token')     || null)
  const tenantId      = ref(localStorage.getItem('op_tenant_id') || null)
  const user          = ref(JSON.parse(localStorage.getItem('op_user') || 'null'))
  const socialAccounts = ref([])
  const pendingDrafts  = ref([])
  const loading        = ref(false)
  const error          = ref(null)

  const isAuthenticated = computed(() => !!token.value && !!tenantId.value)

  // ── Auth ──────────────────────────────────────────────────────────────

  async function signin(email, password) {
    loading.value = true
    error.value   = null
    try {
      const res = await smartPostApi.signin(email, password)
      const data = res.data
      token.value    = data.access_token
      tenantId.value = data.user?.tenant_id || data.tenant_id
      user.value     = data.user || null
      localStorage.setItem('op_token',     token.value)
      localStorage.setItem('op_tenant_id', tenantId.value)
      localStorage.setItem('op_user',      JSON.stringify(user.value))
      await fetchSocialAccounts()
      return true
    } catch (e) {
      error.value = e.response?.data?.detail || 'Sign-in failed. Check your credentials.'
      return false
    } finally {
      loading.value = false
    }
  }

  function signout() {
    token.value    = null
    tenantId.value = null
    user.value     = null
    localStorage.removeItem('op_token')
    localStorage.removeItem('op_tenant_id')
    localStorage.removeItem('op_user')
    socialAccounts.value = []
    pendingDrafts.value  = []
  }

  // ── Auto-login on store init ───────────────────────────────────────────
  async function autoLogin() {
    if (isAuthenticated.value) return
    if (!AUTO_EMAIL || !AUTO_PASSWORD) return
    // Race against a 10 s timeout so a slow/missing OmniPush backend
    // never keeps loading = true forever across the whole app.
    const timeout = new Promise((_, reject) =>
      setTimeout(() => reject(new Error('auto-login timeout')), 10000)
    )
    try {
      await Promise.race([signin(AUTO_EMAIL, AUTO_PASSWORD), timeout])
    } catch {
      loading.value = false
    }
  }

  // ── Social Accounts ───────────────────────────────────────────────────

  async function fetchSocialAccounts() {
    try {
      const res = await smartPostApi.getSocialAccounts()
      socialAccounts.value = res.data?.accounts ?? res.data ?? []
    } catch {
      socialAccounts.value = []
    }
  }

  // ── Publishing ────────────────────────────────────────────────────────

  async function publishNow(payload) {
    loading.value = true
    error.value   = null
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

  // ── Drafts ────────────────────────────────────────────────────────────

  async function fetchPendingDrafts() {
    try {
      const res = await smartPostApi.getPendingDrafts()
      pendingDrafts.value = res.data?.items || res.data || []
    } catch {
      pendingDrafts.value = []
    }
  }

  // Kick off auto-login immediately
  autoLogin()

  return {
    token, tenantId, user,
    socialAccounts, pendingDrafts,
    loading, error, isAuthenticated,
    signin, signout, autoLogin,
    fetchSocialAccounts, publishNow, fetchPendingDrafts,
  }
})
