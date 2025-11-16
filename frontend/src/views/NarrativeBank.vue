<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b">
      <div class="max-w-7xl mx-auto px-6 py-6">
        <!-- Back Button -->
        <div class="mb-4">
          <router-link 
            to="/" 
            class="inline-flex items-center text-gray-600 hover:text-gray-900 transition-colors"
          >
            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
            </svg>
            Back to Dashboard
          </router-link>
        </div>
        
        <div class="flex justify-between items-start">
          <div>
            <h1 class="text-3xl font-bold text-gray-900">Narrative Bank</h1>
            <p class="text-gray-600 mt-1">Ready-to-use DMK narratives for content creation and crisis response</p>
          </div>
          <button class="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg font-medium flex items-center">
            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
            </svg>
            Add Narrative
          </button>
        </div>
      </div>
    </header>

    <!-- Filters -->
    <div class="max-w-7xl mx-auto px-6 py-6">
      <div class="bg-white rounded-lg shadow-sm border p-4 mb-6">
        <div class="flex flex-wrap gap-4 items-center">
          <!-- Search -->
          <div class="flex-1 min-w-64">
            <div class="relative">
              <svg class="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
              </svg>
              <input 
                v-model="searchQuery" 
                type="text" 
                placeholder="Search narratives..." 
                class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
            </div>
          </div>

          <!-- Category Filter -->
          <div class="flex items-center gap-2">
            <label class="text-sm font-medium text-gray-700">Category:</label>
            <select 
              v-model="selectedCategory" 
              class="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Categories</option>
              <option value="policy">Policy Achievement</option>
              <option value="crisis">Crisis Response</option>
              <option value="leader">Leader Quote</option>
              <option value="historical">Historical Win</option>
            </select>
          </div>

          <!-- Priority Filter -->
          <div class="flex items-center gap-2">
            <label class="text-sm font-medium text-gray-700">Priority:</label>
            <select 
              v-model="selectedPriority" 
              class="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Priorities</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          <!-- Usage Filter -->
          <div class="flex items-center gap-2">
            <label class="text-sm font-medium text-gray-700">Usage:</label>
            <select 
              v-model="selectedUsage" 
              class="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Most Used</option>
              <option value="recent">Recently Used</option>
              <option value="popular">Most Popular</option>
              <option value="unused">Unused</option>
            </select>
          </div>

          <!-- Clear Filters -->
          <button 
            @click="clearFilters"
            class="text-blue-600 hover:text-blue-800 font-medium text-sm flex items-center"
          >
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707v4.586a1 1 0 01-1.447.894l-4-2A1 1 0 018 15.586V11.414a1 1 0 00-.293-.707L1.293 4.293A1 1 0 011 3.586V2a1 1 0 011-1z"/>
            </svg>
            Clear Filters
          </button>
        </div>
      </div>

      <!-- Narratives Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <div 
          v-for="narrative in displayedNarratives" 
          :key="narrative.id"
          class="bg-white rounded-lg shadow-sm border overflow-hidden hover:shadow-md transition-shadow"
          :class="getBorderClass(narrative.priority)"
        >
          <!-- Card Header -->
          <div class="p-4 pb-3">
            <div class="flex items-start justify-between mb-3">
              <div class="flex items-center">
                <div class="p-2 rounded-lg mr-3" :class="getIconBgClass(narrative.category)">
                  <component :is="getIcon(narrative.category)" class="w-5 h-5" :class="getIconColorClass(narrative.category)" />
                </div>
                <div>
                  <h3 class="font-semibold text-gray-900 text-base">{{ narrative.title }}</h3>
                  <p class="text-sm text-gray-600 capitalize">{{ narrative.category }}</p>
                </div>
              </div>
              <span 
                class="px-2 py-1 text-xs font-medium rounded uppercase"
                :class="getPriorityClass(narrative.priority)"
              >
                {{ narrative.priority }}
              </span>
            </div>

            <!-- Description -->
            <p class="text-sm text-gray-700 leading-relaxed mb-4">
              {{ narrative.description }}
            </p>

            <!-- Hashtags -->
            <div class="flex flex-wrap gap-1 mb-4">
              <span 
                v-for="tag in narrative.tags" 
                :key="tag"
                class="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded font-medium"
              >
                {{ tag }}
              </span>
            </div>
          </div>

          <!-- Card Footer -->
          <div class="px-4 pb-4">
            <div class="flex items-center justify-between text-sm text-gray-600 mb-3">
              <span>Used {{ narrative.usageCount }} times</span>
              <span>Last used: {{ narrative.lastUsed }}</span>
            </div>
            <div class="flex items-center justify-between">
              <button class="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded font-medium text-sm flex items-center">
                <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z"/>
                </svg>
                Use Now
              </button>
              <div class="flex items-center space-x-2">
                <button class="p-2 text-gray-400 hover:text-gray-600">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                  </svg>
                </button>
                <button class="p-2 text-gray-400 hover:text-gray-600">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Load More Button -->
      <div class="text-center">
        <button 
          v-if="hasMore"
          @click="loadMore"
          class="bg-white border border-gray-300 text-gray-700 px-6 py-3 rounded-lg font-medium hover:bg-gray-50 transition-colors"
        >
          <svg class="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
          </svg>
          Load More Narratives
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { 
  TruckIcon, 
  ChatBubbleLeftRightIcon, 
  AcademicCapIcon, 
  TrophyIcon,
  ShieldCheckIcon,
  HeartIcon 
} from '@heroicons/vue/24/outline'

// Reactive data
const searchQuery = ref('')
const selectedCategory = ref('')
const selectedPriority = ref('')
const selectedUsage = ref('')
const displayLimit = ref(6)

// Sample narrative data matching your images
const narratives = ref([
  {
    id: 1,
    title: 'Free Bus Scheme Success',
    category: 'policy',
    priority: 'high',
    description: "DMK's revolutionary free bus scheme has empowered women across Tamil Nadu, providing economic freedom and mobility. Over 2 crore women have benefited, saving families thousands...",
    tags: ['#WomenEmpowerment', '#FreeTransport', '#SocialWelfare'],
    usageCount: 47,
    lastUsed: '2 days ago'
  },
  {
    id: 2,
    title: "Stalin's Vision Quote",
    category: 'leader',
    priority: 'medium',
    description: '"Tamil Nadu will lead India in development, education, and social justice. Our Dravidian model shows the path forward for inclusive growth that leaves no one behind."',
    tags: ['#DravidianModel', '#Development', '#Leadership'],
    usageCount: 23,
    lastUsed: '1 week ago'
  },
  {
    id: 3,
    title: '2021 Election Victory',
    category: 'historical',
    priority: 'high',
    description: "DMK's historic victory in 2021 with 133 seats proved Tamil Nadu's faith in Dravidian principles. The people chose development over divisive politics, social justice over communalism.",
    tags: ['#Victory2021', '#Democracy', '#Mandate'],
    usageCount: 89,
    lastUsed: '3 days ago'
  },
  {
    id: 4,
    title: 'Corruption Allegations Response',
    category: 'crisis',
    priority: 'high',
    description: "DMK's commitment to transparency is unmatched. Every allegation is investigated thoroughly. Our track record of clean governance and accountability speaks louder than opposition's...",
    tags: ['#Transparency', '#CleanGovernance', '#Accountability'],
    usageCount: 156,
    lastUsed: '5 hours ago'
  },
  {
    id: 5,
    title: 'Education Revolution',
    category: 'policy',
    priority: 'medium',
    description: "DMK's education reforms have transformed Tamil Nadu's academic landscape. From free laptops to breakfast schemes, we've ensured no child is left behind in their educational journey.",
    tags: ['#Education', '#StudentWelfare', '#DigitalLiteracy'],
    usageCount: 34,
    lastUsed: '4 days ago'
  },
  {
    id: 6,
    title: 'Universal Healthcare',
    category: 'policy',
    priority: 'high',
    description: "DMK's healthcare initiatives have made quality medical care accessible to all. From free medicines to advanced treatments, we've built a healthcare system that serves every Tamil.",
    tags: ['#Healthcare', '#UniversalCare', '#PublicHealth'],
    usageCount: 67,
    lastUsed: '1 day ago'
  }
])

// Computed properties
const filteredNarratives = computed(() => {
  let filtered = narratives.value

  if (searchQuery.value) {
    filtered = filtered.filter(n => 
      n.title.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      n.description.toLowerCase().includes(searchQuery.value.toLowerCase())
    )
  }

  if (selectedCategory.value) {
    filtered = filtered.filter(n => n.category === selectedCategory.value)
  }

  if (selectedPriority.value) {
    filtered = filtered.filter(n => n.priority === selectedPriority.value)
  }

  return filtered
})

const displayedNarratives = computed(() => {
  return filteredNarratives.value.slice(0, displayLimit.value)
})

const hasMore = computed(() => {
  return displayLimit.value < filteredNarratives.value.length
})

// Methods
const clearFilters = () => {
  searchQuery.value = ''
  selectedCategory.value = ''
  selectedPriority.value = ''
  selectedUsage.value = ''
}

const loadMore = () => {
  displayLimit.value += 6
}

const getBorderClass = (priority) => {
  const classes = {
    high: 'border-l-4 border-l-green-500',
    medium: 'border-l-4 border-l-yellow-500', 
    low: 'border-l-4 border-l-red-500'
  }
  return classes[priority] || 'border-l-4 border-l-gray-300'
}

const getPriorityClass = (priority) => {
  const classes = {
    high: 'bg-green-100 text-green-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-red-100 text-red-800'
  }
  return classes[priority] || 'bg-gray-100 text-gray-800'
}

const getIcon = (category) => {
  const icons = {
    policy: TruckIcon,
    leader: ChatBubbleLeftRightIcon,
    historical: TrophyIcon,
    crisis: ShieldCheckIcon,
    education: AcademicCapIcon,
    healthcare: HeartIcon
  }
  return icons[category] || TruckIcon
}

const getIconBgClass = (category) => {
  const classes = {
    policy: 'bg-green-100',
    leader: 'bg-blue-100', 
    historical: 'bg-yellow-100',
    crisis: 'bg-red-100',
    education: 'bg-purple-100',
    healthcare: 'bg-teal-100'
  }
  return classes[category] || 'bg-gray-100'
}

const getIconColorClass = (category) => {
  const classes = {
    policy: 'text-green-600',
    leader: 'text-blue-600',
    historical: 'text-yellow-600', 
    crisis: 'text-red-600',
    education: 'text-purple-600',
    healthcare: 'text-teal-600'
  }
  return classes[category] || 'text-gray-600'
}

onMounted(() => {
  // Component mounted
})
</script>