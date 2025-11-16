<template>
  <div class="active-threat-campaigns">
    <!-- Header Section -->
    <div class="campaigns-header">
      <div class="header-content">
        <h2 class="section-title">Active Threat Campaigns</h2>
        <div class="header-actions">
          <button 
            @click="refreshCampaigns" 
            :disabled="loading"
            class="refresh-btn"
          >
            <span class="icon">🔄</span>
            {{ loading ? 'Refreshing...' : 'Refresh' }}
          </button>
          <button 
            @click="triggerDetection"
            :disabled="loading"
            class="detect-btn"
          >
            <span class="icon">🔍</span>
            Detect New
          </button>
        </div>
      </div>
      
      <!-- Campaign Stats -->
      <div class="campaign-stats">
        <div class="stat-card">
          <div class="stat-number">{{ campaignStats.active_campaigns }}</div>
          <div class="stat-label">Active</div>
        </div>
        <div class="stat-card critical">
          <div class="stat-number">{{ campaignStats.critical_campaigns }}</div>
          <div class="stat-label">Critical</div>
        </div>
        <div class="stat-card high">
          <div class="stat-number">{{ campaignStats.high_threat_campaigns }}</div>
          <div class="stat-label">High Threat</div>
        </div>
        <div class="stat-card">
          <div class="stat-number">{{ campaignStats.campaigns_today }}</div>
          <div class="stat-label">Today</div>
        </div>
        <div class="stat-card">
          <div class="stat-number">{{ formatVelocity(campaignStats.average_velocity) }}</div>
          <div class="stat-label">Avg Velocity</div>
        </div>
      </div>
    </div>

    <!-- Error Message -->
    <div v-if="error" class="error-message">
      <span class="error-icon">⚠️</span>
      {{ error }}
      <button @click="clearError" class="close-error">✕</button>
    </div>

    <!-- Loading State -->
    <div v-if="loading && !activeCampaigns.length" class="loading-state">
      <div class="spinner"></div>
      <p>Loading threat campaigns...</p>
    </div>

    <!-- No Campaigns State -->
    <div v-else-if="!loading && !activeCampaigns.length" class="no-campaigns">
      <div class="no-campaigns-icon">🛡️</div>
      <h3>No Active Threat Campaigns</h3>
      <p>All clear! No coordinated threat campaigns detected at this time.</p>
      <button @click="triggerDetection" class="detect-campaigns-btn">
        Run Detection
      </button>
    </div>

    <!-- Campaigns Grid -->
    <div v-else class="campaigns-grid">
      <div 
        v-for="campaign in sortedCampaigns" 
        :key="campaign.id"
        class="campaign-card"
        :class="getCampaignCardClass(campaign)"
        @click="selectCampaign(campaign)"
      >
        <!-- Campaign Header -->
        <div class="campaign-header">
          <div class="campaign-title">
            <h3>{{ campaign.name }}</h3>
            <div class="campaign-badges">
              <span 
                class="threat-badge" 
                :class="getThreatLevelClass(campaign.threat_level)"
              >
                {{ campaign.threat_level.toUpperCase() }}
              </span>
              <span 
                class="status-badge"
                :class="getStatusClass(campaign.status)"
              >
                {{ campaign.status.toUpperCase() }}
              </span>
            </div>
          </div>
          <div class="campaign-actions">
            <button 
              @click.stop="acknowledgeCampaign(campaign)"
              v-if="campaign.status === 'active'"
              class="action-btn acknowledge"
              title="Acknowledge Campaign"
            >
              ✓
            </button>
            <button 
              @click.stop="viewCampaignDetails(campaign)"
              class="action-btn details"
              title="View Details"
            >
              👁️
            </button>
          </div>
        </div>

        <!-- Campaign Info -->
        <div class="campaign-info">
          <p class="campaign-description">{{ campaign.description }}</p>
          
          <div class="campaign-metrics">
            <div class="metric">
              <span class="metric-label">Posts:</span>
              <span class="metric-value">{{ campaign.total_posts }}</span>
            </div>
            <div class="metric">
              <span class="metric-label">Velocity:</span>
              <span class="metric-value">{{ formatVelocity(campaign.campaign_velocity) }}</span>
            </div>
            <div class="metric">
              <span class="metric-label">Engagement:</span>
              <span class="metric-value">{{ formatNumber(campaign.total_engagement) }}</span>
            </div>
            <div class="metric">
              <span class="metric-label">Sentiment:</span>
              <span class="metric-value sentiment" :class="getSentimentClass(campaign.average_sentiment)">
                {{ formatSentiment(campaign.average_sentiment) }}
              </span>
            </div>
          </div>

          <!-- Keywords and Hashtags -->
          <div class="campaign-tags">
            <div v-if="campaign.keywords.length" class="tag-group">
              <span class="tag-label">Keywords:</span>
              <span 
                v-for="keyword in campaign.keywords.slice(0, 3)" 
                :key="keyword"
                class="tag keyword-tag"
              >
                {{ keyword }}
              </span>
              <span v-if="campaign.keywords.length > 3" class="tag more-tag">
                +{{ campaign.keywords.length - 3 }} more
              </span>
            </div>
            
            <div v-if="campaign.hashtags.length" class="tag-group">
              <span class="tag-label">Hashtags:</span>
              <span 
                v-for="hashtag in campaign.hashtags.slice(0, 3)" 
                :key="hashtag"
                class="tag hashtag-tag"
              >
                {{ hashtag }}
              </span>
              <span v-if="campaign.hashtags.length > 3" class="tag more-tag">
                +{{ campaign.hashtags.length - 3 }} more
              </span>
            </div>
          </div>

          <!-- Timeline -->
          <div class="campaign-timeline">
            <div class="timeline-item">
              <span class="timeline-label">Detected:</span>
              <span class="timeline-value">{{ formatRelativeTime(campaign.first_detected_at) }}</span>
            </div>
            <div class="timeline-item">
              <span class="timeline-label">Updated:</span>
              <span class="timeline-value">{{ formatRelativeTime(campaign.last_updated_at) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Campaign Detail Modal -->
    <div v-if="selectedCampaign" class="modal-overlay" @click="closeModal">
      <div class="campaign-modal" @click.stop>
        <div class="modal-header">
          <h2>{{ selectedCampaign.name }}</h2>
          <button @click="closeModal" class="close-modal">✕</button>
        </div>
        
        <div class="modal-content">
          <!-- Campaign Details -->
          <div class="campaign-details">
            <div class="detail-section">
              <h4>Campaign Information</h4>
              <div class="detail-grid">
                <div class="detail-item">
                  <span class="detail-label">Threat Level:</span>
                  <span class="detail-value">
                    <span class="threat-badge" :class="getThreatLevelClass(selectedCampaign.threat_level)">
                      {{ selectedCampaign.threat_level.toUpperCase() }}
                    </span>
                  </span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Status:</span>
                  <span class="detail-value">
                    <span class="status-badge" :class="getStatusClass(selectedCampaign.status)">
                      {{ selectedCampaign.status.toUpperCase() }}
                    </span>
                  </span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Total Posts:</span>
                  <span class="detail-value">{{ selectedCampaign.total_posts }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Campaign Velocity:</span>
                  <span class="detail-value">{{ formatVelocity(selectedCampaign.campaign_velocity) }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Total Engagement:</span>
                  <span class="detail-value">{{ formatNumber(selectedCampaign.total_engagement) }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Average Sentiment:</span>
                  <span class="detail-value sentiment" :class="getSentimentClass(selectedCampaign.average_sentiment)">
                    {{ formatSentiment(selectedCampaign.average_sentiment) }}
                  </span>
                </div>
              </div>
            </div>
            
            <!-- Keywords and Hashtags -->
            <div class="detail-section">
              <h4>Campaign Elements</h4>
              <div class="elements-grid">
                <div v-if="selectedCampaign.keywords.length" class="element-group">
                  <h5>Keywords</h5>
                  <div class="element-tags">
                    <span 
                      v-for="keyword in selectedCampaign.keywords" 
                      :key="keyword"
                      class="tag keyword-tag"
                    >
                      {{ keyword }}
                    </span>
                  </div>
                </div>
                
                <div v-if="selectedCampaign.hashtags.length" class="element-group">
                  <h5>Hashtags</h5>
                  <div class="element-tags">
                    <span 
                      v-for="hashtag in selectedCampaign.hashtags" 
                      :key="hashtag"
                      class="tag hashtag-tag"
                    >
                      {{ hashtag }}
                    </span>
                  </div>
                </div>
                
                <div v-if="selectedCampaign.participating_accounts.length" class="element-group">
                  <h5>Participating Accounts</h5>
                  <div class="element-tags">
                    <span 
                      v-for="account in selectedCampaign.participating_accounts.slice(0, 10)" 
                      :key="account"
                      class="tag account-tag"
                    >
                      @{{ account }}
                    </span>
                    <span v-if="selectedCampaign.participating_accounts.length > 10" class="tag more-tag">
                      +{{ selectedCampaign.participating_accounts.length - 10 }} more
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Modal Actions -->
          <div class="modal-actions">
            <button 
              @click="viewCampaignPosts(selectedCampaign)"
              class="action-btn primary"
            >
              View Posts
            </button>
            <button 
              @click="generateReport(selectedCampaign)"
              class="action-btn secondary"
            >
              Generate Report
            </button>
            <button 
              v-if="selectedCampaign.status === 'active'"
              @click="acknowledgeCampaign(selectedCampaign)"
              class="action-btn acknowledge"
            >
              Acknowledge Campaign
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useThreatCampaignsStore } from '../stores/threatCampaigns'

// Store
const threatCampaignsStore = useThreatCampaignsStore()

// Local state
const selectedCampaign = ref(null)
const refreshInterval = ref(null)

// Computed properties
const { 
  activeCampaigns, 
  campaignStats, 
  loading, 
  error,
  clearError,
  fetchActiveCampaigns,
  fetchCampaignStats,
  triggerCampaignDetection,
  acknowledgeCampaign: storeCampaignAcknowledge,
  initializeWebSocketListeners
} = threatCampaignsStore

const sortedCampaigns = computed(() => {
  return [...activeCampaigns.value].sort((a, b) => {
    // Sort by threat level first (critical, high, medium, low)
    const threatOrder = { critical: 4, high: 3, medium: 2, low: 1 }
    const threatDiff = threatOrder[b.threat_level] - threatOrder[a.threat_level]
    if (threatDiff !== 0) return threatDiff
    
    // Then by velocity (descending)
    const velocityDiff = b.campaign_velocity - a.campaign_velocity
    if (velocityDiff !== 0) return velocityDiff
    
    // Finally by last updated (most recent first)
    return new Date(b.last_updated_at) - new Date(a.last_updated_at)
  })
})

// Methods
async function refreshCampaigns() {
  try {
    await Promise.all([
      fetchActiveCampaigns(),
      fetchCampaignStats()
    ])
  } catch (err) {
    console.error('Error refreshing campaigns:', err)
  }
}

async function triggerDetection() {
  try {
    await triggerCampaignDetection()
    // Refresh after a short delay to allow processing
    setTimeout(() => {
      refreshCampaigns()
    }, 2000)
  } catch (err) {
    console.error('Error triggering detection:', err)
  }
}

function selectCampaign(campaign) {
  selectedCampaign.value = campaign
}

function closeModal() {
  selectedCampaign.value = null
}

async function acknowledgeCampaign(campaign) {
  try {
    await storeCampaignAcknowledge(campaign.id, 'Dashboard User')
    if (selectedCampaign.value && selectedCampaign.value.id === campaign.id) {
      selectedCampaign.value.status = 'acknowledged'
    }
    await refreshCampaigns()
  } catch (err) {
    console.error('Error acknowledging campaign:', err)
  }
}

function viewCampaignDetails(campaign) {
  selectedCampaign.value = campaign
}

function viewCampaignPosts(campaign) {
  // Emit event or navigate to posts view
  console.log('Viewing posts for campaign:', campaign.id)
  // This could navigate to a dedicated page or open another modal
}

async function generateReport(campaign) {
  try {
    const report = await threatCampaignsStore.generateCampaignReport(campaign.id)
    console.log('Generated report:', report)
    // Handle report display/download
  } catch (err) {
    console.error('Error generating report:', err)
  }
}

// Utility functions
function getCampaignCardClass(campaign) {
  return [
    'threat-' + campaign.threat_level,
    'status-' + campaign.status,
    {
      'high-velocity': campaign.campaign_velocity > 5,
      'escalated': campaign.campaign_velocity > 10
    }
  ]
}

function getThreatLevelClass(threatLevel) {
  return 'threat-' + threatLevel
}

function getStatusClass(status) {
  return 'status-' + status
}

function getSentimentClass(sentiment) {
  if (sentiment > 0.3) return 'positive'
  if (sentiment < -0.3) return 'negative'
  return 'neutral'
}

function formatVelocity(velocity) {
  if (velocity < 1) {
    return `${(velocity * 60).toFixed(1)}/hr`
  }
  return `${velocity.toFixed(1)}/hr`
}

function formatNumber(num) {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}

function formatSentiment(sentiment) {
  if (sentiment > 0.3) return 'Positive'
  if (sentiment < -0.3) return 'Negative'
  return 'Neutral'
}

function formatRelativeTime(timestamp) {
  const now = new Date()
  const time = new Date(timestamp)
  const diff = now - time
  
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  return `${days}d ago`
}

// Lifecycle
onMounted(async () => {
  // Initialize WebSocket listeners
  initializeWebSocketListeners()
  
  // Load initial data
  await refreshCampaigns()
  
  // Set up auto-refresh every 30 seconds
  refreshInterval.value = setInterval(refreshCampaigns, 30000)
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
})
</script>

<style scoped>
.active-threat-campaigns {
  padding: 1rem;
  background: #f8f9fa;
  min-height: 100vh;
}

.campaigns-header {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-title {
  margin: 0;
  color: #2c3e50;
  font-size: 1.5rem;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
}

.refresh-btn, .detect-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  color: #555;
  cursor: pointer;
  transition: all 0.2s;
}

.refresh-btn:hover, .detect-btn:hover {
  background: #f8f9fa;
  border-color: #007bff;
}

.detect-btn {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

.detect-btn:hover {
  background: #0056b3;
}

.campaign-stats {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.stat-card {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 1rem;
  text-align: center;
  min-width: 120px;
  border: 2px solid transparent;
}

.stat-card.critical {
  background: #fee;
  border-color: #dc3545;
}

.stat-card.high {
  background: #fff3cd;
  border-color: #ffc107;
}

.stat-number {
  font-size: 1.5rem;
  font-weight: bold;
  color: #2c3e50;
}

.stat-label {
  font-size: 0.875rem;
  color: #666;
  margin-top: 0.25rem;
}

.error-message {
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  color: #721c24;
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.close-error {
  margin-left: auto;
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  color: #721c24;
}

.loading-state {
  text-align: center;
  padding: 3rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.no-campaigns {
  text-align: center;
  padding: 3rem;
  background: white;
  border-radius: 8px;
  margin-top: 2rem;
}

.no-campaigns-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.detect-campaigns-btn {
  background: #007bff;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  margin-top: 1rem;
}

.campaigns-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 1.5rem;
}

.campaign-card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  border-left: 4px solid #ddd;
  cursor: pointer;
  transition: all 0.2s;
}

.campaign-card:hover {
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
  transform: translateY(-2px);
}

.campaign-card.threat-critical {
  border-left-color: #dc3545;
}

.campaign-card.threat-high {
  border-left-color: #fd7e14;
}

.campaign-card.threat-medium {
  border-left-color: #ffc107;
}

.campaign-card.threat-low {
  border-left-color: #28a745;
}

.campaign-card.high-velocity {
  box-shadow: 0 0 0 2px #ffc107;
}

.campaign-card.escalated {
  box-shadow: 0 0 0 2px #dc3545;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 2px #dc3545; }
  50% { box-shadow: 0 0 0 2px #dc3545, 0 0 0 6px rgba(220, 53, 69, 0.3); }
  100% { box-shadow: 0 0 0 2px #dc3545; }
}

.campaign-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.campaign-title h3 {
  margin: 0 0 0.5rem 0;
  color: #2c3e50;
  font-size: 1.125rem;
}

.campaign-badges {
  display: flex;
  gap: 0.5rem;
}

.threat-badge, .status-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: bold;
  text-transform: uppercase;
}

.threat-badge.threat-critical { background: #dc3545; color: white; }
.threat-badge.threat-high { background: #fd7e14; color: white; }
.threat-badge.threat-medium { background: #ffc107; color: #212529; }
.threat-badge.threat-low { background: #28a745; color: white; }

.status-badge.status-active { background: #dc3545; color: white; }
.status-badge.status-monitoring { background: #ffc107; color: #212529; }
.status-badge.status-acknowledged { background: #007bff; color: white; }
.status-badge.status-resolved { background: #28a745; color: white; }

.campaign-actions {
  display: flex;
  gap: 0.5rem;
}

.action-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.action-btn:hover {
  background: #f8f9fa;
}

.action-btn.acknowledge {
  border-color: #28a745;
  color: #28a745;
}

.action-btn.acknowledge:hover {
  background: #28a745;
  color: white;
}

.campaign-description {
  color: #666;
  margin-bottom: 1rem;
  line-height: 1.4;
}

.campaign-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.metric {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem;
  background: #f8f9fa;
  border-radius: 4px;
}

.metric-label {
  color: #666;
  font-size: 0.875rem;
}

.metric-value {
  font-weight: 600;
  color: #2c3e50;
}

.metric-value.sentiment.positive { color: #28a745; }
.metric-value.sentiment.negative { color: #dc3545; }
.metric-value.sentiment.neutral { color: #6c757d; }

.campaign-tags {
  margin-bottom: 1rem;
}

.tag-group {
  margin-bottom: 0.5rem;
}

.tag-label {
  font-size: 0.75rem;
  color: #666;
  margin-right: 0.5rem;
}

.tag {
  display: inline-block;
  padding: 0.125rem 0.375rem;
  margin: 0.125rem;
  border-radius: 12px;
  font-size: 0.75rem;
  background: #e9ecef;
  color: #495057;
}

.keyword-tag { background: #cfe2ff; color: #084298; }
.hashtag-tag { background: #d1ecf1; color: #0c5460; }
.account-tag { background: #f8d7da; color: #721c24; }
.more-tag { background: #f8f9fa; color: #6c757d; font-style: italic; }

.campaign-timeline {
  display: flex;
  justify-content: space-between;
  padding-top: 1rem;
  border-top: 1px solid #eee;
}

.timeline-item {
  font-size: 0.75rem;
  color: #666;
}

.timeline-label {
  font-weight: 600;
}

.timeline-value {
  color: #999;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.campaign-modal {
  background: white;
  border-radius: 8px;
  max-width: 800px;
  max-height: 90vh;
  overflow-y: auto;
  width: 90vw;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #eee;
}

.modal-header h2 {
  margin: 0;
  color: #2c3e50;
}

.close-modal {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #999;
}

.modal-content {
  padding: 1.5rem;
}

.detail-section {
  margin-bottom: 2rem;
}

.detail-section h4 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
  border-bottom: 2px solid #007bff;
  padding-bottom: 0.5rem;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 6px;
}

.detail-label {
  font-weight: 600;
  color: #495057;
}

.detail-value {
  color: #2c3e50;
}

.elements-grid {
  display: grid;
  gap: 1.5rem;
}

.element-group h5 {
  margin: 0 0 0.75rem 0;
  color: #495057;
  font-size: 1rem;
}

.element-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  padding-top: 1.5rem;
  border-top: 1px solid #eee;
}

.action-btn.primary {
  background: #007bff;
  color: white;
  border: 1px solid #007bff;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  cursor: pointer;
  width: auto;
  height: auto;
}

.action-btn.secondary {
  background: white;
  color: #007bff;
  border: 1px solid #007bff;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  cursor: pointer;
  width: auto;
  height: auto;
}

.action-btn.acknowledge {
  background: #28a745;
  color: white;
  border: 1px solid #28a745;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  cursor: pointer;
  width: auto;
  height: auto;
}

@media (max-width: 768px) {
  .campaigns-grid {
    grid-template-columns: 1fr;
  }
  
  .campaign-stats {
    justify-content: center;
  }
  
  .campaign-metrics {
    grid-template-columns: 1fr;
  }
  
  .modal-content {
    padding: 1rem;
  }
  
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>