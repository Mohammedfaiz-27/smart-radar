<template>
  <div class="relative">
    <!-- Notification Bell -->
    <button 
      @click="toggleNotifications"
      class="relative p-2 text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
    >
      <BellIcon class="h-6 w-6" />
      <!-- Notification Badge -->
      <span 
        v-if="unreadCount > 0"
        class="absolute -top-1 -right-1 h-5 w-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center"
      >
        {{ unreadCount > 9 ? '9+' : unreadCount }}
      </span>
    </button>

    <!-- Notifications Dropdown -->
    <div 
      v-if="showNotifications"
      class="absolute right-0 mt-2 w-80 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-50"
    >
      <div class="py-1">
        <!-- Header -->
        <div class="px-4 py-2 border-b border-gray-100">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-medium text-gray-900">Notifications</h3>
            <button 
              v-if="notifications.length > 0"
              @click="clearAll"
              class="text-xs text-gray-500 hover:text-gray-700"
            >
              Clear All
            </button>
          </div>
        </div>

        <!-- Notifications List -->
        <div class="max-h-96 overflow-y-auto">
          <div v-if="notifications.length === 0" class="px-4 py-6 text-center">
            <p class="text-sm text-gray-500">No notifications</p>
          </div>

          <div 
            v-for="notification in notifications" 
            :key="notification.id"
            :class="[
              'px-4 py-3 hover:bg-gray-50 cursor-pointer border-b border-gray-50',
              !notification.read ? 'bg-blue-50' : ''
            ]"
            @click="markAsRead(notification.id)"
          >
            <div class="flex items-start">
              <div :class="notificationIconClasses(notification.type)">
                <component :is="getNotificationIcon(notification.type)" class="h-4 w-4" />
              </div>
              <div class="ml-3 flex-1">
                <p class="text-sm font-medium text-gray-900">
                  {{ notification.title }}
                </p>
                <p class="text-xs text-gray-500 mt-1">
                  {{ notification.message }}
                </p>
                <p class="text-xs text-gray-400 mt-1">
                  {{ formatTimestamp(notification.timestamp) }}
                </p>
              </div>
              <div v-if="!notification.read" class="w-2 h-2 bg-blue-500 rounded-full ml-2"></div>
            </div>
          </div>
        </div>

        <!-- Alerts Section -->
        <div v-if="alerts.length > 0" class="border-t border-gray-100">
          <div class="px-4 py-2 bg-red-50">
            <h4 class="text-sm font-medium text-red-900">Critical Alerts</h4>
          </div>
          <div 
            v-for="alert in alerts.slice(0, 3)" 
            :key="alert.id"
            class="px-4 py-3 border-b border-red-100 bg-red-50"
          >
            <div class="flex items-start">
              <ExclamationTriangleIcon class="h-4 w-4 text-red-500 mt-0.5" />
              <div class="ml-3 flex-1">
                <p class="text-sm text-red-900">
                  Threat detected in {{ alert.platform }} post
                </p>
                <p class="text-xs text-red-700 mt-1">
                  {{ alert.content?.text?.substring(0, 100) }}...
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { 
  BellIcon, 
  ExclamationTriangleIcon,
  InformationCircleIcon,
  CheckCircleIcon,
  XCircleIcon
} from '@heroicons/vue/24/outline'
import { useNotificationsStore } from '@/stores/notifications'

const notificationsStore = useNotificationsStore()
const showNotifications = ref(false)

const notifications = computed(() => notificationsStore.notifications)
const alerts = computed(() => notificationsStore.alerts)

const unreadCount = computed(() => {
  return notifications.value.filter(n => !n.read).length + 
         alerts.value.filter(a => !a.read).length
})

const toggleNotifications = () => {
  showNotifications.value = !showNotifications.value
}

const markAsRead = (notificationId) => {
  notificationsStore.markNotificationAsRead(notificationId)
}

const clearAll = () => {
  notificationsStore.clearAllNotifications()
  notificationsStore.clearAllAlerts()
}

const getNotificationIcon = (type) => {
  const iconMap = {
    info: InformationCircleIcon,
    success: CheckCircleIcon,
    error: XCircleIcon,
    alert: ExclamationTriangleIcon
  }
  return iconMap[type] || InformationCircleIcon
}

const notificationIconClasses = (type) => {
  const baseClasses = 'flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center'
  const colorMap = {
    info: 'bg-blue-100 text-blue-600',
    success: 'bg-green-100 text-green-600',
    error: 'bg-red-100 text-red-600',
    alert: 'bg-orange-100 text-orange-600'
  }
  return `${baseClasses} ${colorMap[type] || colorMap.info}`
}

const formatTimestamp = (timestamp) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  return date.toLocaleDateString()
}

// Close dropdown when clicking outside
const handleClickOutside = (event) => {
  if (!event.target.closest('.relative')) {
    showNotifications.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>