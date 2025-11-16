import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { tasksApi, dataCollectionApi } from '@/services/api'
import { useNotificationsStore } from './notifications'

export const useTasksStore = defineStore('tasks', () => {
  const activeTasks = ref([])
  const taskHistory = ref([])
  const loading = ref(false)
  const error = ref(null)
  const collectionStatus = ref(null)

  const notificationsStore = useNotificationsStore()

  // Computed properties
  const runningTasksCount = computed(() => 
    activeTasks.value.filter(task => task.status === 'running').length
  )

  const queuedTasksCount = computed(() => 
    activeTasks.value.filter(task => task.status === 'queued').length
  )

  const recentTasks = computed(() => 
    taskHistory.value.slice(0, 10)
  )

  // Data Collection Actions
  const triggerDataCollection = async (clusterId = null, platforms = ['x', 'facebook', 'youtube']) => {
    loading.value = true
    error.value = null
    
    try {
      let response
      if (clusterId) {
        response = await tasksApi.triggerClusterCollection(clusterId, platforms)
      } else {
        response = await tasksApi.triggerScheduledCollection()
      }
      
      // Add to task history
      taskHistory.value.unshift({
        id: response.data.task_id,
        type: 'data_collection',
        status: response.data.status,
        message: response.data.message,
        timestamp: new Date().toISOString(),
        clusterId
      })

      notificationsStore.addNotification({
        type: 'info',
        title: 'Data Collection Started',
        message: response.data.message
      })

      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to start data collection'
      notificationsStore.addNotification({
        type: 'error',
        title: 'Data Collection Failed',
        message: error.value
      })
      throw err
    } finally {
      loading.value = false
    }
  }

  const triggerEmergencyCollection = async (keywords, priority = 'high') => {
    loading.value = true
    error.value = null
    
    try {
      const response = await tasksApi.triggerEmergencyCollection(keywords, priority)
      
      taskHistory.value.unshift({
        id: response.data.task_id,
        type: 'emergency_collection',
        status: response.data.status,
        message: response.data.message,
        timestamp: new Date().toISOString(),
        keywords,
        priority
      })

      notificationsStore.addNotification({
        type: 'warning',
        title: 'Emergency Collection Started',
        message: `Collecting data for: ${keywords.join(', ')}`
      })

      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to start emergency collection'
      notificationsStore.addNotification({
        type: 'error',
        title: 'Emergency Collection Failed',
        message: error.value
      })
      throw err
    } finally {
      loading.value = false
    }
  }

  // Intelligence Tasks
  const triggerIntelligenceProcessing = async () => {
    loading.value = true
    error.value = null
    
    try {
      const response = await tasksApi.triggerIntelligenceProcessing()
      
      taskHistory.value.unshift({
        id: response.data.task_id,
        type: 'intelligence_processing',
        status: response.data.status,
        message: response.data.message,
        timestamp: new Date().toISOString()
      })

      notificationsStore.addNotification({
        type: 'info',
        title: 'Intelligence Processing Started',
        message: 'Analyzing pending posts for sentiment and threats'
      })

      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to start intelligence processing'
      throw err
    } finally {
      loading.value = false
    }
  }

  const triggerDeepAnalysis = async (clusterId, timeRangeHours = 24) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await tasksApi.triggerDeepAnalysis(clusterId, timeRangeHours)
      
      taskHistory.value.unshift({
        id: response.data.task_id,
        type: 'deep_analysis',
        status: response.data.status,
        message: response.data.message,
        timestamp: new Date().toISOString(),
        clusterId,
        timeRangeHours
      })

      notificationsStore.addNotification({
        type: 'info',
        title: 'Deep Analysis Started',
        message: `Analyzing cluster content for last ${timeRangeHours} hours`
      })

      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to start deep analysis'
      throw err
    } finally {
      loading.value = false
    }
  }

  // Monitoring Tasks
  const triggerThreatMonitoring = async () => {
    try {
      const response = await tasksApi.triggerThreatMonitoring()
      
      taskHistory.value.unshift({
        id: response.data.task_id,
        type: 'threat_monitoring',
        status: response.data.status,
        message: response.data.message,
        timestamp: new Date().toISOString()
      })

      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to trigger threat monitoring'
      throw err
    }
  }

  const triggerSystemHealthCheck = async () => {
    try {
      const response = await tasksApi.triggerHealthCheck()
      
      taskHistory.value.unshift({
        id: response.data.task_id,
        type: 'health_check',
        status: response.data.status,
        message: response.data.message,
        timestamp: new Date().toISOString()
      })

      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to trigger health check'
      throw err
    }
  }

  // Task Management
  const getActiveTasks = async () => {
    try {
      const response = await tasksApi.getActiveTasks()
      activeTasks.value = response.data.active_tasks || []
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch active tasks'
      throw err
    }
  }

  const getTaskStatus = async (taskId) => {
    try {
      const response = await tasksApi.getTaskStatus(taskId)
      
      // Update task in history if it exists
      const taskIndex = taskHistory.value.findIndex(task => task.id === taskId)
      if (taskIndex !== -1) {
        taskHistory.value[taskIndex] = {
          ...taskHistory.value[taskIndex],
          status: response.data.status,
          result: response.data.result
        }
      }

      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to get task status'
      throw err
    }
  }

  const cancelTask = async (taskId) => {
    try {
      const response = await tasksApi.cancelTask(taskId)
      
      // Update task status in history
      const taskIndex = taskHistory.value.findIndex(task => task.id === taskId)
      if (taskIndex !== -1) {
        taskHistory.value[taskIndex].status = 'cancelled'
      }

      notificationsStore.addNotification({
        type: 'info',
        title: 'Task Cancelled',
        message: `Task ${taskId} has been cancelled`
      })

      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to cancel task'
      throw err
    }
  }

  // Data Collection Status
  const getCollectionStatus = async () => {
    try {
      const response = await dataCollectionApi.status()
      collectionStatus.value = response.data
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to get collection status'
      throw err
    }
  }

  // Utility functions
  const clearTaskHistory = () => {
    taskHistory.value = []
  }

  const getTasksByType = (type) => {
    return taskHistory.value.filter(task => task.type === type)
  }

  // Auto-refresh active tasks (call this periodically)
  const refreshActiveTasks = async () => {
    try {
      await getActiveTasks()
    } catch (err) {
      // Silent fail for auto-refresh
      console.warn('Failed to refresh active tasks:', err)
    }
  }

  return {
    // State
    activeTasks,
    taskHistory,
    loading,
    error,
    collectionStatus,
    
    // Computed
    runningTasksCount,
    queuedTasksCount,
    recentTasks,
    
    // Data Collection
    triggerDataCollection,
    triggerEmergencyCollection,
    
    // Intelligence
    triggerIntelligenceProcessing,
    triggerDeepAnalysis,
    
    // Monitoring
    triggerThreatMonitoring,
    triggerSystemHealthCheck,
    
    // Task Management
    getActiveTasks,
    getTaskStatus,
    cancelTask,
    refreshActiveTasks,
    
    // Data Collection Status
    getCollectionStatus,
    
    // Utilities
    clearTaskHistory,
    getTasksByType
  }
})