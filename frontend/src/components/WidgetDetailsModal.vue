<template>
  <div 
    v-if="isOpen" 
    class="fixed inset-0 z-50 overflow-y-auto"
    @click="closeModal"
  >
    <div class="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
      <!-- Background overlay -->
      <div class="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"></div>
      
      <!-- Modal panel -->
      <div 
        class="inline-block w-full max-w-4xl p-6 my-8 overflow-hidden text-left align-middle transition-all transform bg-white shadow-xl rounded-2xl"
        @click.stop
      >
        <!-- Header -->
        <div class="flex items-center justify-between mb-6">
          <div>
            <h3 class="text-2xl font-bold text-gray-900">
              {{ modalTitle }}
            </h3>
            <p class="text-sm text-gray-500 mt-1">
              {{ modalSubtitle }}
            </p>
          </div>
          <button
            @click="closeModal"
            class="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Stats Header -->
        <div class="mb-6 bg-gray-50 p-4 rounded-lg">
          <div class="flex items-center justify-center space-x-3">
            <component :is="getWidgetIcon()" class="h-6 w-6" :class="getWidgetIconColor()" />
            <span class="text-lg font-medium text-gray-900">{{ getWidgetTypeLabel() }}</span>
            <span class="text-sm bg-blue-100 text-blue-800 px-3 py-1 rounded-full font-medium">
              {{ posts.length }} posts
            </span>
          </div>
        </div>

        <!-- Posts List -->
        <div class="max-h-96 overflow-y-auto">
          <div v-if="loading" class="flex justify-center py-8">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span class="ml-3 text-gray-600">Loading posts...</span>
          </div>
          
          <div v-else-if="posts.length === 0" class="text-center py-8 text-gray-500">
            No posts found for this category
          </div>
          
          <div v-else class="space-y-4">
            <div
              v-for="post in posts"
              :key="post.id"
              class="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
            >
              <!-- Post Header -->
              <div class="flex items-start justify-between mb-3">
                <div class="flex items-center space-x-3">
                  <div class="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                    <span class="text-sm font-medium text-blue-600">
                      {{ post.platform?.charAt(0)?.toUpperCase() || 'P' }}
                    </span>
                  </div>
                  <div>
                    <p class="text-sm font-medium text-gray-900">{{ post.author }}</p>
                    <p class="text-xs text-gray-500">{{ formatDate(post.posted_at) }}</p>
                  </div>
                </div>
                
                <!-- Sentiment Badge -->
                <span 
                  class="px-2 py-1 text-xs rounded-full font-medium"
                  :class="getSentimentBadgeClass(post.sentiment)"
                >
                  {{ post.sentiment }}
                </span>
              </div>

              <!-- Post Content -->
              <div class="mb-3">
                <p class="text-gray-700 text-sm leading-relaxed">
                  {{ post.content }}
                </p>
              </div>

              <!-- Engagement Metrics -->
              <div class="flex items-center justify-between text-xs text-gray-500 mb-3">
                <span class="capitalize">{{ post.cluster_type }} • {{ post.platform }}</span>
                <div class="flex items-center space-x-4">
                  <span v-if="post.engagement_metrics?.likes">
                    👍 {{ post.engagement_metrics.likes }}
                  </span>
                  <span v-if="post.engagement_metrics?.shares">
                    🔄 {{ post.engagement_metrics.shares }}
                  </span>
                  <span v-if="post.engagement_metrics?.comments">
                    💬 {{ post.engagement_metrics.comments }}
                  </span>
                </div>
              </div>

              <!-- Action Buttons -->
              <div class="flex items-center justify-between pt-3 border-t border-gray-200">
                <!-- Source Link -->
                <a 
                  v-if="post.url || post.post_url"
                  :href="post.url || post.post_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="flex items-center space-x-2 text-blue-600 hover:text-blue-800 transition-colors"
                >
                  <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                  <span class="text-sm font-medium">View Source</span>
                </a>
                
                <!-- Respond Button -->
                <button
                  @click="handleRespond(post)"
                  class="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-green-500 to-emerald-600 text-white text-sm font-medium rounded-lg hover:from-green-600 hover:to-emerald-700 transition-all transform hover:scale-105 shadow-sm"
                >
                  <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                  <span>Respond</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="mt-6 flex justify-end">
          <button
            @click="closeModal"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useResponseStore } from '@/stores/response'
import { usePostsStore } from '@/stores/posts'

// Stores
const responseStore = useResponseStore()
const postsStore = usePostsStore()

// Props
const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  widgetType: {
    type: String,
    default: '',
    validator: value => ['positive', 'negative', 'opportunities', ''].includes(value)
  }
})

// Emits
const emit = defineEmits(['close'])

// State
const posts = ref([])
const loading = ref(false)

// Computed properties
const modalTitle = computed(() => {
  switch (props.widgetType) {
    case 'positive':
      return 'Positive Posts'
    case 'negative':
      return 'Negative Posts'
    case 'opportunities':
      return 'Opportunities'
    default:
      return 'Posts'
  }
})

const modalSubtitle = computed(() => {
  switch (props.widgetType) {
    case 'positive':
      return 'Own posts with positive sentiment'
    case 'negative':
      return 'Own posts with negative sentiment requiring attention'
    case 'opportunities':
      return 'Competitor posts with negative sentiment'
    default:
      return 'Post details'
  }
})

// Methods
const closeModal = () => {
  emit('close')
}

const getWidgetIcon = () => {
  switch (props.widgetType) {
    case 'positive':
      return 'svg'
    case 'negative':
      return 'svg'
    case 'opportunities':
      return 'svg'
    default:
      return 'svg'
  }
}

const getWidgetIconColor = () => {
  switch (props.widgetType) {
    case 'positive':
      return 'text-green-600'
    case 'negative':
      return 'text-red-600'
    case 'opportunities':
      return 'text-purple-600'
    default:
      return 'text-gray-600'
  }
}

const getWidgetTypeLabel = () => {
  switch (props.widgetType) {
    case 'positive':
      return 'Positive Sentiment'
    case 'negative':
      return 'Negative Sentiment'
    case 'opportunities':
      return 'Competitor Insights'
    default:
      return 'Posts'
  }
}

const getSentimentBadgeClass = (sentiment) => {
  switch (sentiment?.toLowerCase()) {
    case 'positive':
      return 'bg-green-100 text-green-800'
    case 'negative':
      return 'bg-red-100 text-red-800'
    case 'neutral':
      return 'bg-gray-100 text-gray-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const handleRespond = (post) => {
  // Open the response panel with the selected post
  responseStore.openResponsePanel(post)
  // Close the widget modal
  closeModal()
}

const fetchPosts = async () => {
  if (!props.widgetType || !props.isOpen) return

  try {
    loading.value = true

    // Fetch all posts from store
    await postsStore.fetchPosts()

    // Filter posts based on widget type
    const allPosts = postsStore.posts

    switch (props.widgetType) {
      case 'positive':
        // Own organization positive sentiment posts
        posts.value = allPosts.filter(post =>
          post.cluster_type === 'own' && post.sentiment === 'positive'
        )
        break

      case 'negative':
        // Own organization negative sentiment posts
        posts.value = allPosts.filter(post =>
          post.cluster_type === 'own' && post.sentiment === 'negative'
        )
        break

      case 'opportunities':
        // Competitor negative sentiment posts (opportunities)
        posts.value = allPosts.filter(post =>
          post.cluster_type === 'competitor' && post.sentiment === 'negative'
        )
        break

      default:
        posts.value = []
    }

    console.log(`📊 Loaded ${posts.value.length} posts for ${props.widgetType}`)

  } catch (error) {
    console.error('Error fetching widget posts:', error)
    posts.value = []
  } finally {
    loading.value = false
  }
}

// Watch for modal open/close and widget type changes
watch(() => [props.isOpen, props.widgetType], () => {
  if (props.isOpen && props.widgetType) {
    fetchPosts()
  } else {
    posts.value = []
  }
}, { immediate: true })
</script>