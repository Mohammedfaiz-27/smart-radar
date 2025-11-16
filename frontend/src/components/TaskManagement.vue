<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200">
    <div class="px-6 py-4 border-b border-gray-200">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-lg font-semibold text-gray-900">Task Management</h3>
          <p class="text-sm text-gray-500">Monitor and control background tasks</p>
        </div>
        
        <div class="flex items-center space-x-2">
          <div class="flex items-center space-x-4">
            <div class="text-sm">
              <span class="font-medium text-blue-600">{{ tasksStore.runningTasksCount }}</span>
              <span class="text-gray-500">Running</span>
            </div>
            <div class="text-sm">
              <span class="font-medium text-yellow-600">{{ tasksStore.queuedTasksCount }}</span>
              <span class="text-gray-500">Queued</span>
            </div>
          </div>
          
          <button 
            @click="refreshTasks"
            class="btn-secondary"
            :disabled="tasksStore.loading"
          >
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="px-6 py-4 bg-gray-50 border-b border-gray-200">
      <h4 class="text-sm font-medium text-gray-900 mb-3">Quick Actions</h4>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <button 
          @click="triggerDataCollection"
          class="btn-primary text-xs py-2"
          :disabled="tasksStore.loading"
        >
          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Collect Data
        </button>
        
        <button 
          @click="triggerIntelligence"
          class="btn-secondary text-xs py-2"
          :disabled="tasksStore.loading"
        >
          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          Analyze
        </button>
        
        <button 
          @click="triggerThreatMonitoring"
          class="btn-danger text-xs py-2"
          :disabled="tasksStore.loading"
        >
          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.502 0L4.768 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          Monitor
        </button>
        
        <button 
          @click="triggerHealthCheck"
          class="btn-secondary text-xs py-2"
          :disabled="tasksStore.loading"
        >
          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                  d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
          Health Check
        </button>
      </div>
    </div>

    <!-- Active Tasks -->
    <div class="px-6 py-4" v-if="tasksStore.activeTasks.length > 0">
      <h4 class="text-sm font-medium text-gray-900 mb-3">Active Tasks</h4>
      <div class="space-y-2">
        <div 
          v-for="task in tasksStore.activeTasks" 
          :key="task.id"
          class="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
        >
          <div class="flex items-center space-x-3">
            <div class="flex-shrink-0">
              <div class="w-2 h-2 rounded-full" :class="getTaskStatusColor(task.status)"></div>
            </div>
            <div>
              <p class="text-sm font-medium text-gray-900">{{ task.name || task.id }}</p>
              <p class="text-xs text-gray-500">{{ task.worker || 'Unknown worker' }}</p>
            </div>
          </div>
          
          <div class="flex items-center space-x-2">
            <span class="text-xs px-2 py-1 rounded-full" 
                  :class="getTaskStatusBadge(task.status)">
              {{ task.status }}
            </span>
            <button 
              @click="cancelTask(task.id)"
              class="text-red-600 hover:text-red-800 text-xs"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Task History -->
    <div class="px-6 py-4">
      <div class="flex items-center justify-between mb-3">
        <h4 class="text-sm font-medium text-gray-900">Recent Tasks</h4>
        <button 
          @click="clearHistory"
          class="text-xs text-gray-500 hover:text-gray-700"
        >
          Clear History
        </button>
      </div>
      
      <div class="space-y-2 max-h-64 overflow-y-auto">
        <div 
          v-for="task in tasksStore.recentTasks" 
          :key="task.id"
          class="flex items-center justify-between p-2 hover:bg-gray-50 rounded"
        >
          <div class="flex items-center space-x-3">
            <div class="flex-shrink-0">
              <div class="w-2 h-2 rounded-full" :class="getTaskStatusColor(task.status)"></div>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm text-gray-900 truncate">{{ task.message }}</p>
              <p class="text-xs text-gray-500">{{ formatTime(task.timestamp) }}</p>
            </div>
          </div>
          
          <div class="flex items-center space-x-2">
            <span class="text-xs px-2 py-1 rounded-full" 
                  :class="getTaskStatusBadge(task.status)">
              {{ task.status }}
            </span>
            <button 
              @click="getTaskDetails(task.id)"
              class="text-blue-600 hover:text-blue-800 text-xs"
            >
              Details
            </button>
          </div>
        </div>
        
        <div v-if="tasksStore.recentTasks.length === 0" class="text-center py-4">
          <p class="text-sm text-gray-500">No recent tasks</p>
        </div>
      </div>
    </div>

    <!-- Emergency Collection Modal -->
    <div v-if="showEmergencyModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg p-6 w-full max-w-md">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Emergency Data Collection</h3>
        
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Keywords</label>
            <textarea 
              v-model="emergencyKeywords"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows="3"
              placeholder="Enter keywords separated by commas"
            ></textarea>
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Priority</label>
            <select 
              v-model="emergencyPriority"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
        </div>
        
        <div class="flex justify-end space-x-3 mt-6">
          <button 
            @click="showEmergencyModal = false"
            class="btn-secondary"
          >
            Cancel
          </button>
          <button 
            @click="submitEmergencyCollection"
            class="btn-danger"
            :disabled="!emergencyKeywords.trim()"
          >
            Start Emergency Collection
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useTasksStore } from '@/stores/tasks'

const tasksStore = useTasksStore()

// Modal state
const showEmergencyModal = ref(false)
const emergencyKeywords = ref('')
const emergencyPriority = ref('high')

// Auto-refresh interval
let refreshInterval = null

const refreshTasks = async () => {
  await tasksStore.refreshActiveTasks()
}

const triggerDataCollection = async () => {
  try {
    await tasksStore.triggerDataCollection()
  } catch (error) {
    console.error('Failed to trigger data collection:', error)
  }
}

const triggerIntelligence = async () => {
  try {
    await tasksStore.triggerIntelligenceProcessing()
  } catch (error) {
    console.error('Failed to trigger intelligence processing:', error)
  }
}

const triggerThreatMonitoring = async () => {
  try {
    await tasksStore.triggerThreatMonitoring()
  } catch (error) {
    console.error('Failed to trigger threat monitoring:', error)
  }
}

const triggerHealthCheck = async () => {
  try {
    await tasksStore.triggerSystemHealthCheck()
  } catch (error) {
    console.error('Failed to trigger health check:', error)
  }
}

const submitEmergencyCollection = async () => {
  const keywords = emergencyKeywords.value
    .split(',')
    .map(k => k.trim())
    .filter(k => k.length > 0)
  
  if (keywords.length === 0) return
  
  try {
    await tasksStore.triggerEmergencyCollection(keywords, emergencyPriority.value)
    showEmergencyModal.value = false
    emergencyKeywords.value = ''
    emergencyPriority.value = 'high'
  } catch (error) {
    console.error('Failed to start emergency collection:', error)
  }
}

const cancelTask = async (taskId) => {
  try {
    await tasksStore.cancelTask(taskId)
    await refreshTasks()
  } catch (error) {
    console.error('Failed to cancel task:', error)
  }
}

const getTaskDetails = async (taskId) => {
  try {
    const details = await tasksStore.getTaskStatus(taskId)
    // Could open a modal with detailed task information
    console.log('Task details:', details)
  } catch (error) {
    console.error('Failed to get task details:', error)
  }
}

const clearHistory = () => {
  tasksStore.clearTaskHistory()
}

const getTaskStatusColor = (status) => {
  switch (status) {
    case 'running':
    case 'PENDING':
      return 'bg-blue-500'
    case 'completed':
    case 'SUCCESS':
      return 'bg-green-500'
    case 'failed':
    case 'FAILURE':
      return 'bg-red-500'
    case 'cancelled':
    case 'REVOKED':
      return 'bg-gray-500'
    case 'queued':
      return 'bg-yellow-500'
    default:
      return 'bg-gray-300'
  }
}

const getTaskStatusBadge = (status) => {
  switch (status) {
    case 'running':
    case 'PENDING':
      return 'bg-blue-100 text-blue-800'
    case 'completed':
    case 'SUCCESS':
      return 'bg-green-100 text-green-800'
    case 'failed':
    case 'FAILURE':
      return 'bg-red-100 text-red-800'
    case 'cancelled':
    case 'REVOKED':
      return 'bg-gray-100 text-gray-800'
    case 'queued':
      return 'bg-yellow-100 text-yellow-800'
    default:
      return 'bg-gray-100 text-gray-600'
  }
}

const formatTime = (timestamp) => {
  return new Date(timestamp).toLocaleTimeString()
}

onMounted(async () => {
  // Initial load
  await refreshTasks()
  await tasksStore.getCollectionStatus()
  
  // Set up auto-refresh every 30 seconds
  refreshInterval = setInterval(refreshTasks, 30000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>