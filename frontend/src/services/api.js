import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Global emergency stop mechanism
let globalAbortController = new AbortController()
let isEmergencyStop = false

// Function to trigger emergency stop
window.emergencyStopAllRequests = () => {
  console.warn('🚨 EMERGENCY STOP: Killing all pending requests')
  isEmergencyStop = true
  globalAbortController.abort()
  globalAbortController = new AbortController()
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Environment-based configuration (moved up to avoid circular reference)
export const apiConfig = {
  version: import.meta.env.VITE_API_VERSION || '25.0',
  useUnifiedApi: import.meta.env.VITE_USE_UNIFIED_API === 'true',
  compatibilityMode: import.meta.env.VITE_BACKEND_COMPATIBILITY_MODE || 'legacy',
  enableMigrationTools: import.meta.env.VITE_ENABLE_MIGRATION_TOOLS === 'true',
  enableV24Intelligence: import.meta.env.VITE_ENABLE_V24_INTELLIGENCE === 'true',
  debugApi: import.meta.env.VITE_DEBUG_API === 'true'
}

// Global state for API features and version
let apiFeatures = {}
let apiVersion = '19.0'
let isApiInitialized = false

// Request interceptor to add global abort signal and emergency stop check
api.interceptors.request.use((config) => {
  if (isEmergencyStop) {
    console.warn('🚨 Request blocked by emergency stop')
    return Promise.reject(new Error('Emergency stop activated'))
  }
  
  // Add global abort signal to all requests
  config.signal = globalAbortController.signal
  
  // Add API version header for debugging
  if (apiConfig.debugApi) {
    config.headers['X-Frontend-Version'] = '25.0'
    config.headers['X-API-Compatibility'] = apiConfig.compatibilityMode
  }
  
  return config
})

// Response interceptor to detect problematic patterns
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // If we detect redirect loops, trigger emergency stop
    if (error.response?.status === 307) {
      console.warn('🚨 Redirect detected, triggering emergency stop')
      window.emergencyStopAllRequests()
    }
    return Promise.reject(error)
  }
)

export const clustersApi = {
  getAll: (params = {}) => api.get('/api/v1/clusters', { params }),
  getById: (id) => api.get(`/api/v1/clusters/${id}`),
  create: (data) => api.post('/api/v1/clusters', data),
  update: (id, data) => api.put(`/api/v1/clusters/${id}`, data),
  delete: (id) => api.delete(`/api/v1/clusters/${id}`)
}


export const postsApi = {
  getAll: (params = {}) => api.get('/api/v1/posts', { params: { limit: 5000, ...params } }),
  getById: (id) => api.get(`/api/v1/posts/${id}`),
  getThreats: (params = {}) => api.get('/api/v1/posts/threats', { params }),
  markAsResponded: (id) => api.patch(`/api/v1/posts/${id}/respond`)
}

export const responsesApi = {
  generate: (data) => api.post('/api/v1/responses/generate', data),
  log: (data) => api.post('/api/v1/responses/log', data)
}

export const dataCollectionApi = {
  status: () => api.get('/api/v1/collection/status'),
  collectCluster: (clusterId, platforms = ['x', 'facebook', 'youtube']) => 
    api.post(`/api/v1/collection/collect/${clusterId}`, { cluster_id: clusterId, platforms }),
  collectBatch: (clusterIds, platforms = ['x', 'facebook', 'youtube']) => 
    api.post('/api/v1/collection/collect/batch', { cluster_ids: clusterIds, platforms }),
  backgroundCollection: (clusterId, platforms = ['x', 'facebook', 'youtube']) =>
    api.post(`/api/v1/collection/collect/start-background/${clusterId}`, { cluster_id: clusterId, platforms })
}

export const tasksApi = {
  // Data Collection Tasks
  triggerScheduledCollection: () => api.post('/api/v1/tasks/data-collection/scheduled'),
  triggerClusterCollection: (clusterId, platforms) => 
    api.post(`/api/v1/tasks/data-collection/cluster/${clusterId}`, { platforms }),
  triggerEmergencyCollection: (keywords, priority = 'high') =>
    api.post('/api/v1/tasks/data-collection/emergency', { keywords, priority }),
  
  // Intelligence Tasks
  triggerIntelligenceProcessing: () => api.post('/api/v1/tasks/intelligence/process-pending'),
  triggerPostAnalysis: (postId) => api.post(`/api/v1/tasks/intelligence/analyze/${postId}`),
  triggerBatchAnalysis: (postIds) => api.post('/api/v1/tasks/intelligence/batch-analysis', { post_ids: postIds }),
  triggerDeepAnalysis: (clusterId, timeRangeHours = 24) => 
    api.post(`/api/v1/tasks/intelligence/deep-analysis/${clusterId}`, null, { params: { time_range_hours: timeRangeHours } }),
  
  // Monitoring Tasks
  triggerThreatMonitoring: () => api.post('/api/v1/tasks/monitoring/threat-monitor'),
  triggerDailyAnalytics: () => api.post('/api/v1/tasks/monitoring/daily-analytics'),
  triggerHealthCheck: () => api.post('/api/v1/tasks/monitoring/health-check'),
  
  // Task Management
  getTaskStatus: (taskId) => api.get(`/api/v1/tasks/status/${taskId}`),
  getActiveTasks: () => api.get('/api/v1/tasks/active'),
  getTaskStats: () => api.get('/api/v1/tasks/stats'),
  cancelTask: (taskId) => api.post(`/api/v1/tasks/cancel/${taskId}`)
}

// SMART RADAR v25.0 - Unified Content API
export const contentApi = {
  // Core content operations
  getAll: (params = {}) => api.get('/api/v1/content', { params }),
  getById: (id) => api.get(`/api/v1/content/${id}`),
  create: (data) => api.post('/api/v1/content', data),
  update: (id, data) => api.put(`/api/v1/content/${id}`, data),
  delete: (id) => api.delete(`/api/v1/content/${id}`),
  
  // Specialized queries
  getThreats: (params = {}) => api.get('/api/v1/content/threats', { params }),
  getAggregations: (params = {}) => api.get('/api/v1/content/aggregations', { params }),
  
  // Legacy compatibility endpoints (maps to unified backend)
  posts: (params = {}) => api.get('/api/v1/content/posts', { params }),
  threatsLegacy: () => api.get('/api/v1/content/posts/threats'),
  
  // Batch processing
  batchProcess: (limit = 10) => api.post('/api/v1/content/batch/process', null, { params: { limit } }),
  
  // Sentiment analysis (v25.0 enhanced)
  sentiment: {
    organization: (params = {}) => api.get('/api/v1/content/sentiment/organization', { params }),
    competitors: (params = {}) => api.get('/api/v1/content/sentiment/competitors', { params }),
    cluster: (clusterName) => api.get(`/api/v1/content/sentiment/cluster/${clusterName}`)
  },
  
  // Migration and data management
  migration: {
    migrateAll: () => api.post('/api/v1/content/migrate/all'),
    migrateSocialPosts: () => api.post('/api/v1/content/migrate/social-posts'),
    migrateNewsArticles: () => api.post('/api/v1/content/migrate/news-articles'),
    validate: () => api.get('/api/v1/content/migrate/validate')
  }
}

// API Version and Feature Detection
export const systemApi = {
  health: () => api.get('/health'),
  version: () => api.get('/'),
  features: () => api.get('/health').then(response => response.data.features || {})
}

// API Initialization and feature detection
export const initializeApi = async () => {
  if (isApiInitialized) return { version: apiVersion, features: apiFeatures }
  
  try {
    console.log('🔄 Initializing SMART RADAR API connection...')
    
    // Try to get API version and features
    const healthResponse = await systemApi.health()
    const versionResponse = await systemApi.version()
    
    if (healthResponse.data) {
      apiVersion = healthResponse.data.version || '19.0'
      apiFeatures = healthResponse.data.features || {}
      
      // Log initialization results
      if (apiVersion === '25.0') {
        console.log('✅ Connected to SMART RADAR v25.0 - Unified Intelligence Platform')
        console.log('🎯 Core Module:', versionResponse.data?.core_module || 'legacy')
        console.log('🧠 Intelligence Version:', versionResponse.data?.intelligence_version || 'v19.0')
        
        if (apiFeatures.unified_content_api) {
          console.log('🔗 Unified Content API Available:', apiFeatures.unified_content_api)
        }
        
        if (apiFeatures.migration_endpoints) {
          console.log('📦 Migration Tools Available:', apiFeatures.migration_endpoints)
        }
      } else {
        console.log(`✅ Connected to SMART RADAR v${apiVersion}`)
      }
      
      // Set global API features for components to use
      window.SMART_RADAR_API = {
        version: apiVersion,
        features: apiFeatures,
        config: apiConfig
      }
      
      isApiInitialized = true
      return { version: apiVersion, features: apiFeatures }
    }
  } catch (error) {
    console.warn('⚠️ API initialization failed, using default configuration:', error.message)
    
    // Fallback to legacy mode
    apiVersion = '19.0'
    apiFeatures = {}
    isApiInitialized = true
    
    window.SMART_RADAR_API = {
      version: apiVersion,
      features: apiFeatures,
      config: { ...apiConfig, compatibilityMode: 'legacy' }
    }
  }
  
  return { version: apiVersion, features: apiFeatures }
}

// Smart API selector - chooses best API based on backend version and config
export const getSmartApi = () => {
  const shouldUseUnified = apiConfig.useUnifiedApi && apiVersion === '25.0' && apiFeatures.unified_content_api
  
  return {
    // Posts API - smart selection between legacy and unified
    posts: shouldUseUnified ? contentApi : postsApi,
    
    // Sentiment API - enhanced for v25.0 or fallback to legacy
    sentiment: shouldUseUnified ? contentApi.sentiment : {
      organization: (params = {}) => api.get('/api/v1/sentiment/organization', { params }),
      competitors: (params = {}) => api.get('/api/v1/sentiment/competitors', { params }),
      cluster: (clusterName) => api.get(`/api/v1/sentiment/cluster/${clusterName}`)
    },
    
    // Content API - only available in v25.0
    content: apiVersion === '25.0' ? contentApi : null,
    
    // Migration tools - only available if enabled
    migration: (apiConfig.enableMigrationTools && apiFeatures.migration_endpoints) ? contentApi.migration : null,
    
    // Check if specific features are available
    hasFeature: (feature) => !!apiFeatures[feature],
    hasUnifiedApi: () => shouldUseUnified,
    hasV24Intelligence: () => apiConfig.enableV24Intelligence && apiVersion === '25.0'
  }
}

// Export API state getters
export const getApiVersion = () => apiVersion
export const getApiFeatures = () => apiFeatures
export const isApiV25 = () => apiVersion === '25.0'
export const hasUnifiedApi = () => apiConfig.useUnifiedApi && apiVersion === '25.0' && apiFeatures.unified_content_api

export default api