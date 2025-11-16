<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
      <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="$emit('close')"></div>

        <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <form @submit.prevent="save">
            <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg leading-6 font-medium text-gray-900">
                  {{ cluster ? 'Edit Cluster' : 'Create New Cluster' }}
                </h3>
                <button type="button" @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
                  <XMarkIcon class="h-6 w-6" />
                </button>
              </div>

              <div class="space-y-4">
                <!-- Cluster Name -->
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    Cluster Name
                  </label>
                  <input
                    v-model="form.name"
                    type="text"
                    required
                    class="input"
                    placeholder="e.g., Healthcare Policy Opposition"
                  />
                </div>

                <!-- Cluster Type -->
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    Cluster Type
                  </label>
                  <select v-model="form.cluster_type" required class="input">
                    <option value="">Select type...</option>
                    <option value="own">Our Organization</option>
                    <option value="competitor">Competitor</option>
                  </select>
                </div>

                <!-- Keywords -->
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    Keywords & Hashtags
                  </label>
                  <div class="space-y-2">
                    <div 
                      v-for="(keyword, index) in form.keywords" 
                      :key="index"
                      class="flex items-center space-x-2"
                    >
                      <input
                        v-model="form.keywords[index]"
                        type="text"
                        class="input"
                        placeholder="e.g., #HealthcareFail or @competitor"
                      />
                      <button
                        type="button"
                        @click="removeKeyword(index)"
                        class="text-red-500 hover:text-red-700"
                      >
                        <XMarkIcon class="h-5 w-5" />
                      </button>
                    </div>
                    <button
                      type="button"
                      @click="addKeyword"
                      class="btn-secondary text-sm"
                    >
                      Add Keyword
                    </button>
                  </div>
                </div>

                <!-- Thresholds -->
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    Engagement Thresholds
                  </label>
                  <div class="grid grid-cols-2 gap-4">
                    <div>
                      <label class="block text-xs text-gray-500 mb-1">Min Likes (Twitter)</label>
                      <input
                        v-model.number="form.thresholds.twitter.min_likes"
                        type="number"
                        min="0"
                        class="input"
                        placeholder="500"
                      />
                    </div>
                    <div>
                      <label class="block text-xs text-gray-500 mb-1">Min Shares (Twitter)</label>
                      <input
                        v-model.number="form.thresholds.twitter.min_shares"
                        type="number"
                        min="0"
                        class="input"
                        placeholder="50"
                      />
                    </div>
                  </div>
                </div>

                <!-- Active Status -->
                <div class="flex items-center">
                  <input
                    v-model="form.is_active"
                    type="checkbox"
                    id="is_active"
                    class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label for="is_active" class="ml-2 block text-sm text-gray-700">
                    Active (will collect posts)
                  </label>
                </div>
              </div>
            </div>

            <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
              <button
                type="submit"
                :disabled="loading"
                class="btn-primary w-full sm:w-auto sm:ml-3"
              >
                {{ loading ? 'Saving...' : 'Save Cluster' }}
              </button>
              <button
                type="button"
                @click="$emit('close')"
                class="btn-secondary w-full sm:w-auto mt-3 sm:mt-0"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { XMarkIcon } from '@heroicons/vue/24/outline'
import { clustersApi } from '@/services/api'

const props = defineProps({
  cluster: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'save'])

const loading = ref(false)
const form = ref({
  name: '',
  cluster_type: '',
  keywords: [''],
  thresholds: {
    twitter: {
      min_likes: 500,
      min_shares: 50
    }
  },
  is_active: true
})

const addKeyword = () => {
  form.value.keywords.push('')
}

const removeKeyword = (index) => {
  if (form.value.keywords.length > 1) {
    form.value.keywords.splice(index, 1)
  }
}

const save = async () => {
  loading.value = true
  
  try {
    // Filter out empty keywords
    const cleanedForm = {
      ...form.value,
      keywords: form.value.keywords.filter(k => k.trim() !== '')
    }

    if (props.cluster) {
      await clustersApi.update(props.cluster.id, cleanedForm)
    } else {
      await clustersApi.create(cleanedForm)
    }
    
    emit('save')
  } catch (error) {
    console.error('Failed to save cluster:', error)
    alert('Failed to save cluster. Please try again.')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (props.cluster) {
    form.value = {
      name: props.cluster.name,
      cluster_type: props.cluster.cluster_type,
      keywords: [...props.cluster.keywords],
      thresholds: { ...props.cluster.thresholds },
      is_active: props.cluster.is_active
    }
  }
})
</script>