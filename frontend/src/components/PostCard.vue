<template>
  <div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
    <!-- Post Header -->
    <div class="flex items-start justify-between mb-3">
      <div class="flex items-center space-x-3">
        <div class="flex-shrink-0">
          <div :class="platformIconClasses">
            <component :is="platformIcon" class="h-4 w-4" />
          </div>
        </div>
        <div>
          <p class="text-sm font-medium text-gray-900">
            {{ post.author }}
          </p>
          <p class="text-xs text-gray-500">
            {{ formatDate(post.posted_at) }}
          </p>
        </div>
      </div>
      
      <!-- Threat Badge -->
      <div v-if="post.intelligence?.is_threat" class="flex items-center space-x-2">
        <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
          <ExclamationTriangleIcon class="h-3 w-3 mr-1" />
          Threat
        </span>
      </div>
    </div>

    <!-- Post Content -->
    <div class="mb-3">
      <p class="text-sm text-gray-900 line-clamp-3">
        {{ post.content }}
      </p>
    </div>

    <!-- Metrics Row -->
    <div class="flex items-center justify-between text-xs text-gray-500 mb-3">
      <div class="flex items-center space-x-4">
        <span>{{ post.engagement_metrics?.likes || 0 }} likes</span>
        <span>{{ post.engagement_metrics?.shares || 0 }} shares</span>
        <span>{{ post.engagement_metrics?.comments || 0 }} comments</span>
      </div>

      <!-- Sentiment -->
      <div class="flex items-center space-x-1">
        <span :class="sentimentClasses">
          {{ post.intelligence?.sentiment_label || 'Unknown' }}
        </span>
        <span class="text-gray-400">
          ({{ (post.intelligence?.sentiment_score || 0).toFixed(2) }})
        </span>
      </div>
    </div>

    <!-- Multi-Entity Sentiment Analysis Section -->
    <div v-if="hasEntitySentiments" class="entity-sentiments mb-3 pt-3 border-t border-gray-200">
      <h4 class="text-xs font-semibold text-gray-700 mb-2">📊 Entity Sentiment Analysis:</h4>

      <div class="entity-badges flex flex-wrap gap-2">
        <div
          v-for="(sentiment, entity) in post.entity_sentiments"
          :key="entity"
          :class="[
            'entity-badge px-3 py-1.5 rounded-lg border-2 flex items-center space-x-2 transition-all',
            getEntitySentimentClass(sentiment.label),
            isPrimaryEntity(entity) ? 'ring-2 ring-offset-1 ring-blue-500' : ''
          ]"
          :title="`Confidence: ${(sentiment.confidence * 100).toFixed(0)}%`"
        >
          <!-- Primary Entity Indicator -->
          <span v-if="isPrimaryEntity(entity)" class="text-blue-600" title="Primary cluster">
            🎯
          </span>

          <!-- Entity Name -->
          <span class="entity-name font-bold text-sm">{{ entity }}</span>

          <!-- Sentiment Score -->
          <span class="sentiment-score text-xs font-mono">
            {{ sentiment.score > 0 ? '+' : '' }}{{ sentiment.score.toFixed(2) }}
          </span>

          <!-- Sentiment Label -->
          <span class="sentiment-label text-xs uppercase font-medium">
            {{ sentiment.label }}
          </span>

          <!-- Confidence -->
          <span class="confidence text-xs opacity-75">
            ({{ (sentiment.confidence * 100).toFixed(0) }}%)
          </span>

          <!-- Sarcasm Indicator -->
          <span
            v-if="sentiment.sarcasm_detected"
            class="sarcasm-badge ml-1"
            :title="sentiment.sarcasm_reasoning || 'Sarcasm detected'"
          >
            🙄
          </span>

          <!-- Threat Indicator -->
          <span
            v-if="sentiment.threat_level > 0.3"
            :class="['threat-badge ml-1', getThreatClass(sentiment.threat_level)]"
            :title="sentiment.threat_reasoning || 'Potential threat detected'"
          >
            ⚠️
          </span>
        </div>
      </div>

      <!-- Comparative Analysis Indicator -->
      <div
        v-if="post.comparative_analysis?.has_comparison"
        class="comparison-badge mt-2 p-2 bg-blue-50 border border-blue-200 rounded-md text-sm"
      >
        <div class="flex items-center space-x-2">
          <svg class="w-4 h-4 text-blue-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
          </svg>
          <div class="flex-1">
            <span class="text-blue-800 font-medium">
              {{ post.comparative_analysis.comparison_type }}:
            </span>
            <span class="text-blue-700 ml-1">
              {{ post.comparative_analysis.relationship }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex items-center justify-between">
      <a 
        :href="post.post_url" 
        target="_blank" 
        class="text-xs text-primary-600 hover:text-primary-700"
      >
        View Original
      </a>
      
      <div class="flex items-center space-x-2">
        <button 
          v-if="!post.has_been_responded_to"
          @click="handleRespond"
          class="btn-primary text-xs px-3 py-1"
        >
          {{ getButtonText }}
        </button>
        <span 
          v-else 
          class="text-xs text-green-600 font-medium"
        >
          ✓ Responded
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { 
  ExclamationTriangleIcon,
  ChatBubbleLeftIcon,
  BuildingOfficeIcon
} from '@heroicons/vue/24/outline'
import { useResponseStore } from '@/stores/response'

const props = defineProps({
  post: {
    type: Object,
    required: true
  },
  feedType: {
    type: String,
    required: true
  }
})

const responseStore = useResponseStore()

const handleRespond = () => {
  responseStore.openResponsePanel(props.post)
}

const platformIcon = computed(() => {
  const iconMap = {
    twitter: ChatBubbleLeftIcon,
    facebook: BuildingOfficeIcon,
    instagram: BuildingOfficeIcon,
    linkedin: BuildingOfficeIcon
  }
  return iconMap[props.post.platform] || ChatBubbleLeftIcon
})

const platformIconClasses = computed(() => {
  const baseClasses = 'p-1 rounded'
  const colorMap = {
    twitter: 'bg-blue-100 text-blue-600',
    facebook: 'bg-blue-100 text-blue-600',
    instagram: 'bg-pink-100 text-pink-600',
    linkedin: 'bg-blue-100 text-blue-600'
  }
  return `${baseClasses} ${colorMap[props.post.platform] || 'bg-gray-100 text-gray-600'}`
})

const sentimentClasses = computed(() => {
  const sentiment = props.post.intelligence?.sentiment_label?.toLowerCase()
  const baseClasses = 'px-2 py-1 rounded-full text-xs font-medium'
  
  switch (sentiment) {
    case 'positive':
      return `${baseClasses} bg-green-100 text-green-800`
    case 'negative':
      return `${baseClasses} bg-red-100 text-red-800`
    case 'neutral':
      return `${baseClasses} bg-gray-100 text-gray-800`
    default:
      return `${baseClasses} bg-gray-100 text-gray-800`
  }
})

const getButtonText = computed(() => {
  const sentiment = props.post.intelligence?.sentiment_label?.toLowerCase()
  const isCompetitor = props.feedType === 'competitors' || props.post.cluster_type === 'competitor'
  const isNegative = sentiment === 'negative'

  // Show "Opportunities" for competitor negative posts
  if (isCompetitor && isNegative) {
    return 'Opportunities'
  }

  return 'Respond'
})

// Multi-entity sentiment helpers
const hasEntitySentiments = computed(() => {
  return props.post.entity_sentiments && Object.keys(props.post.entity_sentiments).length > 0
})

const getEntitySentimentClass = (label) => {
  const labelLower = label?.toLowerCase()
  const classes = {
    'positive': 'bg-green-50 border-green-300 text-green-800',
    'negative': 'bg-red-50 border-red-300 text-red-800',
    'neutral': 'bg-gray-50 border-gray-300 text-gray-700'
  }
  return classes[labelLower] || classes['neutral']
}

const isPrimaryEntity = (entityName) => {
  // The primary entity is the one whose cluster this post belongs to
  // We can determine this by checking if the entity matches the cluster name
  // Or by checking if the entity sentiment score matches the overall sentiment score
  if (!props.post.entity_sentiments) return false

  const entitySentiment = props.post.entity_sentiments[entityName]
  const overallScore = props.post.intelligence?.sentiment_score || props.post.sentiment_score

  // Primary entity has sentiment score matching overall score
  return entitySentiment && Math.abs(entitySentiment.score - overallScore) < 0.01
}

const getThreatClass = (level) => {
  if (level >= 0.7) return 'text-red-600'
  if (level >= 0.5) return 'text-orange-600'
  return 'text-yellow-600'
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  const now = new Date()
  const diff = now - date
  
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days < 7) return `${days}d ago`
  
  return date.toLocaleDateString()
}
</script>

<style scoped>
.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>