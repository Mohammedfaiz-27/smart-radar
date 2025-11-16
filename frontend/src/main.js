import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/css/main.css'
import { initializeApi } from '@/services/api'

const app = createApp(App)

app.use(createPinia())
app.use(router)

// Initialize API connection and features detection
initializeApi().then((apiInfo) => {
  console.log('🚀 SMART RADAR Frontend initialized with API version:', apiInfo.version)
  
  // Mount the app after API initialization
  app.mount('#app')
}).catch((error) => {
  console.warn('⚠️ API initialization failed, mounting app anyway:', error)
  
  // Mount the app even if API initialization fails
  app.mount('#app')
})