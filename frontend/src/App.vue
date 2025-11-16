<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <router-view />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useWebSocketStore } from '@/stores/websocket'

const websocketStore = useWebSocketStore()

onMounted(() => {
  websocketStore.connect()
})
</script>