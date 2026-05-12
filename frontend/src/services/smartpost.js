import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const client = axios.create({ baseURL: BASE })

export const smartPostApi = {
  getSocialAccounts: ()         => client.get('/v1/social-accounts'),
  publishNow: (payload)         => client.post('/v1/posts/publish-now', payload),
  schedulePost: (id, scheduledAt) => client.post(`/v1/posts/${id}/schedule`, { scheduled_at: scheduledAt }),
  getCalendar: (params = {})    => client.get('/v1/calendar', { params }),

  getContentSuggestions: (payload) => client.post('/v1/ai/content-suggestions', payload),

  searchImages: (q)             => client.get('/v1/media/search-images', { params: { q } }),
  uploadMedia: (formData)       => client.post('/v1/media/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  getMedia: ()                  => client.get('/v1/media'),

  getPendingDrafts: ()          => client.get('/v1/drafts/pending'),
  createDraft: (payload)        => client.post('/v1/drafts', payload),
  approveDraft: (id)            => client.post(`/v1/drafts/${id}/approve`),
  rejectDraft: (id, reason)     => client.post(`/v1/drafts/${id}/reject`, { reason }),
  publishDraft: (id)            => client.post(`/v1/drafts/${id}/publish`),

  getAnalyticsDashboard: (p={}) => client.get('/v1/analytics/dashboard', { params: p }),
  getPostAnalytics: (id)        => client.get(`/v1/analytics/posts/${id}`),
  getInsights: ()               => client.get('/v1/analytics/insights'),

  generateNewsCard: (payload)   => client.post('/v1/posts/news-card', payload),
}

export default smartPostApi
