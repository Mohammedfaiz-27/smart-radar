import { defineStore } from 'pinia'
import { ref } from 'vue'
import { usePostsStore } from './posts'
import { useNotificationsStore } from './notifications'

export const useWebSocketStore = defineStore('websocket', () => {
  const socket = ref(null)
  const isConnected = ref(false)
  
  const postsStore = usePostsStore()
  const notificationsStore = useNotificationsStore()

  const connect = () => {
    const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'
    
    try {
      socket.value = new WebSocket(WS_URL)

      socket.value.onopen = () => {
        isConnected.value = true
        console.log('WebSocket connected')
      }

      socket.value.onclose = () => {
        isConnected.value = false
        console.log('WebSocket disconnected')
        
        // Attempt to reconnect after 3 seconds
        setTimeout(() => {
          if (!isConnected.value) {
            console.log('Attempting to reconnect...')
            connect()
          }
        }, 3000)
      }

      socket.value.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          handleMessage(message)
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      socket.value.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
    }
  }

  const disconnect = () => {
    if (socket.value) {
      socket.value.close()
      socket.value = null
      isConnected.value = false
    }
  }

  const sendMessage = (message) => {
    if (socket.value && socket.value.readyState === WebSocket.OPEN) {
      socket.value.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  const messageHandlers = ref(new Map())
  
  const onMessage = (type, handler) => {
    if (!messageHandlers.value.has(type)) {
      messageHandlers.value.set(type, [])
    }
    messageHandlers.value.get(type).push(handler)
  }

  const handleMessage = (message) => {
    // Handle existing message types
    switch (message.type) {
      case 'new_post':
        postsStore.addPost(message.data)
        break
      case 'alert':
        notificationsStore.addAlert(message.data)
        break
    }
    
    // Handle custom message handlers
    const handlers = messageHandlers.value.get(message.type)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(message.data)
        } catch (error) {
          console.error(`Error in message handler for ${message.type}:`, error)
        }
      })
    } else {
      console.log('Unknown message type:', message.type)
    }
  }

  return {
    socket,
    isConnected,
    connect,
    disconnect,
    sendMessage,
    onMessage
  }
})