<template>
  <div>
    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold text-gray-900">Keyword Clusters</h1>
        <button @click="showCreateModal = true" class="btn-primary">
          Add New Cluster
        </button>
      </div>

      <!-- Clusters Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div 
          v-for="cluster in clusters" 
          :key="cluster.id"
          class="card p-6"
        >
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-medium text-gray-900">{{ cluster.name }}</h3>
            <span :class="clusterTypeClasses(cluster.cluster_type)">
              {{ cluster.cluster_type }}
            </span>
          </div>
          
          <div class="mb-4">
            <p class="text-sm text-gray-600 mb-2">Keywords:</p>
            <div class="flex flex-wrap gap-1">
              <span 
                v-for="keyword in cluster.keywords" 
                :key="keyword"
                class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800"
              >
                {{ keyword }}
              </span>
            </div>
          </div>
          
          <div class="flex items-center justify-between">
            <span :class="cluster.is_active ? 'text-green-600' : 'text-gray-400'">
              {{ cluster.is_active ? 'Active' : 'Inactive' }}
            </span>
            
            <div class="flex space-x-2">
              <button 
                @click="editCluster(cluster)"
                class="text-primary-600 hover:text-primary-700 text-sm"
              >
                Edit
              </button>
              <button 
                @click="deleteCluster(cluster.id)"
                class="text-red-600 hover:text-red-700 text-sm"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="clusters.length === 0" class="text-center py-12">
        <p class="text-gray-500 mb-4">No clusters configured yet</p>
        <button @click="showCreateModal = true" class="btn-primary">
          Create Your First Cluster
        </button>
      </div>
    </main>

    <!-- Create/Edit Modal -->
    <ClusterModal 
      v-if="showCreateModal || editingCluster"
      :cluster="editingCluster"
      @close="closeModal"
      @save="handleSave"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useClustersStore } from '@/stores/clusters'
import ClusterModal from '@/components/ClusterModal.vue'

const clustersStore = useClustersStore()

// Use store data
const clusters = computed(() => clustersStore.clusters)
const loading = computed(() => clustersStore.loading)

const showCreateModal = ref(false)
const editingCluster = ref(null)

const editCluster = (cluster) => {
  editingCluster.value = cluster
}

const deleteCluster = async (clusterId) => {
  if (confirm('Are you sure you want to delete this cluster?')) {
    try {
      await clustersStore.deleteCluster(clusterId)
    } catch (error) {
      console.error('Failed to delete cluster:', error)
    }
  }
}

const closeModal = () => {
  showCreateModal.value = false
  editingCluster.value = null
}

const handleSave = async () => {
  // Refresh clusters after save
  await clustersStore.refreshClusters()
  closeModal()
}

const clusterTypeClasses = (type) => {
  return type === 'own'
    ? 'px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full'
    : 'px-2 py-1 text-xs font-medium bg-orange-100 text-orange-800 rounded-full'
}

// Data is already loaded by MainLayout, no need to fetch again
</script>