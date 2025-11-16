import { defineStore } from 'pinia'
import { ref } from 'vue'
import { responsesApi } from '@/services/api'

export const useResponseStore = defineStore('response', () => {
  const isResponsePanelOpen = ref(false)
  const currentPost = ref(null)
  const selectedTone = ref('Sarcastic')
  const selectedLanguage = ref('Tamil')
  const responseOptions = ref([])
  const selectedOption = ref(null)
  const loading = ref(false)
  const error = ref(null)

  const openResponsePanel = (post) => {
    currentPost.value = post
    isResponsePanelOpen.value = true
    selectedTone.value = 'Sarcastic'
    selectedLanguage.value = 'Tamil'
    responseOptions.value = []
    selectedOption.value = null
    error.value = null
  }

  const closeResponsePanel = () => {
    isResponsePanelOpen.value = false
    currentPost.value = null
    selectedTone.value = 'Sarcastic'
    selectedLanguage.value = 'Tamil'
    responseOptions.value = []
    selectedOption.value = null
    error.value = null
  }

  const getSelectedResponse = () => {
    if (selectedOption.value !== null && responseOptions.value[selectedOption.value]) {
      return responseOptions.value[selectedOption.value]
    }
    return ''
  }

  const generateResponse = async () => {
    if (!currentPost.value) {
      error.value = 'No post selected'
      return
    }

    loading.value = true
    error.value = null

    try {
      const response = await responsesApi.generate({
        original_post_id: currentPost.value.id,
        tone: selectedTone.value,
        language: selectedLanguage.value
      })
      
      responseOptions.value = [
        response.data.option1,
        response.data.option2,
        response.data.option3
      ]
      
      // Auto-select first option
      selectedOption.value = 0
      
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to generate response'
      console.error('Error generating response:', err)
    } finally {
      loading.value = false
    }
  }

  const logResponse = async () => {
    const selectedResponse = getSelectedResponse()
    if (!currentPost.value || !selectedResponse) {
      error.value = 'Please select a response option'
      return
    }

    try {
      await responsesApi.log({
        original_post_id: currentPost.value.id,
        generated_text: selectedResponse,
        tone: selectedTone.value,
        language: selectedLanguage.value
      })
      
      // Mark post as responded in posts store
      const { usePostsStore } = await import('./posts')
      const postsStore = usePostsStore()
      await postsStore.markAsResponded(currentPost.value.id)
      
      return true
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to log response'
      console.error('Error logging response:', err)
      return false
    }
  }

  const copyToClipboard = async () => {
    const selectedResponse = getSelectedResponse()
    if (!selectedResponse) return false

    try {
      await navigator.clipboard.writeText(selectedResponse)
      
      // Log the response when copied
      const logged = await logResponse()
      if (logged) {
        closeResponsePanel()
      }
      
      return true
    } catch (err) {
      console.error('Failed to copy to clipboard:', err)
      return false
    }
  }

  return {
    isResponsePanelOpen,
    currentPost,
    selectedTone,
    selectedLanguage,
    responseOptions,
    selectedOption,
    loading,
    error,
    openResponsePanel,
    closeResponsePanel,
    getSelectedResponse,
    generateResponse,
    logResponse,
    copyToClipboard
  }
})