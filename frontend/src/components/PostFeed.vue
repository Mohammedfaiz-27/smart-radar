<template>
  <div class="space-y-4">
    <!-- Loading State -->
    <div v-if="loading" class="text-center py-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
      <p class="mt-2 text-sm text-gray-500">Loading posts...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="posts.length === 0" class="text-center py-8">
      <p class="text-gray-500">No posts found</p>
    </div>

    <!-- Posts List -->
    <div v-else class="space-y-4 max-h-96 overflow-y-auto">
      <PostCard
        v-for="post in posts"
        :key="post.id"
        :post="post"
        :feed-type="feedType"
        @respond="handleRespond"
        @create-post="handleCreatePost"
        @news-card="handleNewsCard"
      />
    </div>
  </div>

  <!-- Content Creator modal -->
  <ContentCreator
    :is-open="contentCreatorOpen"
    :post="activePost"
    @close="contentCreatorOpen = false"
  />

  <!-- News Card Generator -->
  <NewsCardGenerator
    :is-open="newsCardOpen"
    :post="activePost"
    @close="newsCardOpen = false"
  />
</template>

<script setup>
import { ref } from 'vue'
import PostCard from './PostCard.vue'
import ContentCreator from './ContentCreator.vue'
import NewsCardGenerator from './NewsCardGenerator.vue'

defineProps({
  posts: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  feedType: {
    type: String,
    required: true,
    validator: (value) => ['own', 'competitor'].includes(value)
  }
})

const emit = defineEmits(['respond'])

const activePost = ref(null)
const contentCreatorOpen = ref(false)
const newsCardOpen = ref(false)

const handleRespond = (post) => {
  emit('respond', post)
}

const handleCreatePost = (post) => {
  activePost.value = post
  contentCreatorOpen.value = true
}

const handleNewsCard = (post) => {
  activePost.value = post
  newsCardOpen.value = true
}
</script>