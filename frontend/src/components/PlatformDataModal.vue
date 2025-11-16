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
        class="inline-block w-full max-w-6xl p-6 my-8 overflow-hidden text-left align-middle transition-all transform bg-white shadow-xl rounded-2xl"
        @click.stop
      >
        <!-- Header -->
        <div class="flex items-center justify-between mb-6">
          <div>
            <h3 class="text-2xl font-bold text-gray-900">
              {{ modalTitle }}
            </h3>
            <p class="text-sm text-gray-500 mt-1">
              Posts grouped by platform
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

        <!-- Platform Info Header -->
        <div class="mb-6 bg-gray-50 p-4 rounded-lg">
          <div class="flex items-center justify-center space-x-3">
            <component :is="getPlatformIcon(currentPlatform)" class="h-6 w-6 text-gray-600" />
            <span class="text-lg font-medium text-gray-900">{{ formatPlatformName(currentPlatform) }}</span>
            <span class="text-sm bg-blue-100 text-blue-800 px-3 py-1 rounded-full font-medium">
              {{ props.posts.length }} posts
            </span>
          </div>
        </div>

        <!-- Platform Data Display -->
        <div class="max-h-96 overflow-y-auto">
          <div v-if="loading" class="flex justify-center py-8">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
          
          <div v-else-if="props.posts.length === 0" class="text-center py-8 text-gray-500">
            No posts found for {{ formatPlatformName(currentPlatform) }}
          </div>
          
          <div v-else class="space-y-4">
            <div
              v-for="post in props.posts"
              :key="post.id"
              class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
            >
              <div class="flex items-start justify-between">
                <div class="flex-1">
                  <!-- Post Header -->
                  <div class="flex items-center space-x-3 mb-3">
                    <component :is="getPlatformIcon(post.platform)" class="h-6 w-6 text-gray-500" />
                    <span class="font-medium text-gray-900">{{ post.author }}</span>
                    <span class="text-sm text-gray-500">
                      {{ formatDate(post.posted_at) }}
                    </span>
                    <span 
                      :class="[
                        'px-2 py-1 text-xs rounded-full font-medium',
                        post.cluster_type === 'own' 
                          ? 'bg-blue-100 text-blue-800' 
                          : 'bg-orange-100 text-orange-800'
                      ]"
                    >
                      {{ post.cluster_type === 'own' ? 'Our Organization' : 'Competitor' }}
                    </span>
                  </div>

                  <!-- Post Content -->
                  <p class="text-gray-800 mb-3 leading-relaxed">
                    {{ post.content }}
                  </p>

                  <!-- View Original Link -->
                  <div class="mb-3">
                    <a 
                      :href="post.post_url" 
                      target="_blank"
                      rel="noopener noreferrer"
                      class="inline-flex items-center space-x-1 text-sm text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                      <span>View Original Post</span>
                    </a>
                  </div>

                  <!-- Metrics Row -->
                  <div class="flex items-center justify-between">
                    <!-- Engagement Metrics -->
                    <div class="flex items-center space-x-4 text-sm text-gray-500">
                      <span class="flex items-center space-x-1">
                        <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
                        </svg>
                        <span>{{ post.engagement_metrics?.likes || 0 }}</span>
                      </span>
                      <span class="flex items-center space-x-1">
                        <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fill-rule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clip-rule="evenodd" />
                        </svg>
                        <span>{{ post.engagement_metrics?.comments || 0 }}</span>
                      </span>
                      <span class="flex items-center space-x-1">
                        <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M15 8a3 3 0 10-2.977-2.63l-4.94 2.47a3 3 0 100 4.319l4.94 2.47a3 3 0 10.895-1.789l-4.94-2.47a3.027 3.027 0 000-.74l4.94-2.47C13.456 7.68 14.19 8 15 8z" />
                        </svg>
                        <span>{{ post.engagement_metrics?.shares || 0 }}</span>
                      </span>
                    </div>

                    <!-- Sentiment & Threat -->
                    <div class="flex items-center space-x-3">
                      <span 
                        :class="[
                          'px-2 py-1 text-xs rounded-full font-medium',
                          getSentimentColor(post.intelligence?.sentiment_score)
                        ]"
                      >
                        {{ getSentimentLabel(post.intelligence?.sentiment_score) }}
                      </span>
                      <span 
                        v-if="post.intelligence?.is_threat"
                        class="px-2 py-1 text-xs rounded-full font-medium bg-red-100 text-red-800"
                      >
                        🚨 Threat
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex justify-between items-center mt-6 pt-4 border-t border-gray-200">
          <p class="text-sm text-gray-500">
            Showing {{ props.posts.length }} posts from {{ formatPlatformName(currentPlatform) }}
          </p>
          <button
            @click="closeModal"
            class="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors"
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
import { 
  GlobeAltIcon,
  PlayIcon,
  ChatBubbleLeftRightIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    required: true
  },
  posts: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  platform: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close'])

const modalTitle = computed(() => {
  return `${props.title} - Platform Breakdown`
})

const currentPlatform = computed(() => {
  // Extract platform from the first post if available, or use the passed platform prop
  return props.platform || (props.posts.length > 0 ? props.posts[0].platform : 'unknown')
})

const getPlatformIcon = (platform) => {
  const iconMap = {
    'x': ChatBubbleLeftRightIcon,
    'twitter': ChatBubbleLeftRightIcon,
    'facebook': GlobeAltIcon,
    'youtube': PlayIcon,
    'all': GlobeAltIcon
  }
  return iconMap[platform] || GlobeAltIcon
}

const formatPlatformName = (platform) => {
  const nameMap = {
    'x': 'X (Twitter)',
    'twitter': 'X (Twitter)',
    'facebook': 'Facebook',
    'youtube': 'YouTube',
    'all': 'All Platforms'
  }
  return nameMap[platform] || platform.charAt(0).toUpperCase() + platform.slice(1)
}

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString()
}

const getSentimentColor = (score) => {
  if (score === null || score === undefined) return 'bg-gray-100 text-gray-600'
  if (score > 0.3) return 'bg-green-100 text-green-800'
  if (score < -0.3) return 'bg-red-100 text-red-800'
  return 'bg-yellow-100 text-yellow-800'
}

const getSentimentLabel = (score) => {
  if (score === null || score === undefined) return 'Unknown'
  if (score > 0.3) return 'Positive'
  if (score < -0.3) return 'Negative'
  return 'Neutral'
}

const closeModal = () => {
  emit('close')
}
</script>