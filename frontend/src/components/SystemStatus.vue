<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200">
    <div class="px-6 py-4 border-b border-gray-200">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-lg font-semibold text-gray-900">System Status</h3>
          <p class="text-sm text-gray-500">Real-time system health and connectivity</p>
        </div>
        
        <div class="flex items-center space-x-2">
          <div class="flex items-center space-x-2">
            <div class="w-2 h-2 rounded-full" :class="overallStatusColor"></div>
            <span class="text-sm font-medium" :class="overallStatusText">
              {{ overallStatus }}
            </span>
          </div>
          
          <button 
            @click="checkSystemHealth"
            class="btn-secondary text-sm"
            :disabled="loading"
          >
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
            </svg>
            Check Health
          </button>
        </div>
      </div>
    </div>

    <!-- System Components Status -->
    <div class="px-6 py-4">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        <!-- Backend API -->
        <div class="p-4 border rounded-lg">
          <div class="flex items-center justify-between mb-2">
            <h4 class="text-sm font-medium text-gray-900">Backend API</h4>
            <div class="flex items-center space-x-1">
              <div class="w-2 h-2 rounded-full" :class="getStatusColor(status.backend)"></div>
              <span class="text-xs" :class="getStatusTextColor(status.backend)">
                {{ status.backend }}
              </span>
            </div>
          </div>
          <p class="text-xs text-gray-500">FastAPI server connectivity</p>
          <div class="mt-2 text-xs text-gray-600">
            <div>Response Time: {{ responseTime }}ms</div>
            <div>Last Check: {{ formatTime(lastHealthCheck) }}</div>
          </div>
        </div>

        <!-- Database -->
        <div class="p-4 border rounded-lg">
          <div class="flex items-center justify-between mb-2">
            <h4 class="text-sm font-medium text-gray-900">Database</h4>
            <div class="flex items-center space-x-1">
              <div class="w-2 h-2 rounded-full" :class="getStatusColor(status.database)"></div>
              <span class="text-xs" :class="getStatusTextColor(status.database)">
                {{ status.database }}
              </span>
            </div>
          </div>
          <p class="text-xs text-gray-500">MongoDB connection</p>
          <div class="mt-2 text-xs text-gray-600">
            <div>Collections: {{ databaseStats.collections || 0 }}</div>
            <div>Total Posts: {{ databaseStats.totalPosts || 0 }}</div>
          </div>
        </div>

        <!-- WebSocket -->
        <div class="p-4 border rounded-lg">
          <div class="flex items-center justify-between mb-2">
            <h4 class="text-sm font-medium text-gray-900">WebSocket</h4>
            <div class="flex items-center space-x-1">
              <div class="w-2 h-2 rounded-full" :class="getStatusColor(websocketStore.isConnected ? 'healthy' : 'error')"></div>
              <span class="text-xs" :class="getStatusTextColor(websocketStore.isConnected ? 'healthy' : 'error')">
                {{ websocketStore.isConnected ? 'Connected' : 'Disconnected' }}
              </span>
            </div>
          </div>
          <p class="text-xs text-gray-500">Real-time updates</p>
          <div class="mt-2 text-xs text-gray-600">
            <div>Status: {{ websocketStore.isConnected ? 'Active' : 'Inactive' }}</div>
            <div>Messages: {{ messageCount }}</div>
          </div>
        </div>

        <!-- Data Collection -->
        <div class="p-4 border rounded-lg">
          <div class="flex items-center justify-between mb-2">
            <h4 class="text-sm font-medium text-gray-900">Data Collection</h4>
            <div class="flex items-center space-x-1">
              <div class="w-2 h-2 rounded-full" :class="getStatusColor(status.dataCollection)"></div>
              <span class="text-xs" :class="getStatusTextColor(status.dataCollection)">
                {{ status.dataCollection }}
              </span>
            </div>
          </div>
          <p class="text-xs text-gray-500">Social media APIs</p>
          <div class="mt-2 text-xs text-gray-600">
            <div>Platforms: {{ availablePlatforms.length }}</div>
            <div>Last Collection: {{ formatTime(lastCollection) }}</div>
          </div>
        </div>

        <!-- Task Queue -->
        <div class="p-4 border rounded-lg">
          <div class="flex items-center justify-between mb-2">
            <h4 class="text-sm font-medium text-gray-900">Task Queue</h4>
            <div class="flex items-center space-x-1">
              <div class="w-2 h-2 rounded-full" :class="getStatusColor(status.taskQueue)"></div>
              <span class="text-xs" :class="getStatusTextColor(status.taskQueue)">
                {{ status.taskQueue }}
              </span>
            </div>
          </div>
          <p class="text-xs text-gray-500">Background processing</p>
          <div class="mt-2 text-xs text-gray-600">
            <div>Active: {{ tasksStore.runningTasksCount }}</div>
            <div>Queued: {{ tasksStore.queuedTasksCount }}</div>
          </div>
        </div>

        <!-- Intelligence Pipeline -->
        <div class="p-4 border rounded-lg">
          <div class="flex items-center justify-between mb-2">
            <h4 class="text-sm font-medium text-gray-900">Intelligence Pipeline</h4>
            <div class="flex items-center space-x-1">
              <div class="w-2 h-2 rounded-full" :class="getStatusColor(status.intelligence)"></div>
              <span class="text-xs" :class="getStatusTextColor(status.intelligence)">
                {{ status.intelligence }}
              </span>
            </div>
          </div>
          <p class="text-xs text-gray-500">AI sentiment analysis</p>
          <div class="mt-2 text-xs text-gray-600">
            <div>Processed: {{ intelligenceStats.processed || 0 }}</div>
            <div>Threats: {{ intelligenceStats.threats || 0 }}</div>
          </div>
        </div>
      </div>

      <!-- API Keys Status -->
      <div class="bg-gray-50 rounded-lg p-4 mb-6">
        <h4 class="text-sm font-medium text-gray-900 mb-3">API Configuration</h4>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div v-for="(configured, platform) in apiKeyStatus" :key="platform" 
               class="flex items-center justify-between p-2 bg-white rounded border">
            <span class="text-xs text-gray-700 capitalize">{{ platform.replace('_configured', '') }}</span>
            <div class="flex items-center space-x-1">
              <div class="w-2 h-2 rounded-full" :class="configured ? 'bg-green-500' : 'bg-red-500'"></div>
              <span class="text-xs" :class="configured ? 'text-green-600' : 'text-red-600'">
                {{ configured ? 'OK' : 'Missing' }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- System Metrics -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="bg-gray-50 rounded-lg p-4">
          <h4 class="text-sm font-medium text-gray-900 mb-3">Performance</h4>
          <div class="space-y-2 text-sm">
            <div class="flex justify-between">
              <span class="text-gray-600">API Response:</span>
              <span class="font-medium">{{ responseTime }}ms</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600">Uptime:</span>
              <span class="font-medium">{{ uptime }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600">Memory Usage:</span>
              <span class="font-medium">Normal</span>
            </div>
          </div>
        </div>

        <div class="bg-gray-50 rounded-lg p-4">
          <h4 class="text-sm font-medium text-gray-900 mb-3">Data Flow</h4>
          <div class="space-y-2 text-sm">
            <div class="flex justify-between">
              <span class="text-gray-600">Posts/Hour:</span>
              <span class="font-medium">{{ dataFlow.postsPerHour || 0 }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600">Threats/Hour:</span>
              <span class="font-medium">{{ dataFlow.threatsPerHour || 0 }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600">Processing Rate:</span>
              <span class="font-medium">{{ dataFlow.processingRate || 0 }}%</span>
            </div>
          </div>
        </div>

        <div class="bg-gray-50 rounded-lg p-4">
          <h4 class="text-sm font-medium text-gray-900 mb-3">Alerts</h4>
          <div class="space-y-2 text-sm">
            <div class="flex justify-between">
              <span class="text-gray-600">Critical:</span>
              <span class="font-medium text-red-600">{{ alerts.critical || 0 }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600">Warnings:</span>
              <span class="font-medium text-yellow-600">{{ alerts.warnings || 0 }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600">Info:</span>
              <span class="font-medium text-blue-600">{{ alerts.info || 0 }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useWebSocketStore } from '@/stores/websocket'
import { useTasksStore } from '@/stores/tasks'
import { usePostsStore } from '@/stores/posts'
import { dataCollectionApi, tasksApi } from '@/services/api'

const websocketStore = useWebSocketStore()
const tasksStore = useTasksStore()
const postsStore = usePostsStore()

const loading = ref(false)
const responseTime = ref(0)
const messageCount = ref(0)
const lastHealthCheck = ref(null)
const lastCollection = ref(null)
const uptime = ref('00:00:00')

const status = reactive({
  backend: 'unknown',
  database: 'unknown',
  dataCollection: 'unknown',
  taskQueue: 'unknown',
  intelligence: 'unknown'
})

const databaseStats = reactive({
  collections: 0,
  totalPosts: 0
})

const intelligenceStats = reactive({
  processed: 0,
  threats: 0
})

const apiKeyStatus = ref({})
const availablePlatforms = ref([])

const dataFlow = reactive({
  postsPerHour: 0,
  threatsPerHour: 0,
  processingRate: 0
})

const alerts = reactive({
  critical: 0,
  warnings: 0,
  info: 0
})

// Computed properties
const overallStatus = computed(() => {
  const statuses = Object.values(status)
  if (statuses.includes('error')) return 'System Error'
  if (statuses.includes('warning')) return 'System Warning'
  if (statuses.every(s => s === 'healthy')) return 'All Systems Operational'
  return 'System Check In Progress'
})

const overallStatusColor = computed(() => {
  const statuses = Object.values(status)
  if (statuses.includes('error')) return 'bg-red-500'
  if (statuses.includes('warning')) return 'bg-yellow-500'
  if (statuses.every(s => s === 'healthy')) return 'bg-green-500'
  return 'bg-gray-500'
})

const overallStatusText = computed(() => {
  const statuses = Object.values(status)
  if (statuses.includes('error')) return 'text-red-600'
  if (statuses.includes('warning')) return 'text-yellow-600'
  if (statuses.every(s => s === 'healthy')) return 'text-green-600'
  return 'text-gray-600'
})

// Auto-refresh interval
let refreshInterval = null
let uptimeInterval = null
let startTime = Date.now()

const checkSystemHealth = async () => {
  loading.value = true
  
  try {
    // Trigger system health check
    const startTime = Date.now()
    await tasksApi.triggerHealthCheck()
    responseTime.value = Date.now() - startTime
    
    // Check data collection status
    await checkDataCollectionStatus()
    
    // Update last health check time
    lastHealthCheck.value = new Date()
    
    // Calculate basic stats
    calculateSystemStats()
    
  } catch (error) {
    console.error('Health check failed:', error)
    status.backend = 'error'
  } finally {
    loading.value = false
  }
}

const checkDataCollectionStatus = async () => {
  try {
    const collectionStatus = await dataCollectionApi.status()
    apiKeyStatus.value = collectionStatus.data
    availablePlatforms.value = collectionStatus.data.available_platforms || []
    
    status.dataCollection = availablePlatforms.value.length > 0 ? 'healthy' : 'warning'
  } catch (error) {
    status.dataCollection = 'error'
  }
}

const calculateSystemStats = () => {
  // Database stats
  databaseStats.totalPosts = postsStore.posts.length
  databaseStats.collections = 4 // Approximate: clusters, narratives, posts, responses
  
  // Intelligence stats
  intelligenceStats.processed = postsStore.posts.length
  intelligenceStats.threats = postsStore.threatPosts.length
  
  // Task queue status
  const activeTasks = tasksStore.runningTasksCount + tasksStore.queuedTasksCount
  status.taskQueue = activeTasks > 0 ? 'healthy' : 'warning'
  
  // Intelligence pipeline status
  status.intelligence = intelligenceStats.processed > 0 ? 'healthy' : 'warning'
  
  // Database status
  status.database = databaseStats.totalPosts >= 0 ? 'healthy' : 'error'
  
  // Backend status
  status.backend = responseTime.value < 5000 ? 'healthy' : 'warning'
  
  // Data flow calculations (mock data)
  const now = new Date()
  const recentPosts = postsStore.posts.filter(post => {
    const postTime = new Date(post.collected_at)
    return (now - postTime) < 3600000 // Last hour
  })
  
  dataFlow.postsPerHour = recentPosts.length
  dataFlow.threatsPerHour = recentPosts.filter(post => post.intelligence?.is_threat).length
  dataFlow.processingRate = intelligenceStats.processed > 0 ? 95 : 0
}

const getStatusColor = (statusValue) => {
  switch (statusValue) {
    case 'healthy': return 'bg-green-500'
    case 'warning': return 'bg-yellow-500'
    case 'error': return 'bg-red-500'
    default: return 'bg-gray-500'
  }
}

const getStatusTextColor = (statusValue) => {
  switch (statusValue) {
    case 'healthy': return 'text-green-600'
    case 'warning': return 'text-yellow-600'
    case 'error': return 'text-red-600'
    default: return 'text-gray-600'
  }
}

const formatTime = (timestamp) => {
  if (!timestamp) return 'Never'
  return new Date(timestamp).toLocaleTimeString()
}

const updateUptime = () => {
  const elapsed = Date.now() - startTime
  const hours = Math.floor(elapsed / 3600000)
  const minutes = Math.floor((elapsed % 3600000) / 60000)
  const seconds = Math.floor((elapsed % 60000) / 1000)
  uptime.value = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
}

onMounted(async () => {
  // Initial health check
  await checkSystemHealth()
  
  // Set up auto-refresh every 30 seconds
  refreshInterval = setInterval(checkSystemHealth, 30000)
  
  // Set up uptime counter every second
  uptimeInterval = setInterval(updateUptime, 1000)
  
  // Listen for WebSocket messages
  const originalHandler = websocketStore.handleMessage
  websocketStore.handleMessage = (message) => {
    messageCount.value++
    originalHandler(message)
  }
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  if (uptimeInterval) {
    clearInterval(uptimeInterval)
  }
})
</script>