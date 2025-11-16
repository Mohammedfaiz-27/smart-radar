/**
 * Threat Campaigns Store - Pinia store for managing threat campaign data
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useWebSocketStore } from './websocket'
import { useNotificationsStore } from './notifications'

// API base URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const useThreatCampaignsStore = defineStore('threatCampaigns', () => {
  // State
  const campaigns = ref([])
  const campaignStats = ref({
    total_campaigns: 0,
    active_campaigns: 0,
    critical_campaigns: 0,
    high_threat_campaigns: 0,
    campaigns_today: 0,
    average_velocity: 0.0
  })
  const selectedCampaign = ref(null)
  const campaignPosts = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const activeCampaigns = computed(() => 
    campaigns.value.filter(campaign => campaign.status === 'active')
  )

  const criticalCampaigns = computed(() => 
    campaigns.value.filter(campaign => campaign.threat_level === 'critical')
  )

  const highThreatCampaigns = computed(() => 
    campaigns.value.filter(campaign => campaign.threat_level === 'high')
  )

  const campaignsByStatus = computed(() => {
    const grouped = {}
    campaigns.value.forEach(campaign => {
      if (!grouped[campaign.status]) {
        grouped[campaign.status] = []
      }
      grouped[campaign.status].push(campaign)
    })
    return grouped
  })

  const campaignsByThreatLevel = computed(() => {
    const grouped = {}
    campaigns.value.forEach(campaign => {
      if (!grouped[campaign.threat_level]) {
        grouped[campaign.threat_level] = []
      }
      grouped[campaign.threat_level].push(campaign)
    })
    return grouped
  })

  // Actions
  async function fetchCampaigns(params = {}) {
    loading.value = true
    error.value = null
    
    try {
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value !== null && value !== undefined && value !== '') {
          queryParams.append(key, value)
        }
      })
      
      const url = `${API_BASE_URL}/api/v1/threat-campaigns/?${queryParams}`
      const response = await fetch(url)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch campaigns: ${response.statusText}`)
      }
      
      const data = await response.json()
      campaigns.value = data
      return data
    } catch (err) {
      error.value = err.message
      console.error('Error fetching campaigns:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchActiveCampaigns() {
    return await fetchCampaigns({ status: 'active' })
  }

  async function fetchCampaignStats() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/threat-campaigns/stats`)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch campaign stats: ${response.statusText}`)
      }
      
      const data = await response.json()
      campaignStats.value = data
      return data
    } catch (err) {
      error.value = err.message
      console.error('Error fetching campaign stats:', err)
      throw err
    }
  }

  async function fetchCampaignById(campaignId) {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/threat-campaigns/${campaignId}`)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch campaign: ${response.statusText}`)
      }
      
      const data = await response.json()
      selectedCampaign.value = data
      return data
    } catch (err) {
      error.value = err.message
      console.error('Error fetching campaign by ID:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchCampaignPosts(campaignId, params = {}) {
    loading.value = true
    error.value = null
    
    try {
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value !== null && value !== undefined) {
          queryParams.append(key, value)
        }
      })
      
      const url = `${API_BASE_URL}/api/v1/threat-campaigns/${campaignId}/posts?${queryParams}`
      const response = await fetch(url)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch campaign posts: ${response.statusText}`)
      }
      
      const data = await response.json()
      campaignPosts.value = data.posts
      return data
    } catch (err) {
      error.value = err.message
      console.error('Error fetching campaign posts:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function acknowledgeCampaign(campaignId, acknowledgedBy, notes = null) {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/threat-campaigns/${campaignId}/acknowledge`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          acknowledged_by: acknowledgedBy,
          notes: notes
        })
      })
      
      if (!response.ok) {
        throw new Error(`Failed to acknowledge campaign: ${response.statusText}`)
      }
      
      const data = await response.json()
      
      // Update campaign in local state
      const campaignIndex = campaigns.value.findIndex(c => c.id === campaignId)
      if (campaignIndex !== -1) {
        campaigns.value[campaignIndex].status = 'acknowledged'
        campaigns.value[campaignIndex].acknowledged_by = acknowledgedBy
        campaigns.value[campaignIndex].acknowledged_at = new Date().toISOString()
      }
      
      // Update selected campaign if it matches
      if (selectedCampaign.value && selectedCampaign.value.id === campaignId) {
        selectedCampaign.value.status = 'acknowledged'
        selectedCampaign.value.acknowledged_by = acknowledgedBy
        selectedCampaign.value.acknowledged_at = new Date().toISOString()
      }
      
      return data
    } catch (err) {
      error.value = err.message
      console.error('Error acknowledging campaign:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateCampaign(campaignId, updateData) {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/threat-campaigns/${campaignId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updateData)
      })
      
      if (!response.ok) {
        throw new Error(`Failed to update campaign: ${response.statusText}`)
      }
      
      const data = await response.json()
      
      // Update campaign in local state
      const campaignIndex = campaigns.value.findIndex(c => c.id === campaignId)
      if (campaignIndex !== -1) {
        campaigns.value[campaignIndex] = data
      }
      
      // Update selected campaign if it matches
      if (selectedCampaign.value && selectedCampaign.value.id === campaignId) {
        selectedCampaign.value = data
      }
      
      return data
    } catch (err) {
      error.value = err.message
      console.error('Error updating campaign:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function generateCampaignReport(campaignId) {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/threat-campaigns/${campaignId}/report`, {
        method: 'POST'
      })
      
      if (!response.ok) {
        throw new Error(`Failed to generate campaign report: ${response.statusText}`)
      }
      
      const data = await response.json()
      return data
    } catch (err) {
      error.value = err.message
      console.error('Error generating campaign report:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function triggerCampaignDetection() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/threat-campaigns/detect`, {
        method: 'POST'
      })
      
      if (!response.ok) {
        throw new Error(`Failed to trigger campaign detection: ${response.statusText}`)
      }
      
      const data = await response.json()
      return data
    } catch (err) {
      error.value = err.message
      console.error('Error triggering campaign detection:', err)
      throw err
    }
  }

  async function fetchCampaignTimeline(campaignId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/threat-campaigns/${campaignId}/timeline`)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch campaign timeline: ${response.statusText}`)
      }
      
      const data = await response.json()
      return data
    } catch (err) {
      error.value = err.message
      console.error('Error fetching campaign timeline:', err)
      throw err
    }
  }

  // WebSocket event handlers
  function handleCampaignDetected(data) {
    console.log('New campaign detected:', data)
    
    // Add to notifications
    const notificationsStore = useNotificationsStore()
    notificationsStore.addNotification({
      type: 'campaign_detected',
      title: 'New Threat Campaign Detected',
      message: data.message || 'A new threat campaign has been identified',
      data: data,
      timestamp: new Date().toISOString()
    })
    
    // Refresh campaigns list
    fetchActiveCampaigns()
    fetchCampaignStats()
  }

  function handleCampaignEscalation(data) {
    console.log('Campaign escalation:', data)
    
    // Add to notifications
    const notificationsStore = useNotificationsStore()
    notificationsStore.addNotification({
      type: 'campaign_escalation',
      title: 'Campaign Escalation Alert',
      message: data.message || 'A threat campaign is showing increased activity',
      data: data,
      timestamp: new Date().toISOString(),
      priority: 'high'
    })
    
    // Update campaign if it's in the list
    const campaignIndex = campaigns.value.findIndex(c => c.id === data.campaign_id)
    if (campaignIndex !== -1) {
      campaigns.value[campaignIndex].campaign_velocity = data.velocity
      campaigns.value[campaignIndex].last_updated_at = new Date().toISOString()
    }
    
    // Refresh stats
    fetchCampaignStats()
  }

  function handleCampaignUpdate(data) {
    console.log('Campaign update:', data)
    
    // Update campaign in local state
    const campaignIndex = campaigns.value.findIndex(c => c.id === data.campaign_id)
    if (campaignIndex !== -1) {
      // Merge update data
      campaigns.value[campaignIndex] = { ...campaigns.value[campaignIndex], ...data }
    }
  }

  function handleBatchEscalations(data) {
    console.log('Batch campaign escalations:', data)
    
    // Add to notifications
    const notificationsStore = useNotificationsStore()
    notificationsStore.addNotification({
      type: 'batch_campaign_escalations',
      title: 'Multiple Campaign Escalations',
      message: data.message || `${data.escalated_count} campaigns showing increased activity`,
      data: data,
      timestamp: new Date().toISOString(),
      priority: 'high'
    })
    
    // Refresh data
    fetchActiveCampaigns()
    fetchCampaignStats()
  }

  // Initialize WebSocket listeners
  function initializeWebSocketListeners() {
    const websocketStore = useWebSocketStore()
    
    websocketStore.onMessage('campaign_detected', handleCampaignDetected)
    websocketStore.onMessage('campaign_escalation', handleCampaignEscalation)
    websocketStore.onMessage('campaign_update', handleCampaignUpdate)
    websocketStore.onMessage('batch_campaign_escalations', handleBatchEscalations)
  }

  // Utility functions
  function clearError() {
    error.value = null
  }

  function clearSelectedCampaign() {
    selectedCampaign.value = null
    campaignPosts.value = []
  }

  function getCampaignById(campaignId) {
    return campaigns.value.find(campaign => campaign.id === campaignId)
  }

  function formatCampaignVelocity(velocity) {
    if (velocity < 1) {
      return `${(velocity * 60).toFixed(1)} posts/hour`
    }
    return `${velocity.toFixed(1)} posts/hour`
  }

  function getThreatLevelColor(threatLevel) {
    const colors = {
      low: 'green',
      medium: 'yellow',
      high: 'orange',
      critical: 'red'
    }
    return colors[threatLevel] || 'gray'
  }

  function getStatusColor(status) {
    const colors = {
      active: 'red',
      monitoring: 'yellow',
      acknowledged: 'blue',
      resolved: 'green'
    }
    return colors[status] || 'gray'
  }

  return {
    // State
    campaigns,
    campaignStats,
    selectedCampaign,
    campaignPosts,
    loading,
    error,
    
    // Getters
    activeCampaigns,
    criticalCampaigns,
    highThreatCampaigns,
    campaignsByStatus,
    campaignsByThreatLevel,
    
    // Actions
    fetchCampaigns,
    fetchActiveCampaigns,
    fetchCampaignStats,
    fetchCampaignById,
    fetchCampaignPosts,
    acknowledgeCampaign,
    updateCampaign,
    generateCampaignReport,
    triggerCampaignDetection,
    fetchCampaignTimeline,
    
    // WebSocket handlers
    initializeWebSocketListeners,
    
    // Utilities
    clearError,
    clearSelectedCampaign,
    getCampaignById,
    formatCampaignVelocity,
    getThreatLevelColor,
    getStatusColor
  }
})