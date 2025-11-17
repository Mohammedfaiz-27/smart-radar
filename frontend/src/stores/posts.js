import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { contentApi, postsApi, getSmartApi, isApiV25 } from '@/services/api'

export const usePostsStore = defineStore('posts', () => {
  const posts = ref([])
  const loading = ref(false)
  const error = ref(null)
  const initialized = ref(false) // Track if data has been loaded

  // Helper function to transform monitored_content to legacy post format
  const transformContentToPost = (content) => {
    // Extract cluster type from matched_clusters
    const clusterType = content.matched_clusters?.length > 0 
      ? content.matched_clusters[0].cluster_type 
      : 'unknown'
    
    // Extract sentiment info from intelligence
    const sentiment = content.intelligence?.entity_sentiments || {}
    const threatLevel = content.intelligence?.threat_level || 'low'
    
    return {
      id: content._id || content.id,
      title: content.title,
      content: content.content,
      platform: content.platform,
      url: content.url,
      cluster_type: clusterType,
      collected_at: content.collected_at,
      
      // Intelligence data
      intelligence: content.intelligence,
      sentiment_analysis: sentiment,
      threat_level: threatLevel,
      is_threat: threatLevel === 'high' || threatLevel === 'critical',
      
      // Matched clusters info
      matched_clusters: content.matched_clusters || [],
      
      // Legacy compatibility
      has_been_responded_to: content.has_been_responded_to || false,
      
      // Additional metadata
      processing_status: content.processing_status,
      last_updated: content.last_updated
    }
  }

  const ownPosts = computed(() => 
    posts.value.filter(post => post.cluster_type === 'own')
  )

  const competitorPosts = computed(() => 
    posts.value.filter(post => post.cluster_type === 'competitor')
  )

  const threatPosts = computed(() => 
    posts.value.filter(post => 
      post.is_threat || 
      post.intelligence?.is_threat || 
      post.threat_level === 'high' || 
      post.threat_level === 'critical'
    )
  )

  // Platform-based filtering
  const getPostsByPlatform = (platform) => {
    return posts.value.filter(post => post.platform === platform)
  }

  const getOwnPostsByPlatform = (platform) => {
    return ownPosts.value.filter(post => post.platform === platform)
  }

  const getCompetitorPostsByPlatform = (platform) => {
    return competitorPosts.value.filter(post => post.platform === platform)
  }

  const getThreatPostsByPlatform = (platform) => {
    return threatPosts.value.filter(post => post.platform === platform)
  }

  const fetchPosts = async (filters = {}, force = false) => {
    // Skip fetching if already initialized and not forced, but only when we actually have data
    if (initialized.value && !force && Object.keys(filters).length === 0 && posts.value.length > 0) {
      console.log('📦 Using cached posts data:', posts.value.length, 'posts')
      return
    }

    loading.value = true
    error.value = null

    try {
      // Always use posts_table API for current data (bypass smart selector)
      console.log('📊 Fetching data from posts_table API', filters)
      const response = await postsApi.getAll(filters)
      posts.value = response.data
      initialized.value = true

      console.log(`✅ Loaded ${posts.value.length} posts with filters:`, filters)
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch posts'
      console.error('Error fetching posts:', err)
      // Don't mark as initialized if fetch failed
      initialized.value = false
    } finally {
      loading.value = false
    }
  }

  // Force refresh data from backend
  const refreshPosts = async (filters = {}) => {
    return await fetchPosts(filters, true)
  }

  const fetchOwnPosts = async () => {
    await fetchPosts({ cluster_type: 'own' })
  }

  const fetchCompetitorPosts = async () => {
    await fetchPosts({ cluster_type: 'competitor' })
  }

  const fetchThreats = async (filters = {}) => {
    loading.value = true
    error.value = null
    
    try {
      // Always use posts_table API for current data (bypass smart selector)
      console.log('⚠️ Fetching threats from posts_table API')
      const response = await postsApi.getThreats(filters)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch threat posts'
      console.error('Error fetching threat posts:', err)
      return []
    } finally {
      loading.value = false
    }
  }

  // Cluster-specific fetching functions
  const fetchPostsByCluster = async (clusterId, filters = {}) => {
    await fetchPosts({ ...filters, cluster_id: clusterId })
  }

  const fetchPostsByKeywords = async (keywords, filters = {}) => {
    await fetchPosts({ ...filters, keywords: keywords.join(',') })
  }

  const fetchPostsByClusterType = async (clusterType, platform = null, keywords = null) => {
    const filters = { cluster_type: clusterType }
    if (platform) filters.platform = platform
    if (keywords) filters.keywords = Array.isArray(keywords) ? keywords.join(',') : keywords
    await fetchPosts(filters)
  }

  // Enhanced filtering functions that accept cluster parameters
  const getPostsByCluster = (clusterData) => {
    if (!clusterData) return posts.value
    
    // Filter by cluster keywords if available
    if (clusterData.keywords && clusterData.keywords.length > 0) {
      return posts.value.filter(post => {
        const content = (post.content || '').toLowerCase()
        const title = (post.title || '').toLowerCase()
        
        return clusterData.keywords.some(keyword => 
          content.includes(keyword.toLowerCase()) || 
          title.includes(keyword.toLowerCase())
        )
      })
    }
    
    // Filter by cluster type
    return posts.value.filter(post => post.cluster_type === clusterData.cluster_type)
  }

  const addPost = (newPost) => {
    // Add new post to the beginning of the array
    posts.value.unshift(newPost)
  }

  const updatePost = (postId, updates) => {
    const index = posts.value.findIndex(post => post.id === postId)
    if (index !== -1) {
      posts.value[index] = { ...posts.value[index], ...updates }
    }
  }

  const markAsResponded = async (postId) => {
    try {
      await postsApi.markAsResponded(postId)
      updatePost(postId, { has_been_responded_to: true })
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to mark post as responded'
      console.error('Error marking post as responded:', err)
    }
  }

  return {
    posts,
    loading,
    error,
    initialized,
    ownPosts,
    competitorPosts,
    threatPosts,
    fetchPosts,
    refreshPosts,
    fetchOwnPosts,
    fetchCompetitorPosts,
    fetchThreats,
    addPost,
    updatePost,
    markAsResponded,
    getPostsByPlatform,
    getOwnPostsByPlatform,
    getCompetitorPostsByPlatform,
    getThreatPostsByPlatform,
    // Cluster-specific functions
    fetchPostsByCluster,
    fetchPostsByKeywords,
    fetchPostsByClusterType,
    getPostsByCluster
  }
})