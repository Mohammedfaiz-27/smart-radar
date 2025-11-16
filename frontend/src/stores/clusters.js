import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { clustersApi } from '@/services/api'

export const useClustersStore = defineStore('clusters', () => {
  const clusters = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Computed properties for cluster grouping
  const ownClusters = computed(() => 
    clusters.value.filter(cluster => cluster.cluster_type === 'own')
  )

  const competitorClusters = computed(() => 
    clusters.value.filter(cluster => cluster.cluster_type === 'competitor')
  )

  const activeClusters = computed(() => 
    clusters.value.filter(cluster => cluster.is_active !== false)
  )

  // Get cluster by ID
  const getClusterById = (id) => {
    return clusters.value.find(cluster => cluster.id === id)
  }

  // Get cluster by name
  const getClusterByName = (name) => {
    return clusters.value.find(cluster => 
      cluster.name.toLowerCase() === name.toLowerCase()
    )
  }

  // Get clusters by type
  const getClustersByType = (type) => {
    return clusters.value.filter(cluster => cluster.cluster_type === type)
  }

  // Get clusters containing specific keywords
  const getClustersWithKeywords = (keywords) => {
    if (!Array.isArray(keywords)) keywords = [keywords]
    
    return clusters.value.filter(cluster => 
      cluster.keywords && cluster.keywords.some(keyword => 
        keywords.some(searchKeyword => 
          keyword.toLowerCase().includes(searchKeyword.toLowerCase())
        )
      )
    )
  }

  // Get all keywords from clusters of a specific type
  const getKeywordsByType = (clusterType) => {
    const relevantClusters = clusters.value.filter(cluster => 
      cluster.cluster_type === clusterType && cluster.is_active !== false
    )
    
    const allKeywords = relevantClusters.flatMap(cluster => cluster.keywords || [])
    return [...new Set(allKeywords)] // Remove duplicates
  }

  // Fetch all clusters
  const fetchClusters = async (filters = {}) => {
    loading.value = true
    error.value = null
    
    try {
      console.log('📊 Fetching clusters with filters:', filters)
      const response = await clustersApi.getAll(filters)
      clusters.value = response.data || []
      
      console.log(`✅ Loaded ${clusters.value.length} clusters`)
      console.log('Own clusters:', ownClusters.value.length)
      console.log('Competitor clusters:', competitorClusters.value.length)
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch clusters'
      console.error('Error fetching clusters:', err)
    } finally {
      loading.value = false
    }
  }

  // Create new cluster
  const createCluster = async (clusterData) => {
    loading.value = true
    error.value = null
    
    try {
      console.log('📝 Creating cluster:', clusterData)
      const response = await clustersApi.create(clusterData)
      clusters.value.unshift(response.data)
      console.log('✅ Cluster created successfully')
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to create cluster'
      console.error('Error creating cluster:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // Update cluster
  const updateCluster = async (clusterId, updates) => {
    loading.value = true
    error.value = null
    
    try {
      console.log('📝 Updating cluster:', clusterId, updates)
      const response = await clustersApi.update(clusterId, updates)
      
      const index = clusters.value.findIndex(cluster => cluster.id === clusterId)
      if (index !== -1) {
        clusters.value[index] = response.data
      }
      
      console.log('✅ Cluster updated successfully')
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to update cluster'
      console.error('Error updating cluster:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // Delete cluster
  const deleteCluster = async (clusterId) => {
    loading.value = true
    error.value = null
    
    try {
      console.log('🗑️ Deleting cluster:', clusterId)
      await clustersApi.delete(clusterId)
      
      const index = clusters.value.findIndex(cluster => cluster.id === clusterId)
      if (index !== -1) {
        clusters.value.splice(index, 1)
      }
      
      console.log('✅ Cluster deleted successfully')
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to delete cluster'
      console.error('Error deleting cluster:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // Check if content matches cluster keywords
  const isContentMatchingCluster = (content, cluster) => {
    if (!cluster.keywords || cluster.keywords.length === 0) return false
    
    const textToSearch = (content.title + ' ' + content.content).toLowerCase()
    
    return cluster.keywords.some(keyword => 
      textToSearch.includes(keyword.toLowerCase())
    )
  }

  // Find matching clusters for content
  const getMatchingClusters = (content) => {
    return clusters.value.filter(cluster => 
      cluster.is_active !== false && isContentMatchingCluster(content, cluster)
    )
  }

  return {
    clusters,
    loading,
    error,
    ownClusters,
    competitorClusters,
    activeClusters,
    
    // Getters
    getClusterById,
    getClusterByName,
    getClustersByType,
    getClustersWithKeywords,
    getKeywordsByType,
    getMatchingClusters,
    isContentMatchingCluster,
    
    // Actions
    fetchClusters,
    createCluster,
    updateCluster,
    deleteCluster
  }
})