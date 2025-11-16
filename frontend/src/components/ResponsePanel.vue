<template>
  <!-- Modal Overlay -->
  <Teleport to="body">
    <div 
      v-if="responseStore.isResponsePanelOpen" 
      class="fixed inset-0 z-50 overflow-y-auto"
      aria-labelledby="modal-title" 
      role="dialog" 
      aria-modal="true"
    >
      <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <!-- Background overlay -->
        <div 
          class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          @click="responseStore.closeResponsePanel"
        ></div>

        <!-- Modal panel -->
        <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
          <!-- Header -->
          <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg leading-6 font-medium text-gray-900">
                Generate AI-Autonomous Response
              </h3>
              <button 
                @click="responseStore.closeResponsePanel"
                class="text-gray-400 hover:text-gray-600"
              >
                <XMarkIcon class="h-6 w-6" />
              </button>
            </div>

            <!-- Original Post Display -->
            <div class="mb-6">
              <h4 class="text-sm font-medium text-gray-700 mb-2">Original Post</h4>
              <div class="bg-gray-50 p-4 rounded-lg">
                <div class="flex items-center mb-2">
                  <span class="text-sm font-medium text-gray-900">
                    {{ responseStore.currentPost?.author_username || responseStore.currentPost?.author?.username || 'Unknown' }}
                  </span>
                  <span class="ml-2 text-xs text-gray-500">
                    on {{ responseStore.currentPost?.platform }}
                  </span>
                </div>
                <p class="text-sm text-gray-700">
                  {{ responseStore.currentPost?.content || responseStore.currentPost?.post_text || responseStore.currentPost?.content?.text || 'No content' }}
                </p>
                <div class="mt-2 flex items-center space-x-4 text-xs text-gray-500">
                  <span>{{ responseStore.currentPost?.engagement_metrics?.likes || responseStore.currentPost?.engagement?.likes || 0 }} likes</span>
                  <span class="capitalize">
                    {{ responseStore.currentPost?.sentiment || responseStore.currentPost?.intelligence?.sentiment_label || 'neutral' }} sentiment
                  </span>
                </div>
              </div>
            </div>

            <!-- Response Configuration -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <!-- Tone Selector -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  Select Tone
                </label>
                <select 
                  v-model="responseStore.selectedTone"
                  class="input"
                  @change="responseStore.responseOptions = []"
                >
                  <option value="Sarcastic">Sarcastic (Mockery & Rhetorical)</option>
                  <option value="Assertive">Assertive (Direct & Aggressive)</option>
                  <option value="Professional">Professional (Measured & Firm)</option>
                </select>
              </div>

              <!-- Language Selector -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  Select Language
                </label>
                <select 
                  v-model="responseStore.selectedLanguage"
                  class="input"
                  @change="responseStore.responseOptions = []"
                >
                  <option value="Tamil">Tamil</option>
                  <option value="English">English</option>
                </select>
              </div>
            </div>


            <!-- Generate Button -->
            <div class="mb-6">
              <button 
                @click="responseStore.generateResponse"
                :disabled="!responseStore.currentPost || responseStore.loading"
                class="btn-primary w-full"
              >
                <span v-if="responseStore.loading" class="flex items-center justify-center">
                  <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  AI Fact-Finding & Generating...
                </span>
                <span v-else>Generate AI-Autonomous Responses</span>
              </button>
            </div>

            <!-- Response Options -->
            <div v-if="responseStore.responseOptions.length > 0" class="mb-6">
              <label class="block text-sm font-medium text-gray-700 mb-3">
                Select Response Option (AI-Generated with Fact-Finding)
              </label>
              <div class="space-y-4">
                <div 
                  v-for="(option, index) in responseStore.responseOptions" 
                  :key="index" 
                  class="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer transition-colors"
                  :class="{ 'border-blue-500 bg-blue-50': responseStore.selectedOption === index }"
                  @click="responseStore.selectedOption = index"
                >
                  <div class="flex items-start">
                    <input 
                      type="radio" 
                      :id="`option-${index}`"
                      v-model="responseStore.selectedOption"
                      :value="index"
                      class="mt-1 mr-3 text-blue-600"
                    >
                    <div class="flex-1">
                      <label 
                        :for="`option-${index}`" 
                        class="text-sm text-gray-700 cursor-pointer leading-relaxed"
                      >
                        {{ option }}
                      </label>
                      <div class="mt-2 text-xs text-gray-500">
                        Option {{ index + 1 }} • {{ option.length }} characters
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Strategic Principles Info -->
            <div v-if="responseStore.responseOptions.length > 0" class="mb-6">
              <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h5 class="text-sm font-medium text-blue-900 mb-2">AI-Autonomous Strategic Playbook Applied:</h5>
                <ul class="text-xs text-blue-800 space-y-1">
                  <li>• Internal fact-finding and verification performed</li>
                  <li>• Mock the premise as misinformation</li>
                  <li>• Attack & counter with devastating facts</li>
                  <li>• Reframe narrative (DMK beneficial vs opponent harmful)</li>
                  <li>• Dismiss and dominate with M.K. Stalin's legacy</li>
                </ul>
              </div>
            </div>

            <!-- Error Display -->
            <div v-if="responseStore.error" class="mb-4">
              <div class="bg-red-50 border border-red-200 rounded-md p-3">
                <div class="flex">
                  <ExclamationTriangleIcon class="h-5 w-5 text-red-400" />
                  <div class="ml-3">
                    <p class="text-sm text-red-700">
                      {{ responseStore.error }}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Footer Actions -->
          <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button 
              v-if="responseStore.responseOptions.length > 0 && responseStore.selectedOption !== null"
              @click="copyResponse"
              class="btn-primary w-full sm:w-auto sm:ml-3"
            >
              Copy Selected Response
            </button>
            <button 
              @click="responseStore.closeResponsePanel"
              class="btn-secondary w-full sm:w-auto mt-3 sm:mt-0"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { XMarkIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import { useResponseStore } from '@/stores/response'
import { useNotificationsStore } from '@/stores/notifications'

const responseStore = useResponseStore()
const notificationsStore = useNotificationsStore()

const copyResponse = async () => {
  const success = await responseStore.copyToClipboard()
  if (success) {
    notificationsStore.addNotification({
      type: 'success',
      title: 'Response Copied',
      message: 'Strategic response has been copied to clipboard and logged'
    })
  } else {
    notificationsStore.addNotification({
      type: 'error',
      title: 'Copy Failed',
      message: 'Failed to copy response to clipboard'
    })
  }
}
</script>