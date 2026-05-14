/**
 * OmniPush API client
 * Connects to the OmniPush backend for all publishing features.
 * Auth: JWT Bearer token + X-Tenant-ID header on every request.
 */
import axios from 'axios'

// In dev: Vite proxy routes /v1/ → localhost:8001
// In prod: nginx proxy routes /v1/ → omnipush:8001
// Use empty base so paths are relative to current origin
const client = axios.create({ baseURL: '', timeout: 20000 })

// Inject auth headers on every request
client.interceptors.request.use((config) => {
  const token    = localStorage.getItem('op_token')
  const tenantId = localStorage.getItem('op_tenant_id')
  if (token)    config.headers['Authorization'] = `Bearer ${token}`
  if (tenantId) config.headers['X-Tenant-ID']  = tenantId
  return config
})

export const smartPostApi = {
  // ── Auth ──────────────────────────────────────────────────────────────
  signin:  (email, password) =>
    client.post('/v1/auth/signin',  { email, password }),
  signup:  (payload) =>
    client.post('/v1/auth/signup',  payload),
  refresh: (refreshToken) =>
    client.post('/v1/auth/refresh', { refresh_token: refreshToken }),

  // ── Social Accounts ───────────────────────────────────────────────────
  getSocialAccounts: () =>
    client.get('/v1/social-accounts'),

  // ── Publishing ────────────────────────────────────────────────────────
  publishNow: (payload) =>
    client.post('/v1/posts/publish-now', payload),

  // ── Scheduling ────────────────────────────────────────────────────────
  schedulePost: (postId, scheduledAt) =>
    client.post(`/v1/posts/${postId}/schedule`, { scheduled_at: scheduledAt }),
  getCalendar: (params = {}) =>
    client.get('/v1/calendar', { params }),

  // ── AI Content ────────────────────────────────────────────────────────
  getContentSuggestions: (payload) =>
    client.post('/v1/ai/content-suggestions', payload),

  // ── Media ─────────────────────────────────────────────────────────────
  getMedia:     ()     => client.get('/v1/media'),
  uploadMedia:  (form) => client.post('/v1/media/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  searchImages: (payload) => client.post('/v1/media/search-images', payload),

  // ── Drafts / Approval ─────────────────────────────────────────────────
  getPendingDrafts: (params = {}) =>
    client.get('/v1/drafts/pending', { params }),
  approveDraft: (id, data = {}) =>
    client.put(`/v1/drafts/${id}/approve`, data),
  rejectDraft:  (id, rejection_reason = '') =>
    client.put(`/v1/drafts/${id}/reject`,  { rejection_reason }),
  publishDraft: (id, newscard_url = null) =>
    client.post(`/v1/drafts/${id}/publish`, newscard_url ? { newscard_url } : {}),

  // ── Analytics ─────────────────────────────────────────────────────────
  getAnalyticsDashboard: (params = {}) =>
    client.get('/v1/analytics/dashboard', { params }),
  getPostAnalytics: (postId) =>
    client.get(`/v1/analytics/posts/${postId}`),
  getInsights: () =>
    client.get('/v1/analytics/insights'),

  // ── News Card ─────────────────────────────────────────────────────────
  generateNewsCard: (payload) =>
    client.post('/v1/posts/news-card', payload),

  // ── Social Accounts (extended) ────────────────────────────────────────
  getAllSocialAccounts: () => client.get('/v1/social-accounts/all'),
  connectSocialAccount: (payload) => client.post('/v1/social-accounts/connect', payload),
  disconnectSocialAccount: (id) => client.delete(`/v1/social-accounts/${id}`),
  refreshSocialToken: (id) => client.post(`/v1/social-accounts/${id}/refresh-token`),
  validateCredentials: (payload) => client.post('/v1/social-accounts/validate-credentials', payload),
  getConnectionRequirements: (platform) => client.get(`/v1/social-accounts/connection-requirements/${platform}`),

  // ── Templates ─────────────────────────────────────────────────────────
  getTemplates: (params = {}) => client.get('/v1/templates/', { params }),
  getTemplate: (id) => client.get(`/v1/templates/${id}`),
  toggleTemplateStatus: (id, is_active) => client.put(`/v1/templates/${id}`, { is_active }),
  bulkActivateTemplates: (ids) => client.post('/v1/templates/bulk/activate', { template_ids: ids }),

  // ── Channel Groups ────────────────────────────────────────────────────
  getChannelGroups: () => client.get('/v1/channel-groups'),
  createChannelGroup: (payload) => client.post('/v1/channel-groups', payload),
  updateChannelGroup: (id, payload) => client.put(`/v1/channel-groups/${id}`, payload),
  deleteChannelGroup: (id) => client.delete(`/v1/channel-groups/${id}`),

  // ── Workflows ─────────────────────────────────────────────────────────
  getWorkflows: () => client.get('/v1/workflows'),
  createWorkflow: (payload) => client.post('/v1/workflows', payload),
  setDefaultWorkflow: (id) => client.post(`/v1/workflows/${id}/set-default`),
  deleteWorkflow: (id) => client.delete(`/v1/workflows/${id}`),

  // ── Automation / Cron ─────────────────────────────────────────────────
  getCronJobs: () => client.get('/v1/automation/cron-jobs'),
  createCronJob: (payload) => client.post('/v1/automation/cron-jobs', payload),
  updateCronJob: (id, payload) => client.put(`/v1/automation/cron-jobs/${id}`, payload),
  deleteCronJob: (id) => client.delete(`/v1/automation/cron-jobs/${id}`),
  getNewsSettings: () => client.get('/v1/automation/news-settings'),
  updateNewsSettings: (payload) => client.post('/v1/automation/news-settings', payload),
  fetchNews: () => client.post('/v1/automation/fetch-news'),

  // ── Pipelines ─────────────────────────────────────────────────────────
  getPipelines: () => client.get('/v1/pipelines'),
  createPipeline: (payload) => client.post('/v1/pipelines', payload),
  deletePipeline: (id) => client.delete(`/v1/pipelines/${id}`),
  fetchPipelineNews: (id) => client.post(`/v1/pipelines/${id}/fetch-news`),
  getPipelineNews: (id) => client.get(`/v1/pipelines/${id}/news`),

  // ── External News ─────────────────────────────────────────────────────
  getExternalNews: (params = {}) => client.get('/v1/external-news/', { params }),
  approveExternalNews: (id) => client.put(`/v1/external-news/${id}/approve`),
  rejectExternalNews: (id, rejection_reason) => client.put(`/v1/external-news/${id}/reject`, { rejection_reason }),
  publishExternalNews: (id, payload = {}) => client.post(`/v1/external-news/${id}/publish`, payload),

  // ── Scraper ───────────────────────────────────────────────────────────
  getScraperJobs: () => client.get('/v1/scraper/jobs'),
  createScraperJob: (payload) => client.post('/v1/scraper/jobs', payload),
  runScraperJob: (id) => client.post(`/v1/scraper/jobs/${id}/run`),
  enableScraperJob: (id) => client.post(`/v1/scraper/jobs/${id}/enable`),
  disableScraperJob: (id) => client.post(`/v1/scraper/jobs/${id}/disable`),
  deleteScraperJob: (id) => client.delete(`/v1/scraper/jobs/${id}`),
  getScraperRuns: (id) => client.get(`/v1/scraper/jobs/${id}/runs`),

  // ── Moderation ────────────────────────────────────────────────────────
  moderateContent: (payload) => client.post('/v1/moderation/moderate', payload),

  // ── Dashboard ─────────────────────────────────────────────────────────
  getDashboardStats: () => client.get('/v1/dashboard/stats'),
  getDashboardOverview: () => client.get('/v1/dashboard/overview'),

  // ── AI (extended) ─────────────────────────────────────────────────────
  optimizeContent: (payload) => client.post('/v1/ai/optimize-content', payload),
  getContentIdeas: (payload) => client.post('/v1/ai/content-ideas', payload),
  getAiUsage: () => client.get('/v1/ai/usage'),

  // ── Posts (CRUD) ─────────────────────────────────────────────────────
  getPosts: (params = {}) => client.get('/v1/posts', { params }),
  createPost: (payload) => client.post('/v1/posts', payload),

  // ── Draft create (legacy alias → POST /v1/posts) ──────────────────────
  createDraft: (payload) => client.post('/v1/posts', payload),

  // ── Narratives (smartradar backend /api/v1/) ──────────────────────────
  getNarratives: (params = {}) => client.get('/api/v1/narratives/', { params }),
  createNarrative: (payload) => client.post('/api/v1/narratives/', payload),
  updateNarrative: (id, payload) => client.put(`/api/v1/narratives/${id}`, payload),
  deleteNarrative: (id) => client.delete(`/api/v1/narratives/${id}`),
  useNarrative: (id) => client.post(`/api/v1/narratives/${id}/use`),
  generateNarrativeContent: (title, category) =>
    client.post('/api/v1/narratives/generate-content', { title, category }),
}

export default smartPostApi
