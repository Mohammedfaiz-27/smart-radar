import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useNotificationsStore = defineStore('notifications', () => {
  const alerts = ref([])
  const notifications = ref([])

  const addAlert = (alertData) => {
    const alert = {
      id: Date.now() + Math.random(),
      ...alertData,
      timestamp: new Date(),
      read: false
    }
    alerts.value.unshift(alert)
    
    // Also add to general notifications
    addNotification({
      type: 'alert',
      title: 'Threat Detected',
      message: `High-priority post detected: ${alertData.content?.text?.substring(0, 100)}...`,
      data: alertData
    })
  }

  const addNotification = ({ type = 'info', title, message, data = null }) => {
    const notification = {
      id: Date.now() + Math.random(),
      type,
      title,
      message,
      data,
      timestamp: new Date(),
      read: false
    }
    notifications.value.unshift(notification)
    
    // Auto-remove after 5 seconds for non-alert notifications
    if (type !== 'alert') {
      setTimeout(() => {
        removeNotification(notification.id)
      }, 5000)
    }
  }

  const markAlertAsRead = (alertId) => {
    const alert = alerts.value.find(a => a.id === alertId)
    if (alert) {
      alert.read = true
    }
  }

  const markNotificationAsRead = (notificationId) => {
    const notification = notifications.value.find(n => n.id === notificationId)
    if (notification) {
      notification.read = true
    }
  }

  const removeNotification = (notificationId) => {
    const index = notifications.value.findIndex(n => n.id === notificationId)
    if (index !== -1) {
      notifications.value.splice(index, 1)
    }
  }

  const clearAllAlerts = () => {
    alerts.value = []
  }

  const clearAllNotifications = () => {
    notifications.value = []
  }

  return {
    alerts,
    notifications,
    addAlert,
    addNotification,
    markAlertAsRead,
    markNotificationAsRead,
    removeNotification,
    clearAllAlerts,
    clearAllNotifications
  }
})