<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

    <!-- Search Section -->
    <div class="bg-white rounded-lg shadow p-6">
      <div class="text-center mb-8">
        <div class="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg class="w-10 h-10 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0118 0z"/>
          </svg>
        </div>
        <h2 class="text-2xl font-bold text-gray-900 mb-2">Start Your Research</h2>
        <p class="text-gray-600">Enter any topic, city, company, or question to begin comprehensive analysis</p>
      </div>

      <div class="max-w-2xl mx-auto">
        <div class="flex gap-3">
          <div class="flex-1 relative">
            <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0118 0z"/>
            </svg>
            <input
              type="text"
              v-model="queryInput"
              class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-lg"
              placeholder="Enter your research query (e.g., 'Artificial Intelligence', 'Climate Change')"
              @keypress.enter="startResearch"
            />
          </div>
          <button
            @click="startResearch"
            :disabled="loading"
            class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 text-lg font-medium transition-colors">
            <div v-if="loading" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            <svg v-else class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0118 0z"/>
            </svg>
            Analyze
          </button>
        </div>
      </div>
    </div>

    <!-- Error Banner -->
    <div v-if="errorMsg" class="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
      <svg class="w-5 h-5 text-red-500 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>
      <p class="text-sm text-red-700">{{ errorMsg }}</p>
    </div>

    <!-- Results Section -->
    <div v-if="showResults" class="bg-white rounded-lg shadow">

      <div class="border-b border-gray-200 p-6">
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center">
            <svg class="w-6 h-6 text-blue-600 mr-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
            </svg>
            <h3 class="text-xl font-semibold text-gray-900">Results for "{{ currentQuery }}"</h3>
            <span v-if="isFromCache" class="ml-3 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
              Cached
            </span>
          </div>
          <button @click="clearResults"
            class="inline-flex items-center px-3 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 transition-colors">
            <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>
            Clear
          </button>
        </div>

        <!-- Tabs -->
        <div class="border-b border-gray-200">
          <nav class="-mb-px flex space-x-8">
            <button v-for="tab in tabs" :key="tab.id"
              @click="activeTab = tab.id"
              class="py-2 px-1 border-b-2 font-medium text-sm whitespace-nowrap transition-colors"
              :class="activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'">
              {{ tab.name }}
            </button>
          </nav>
        </div>
      </div>

      <div class="p-6">

        <!-- Research Tab -->
        <div v-if="activeTab === 'research'">
          <div class="flex justify-between items-center mb-6">
            <h4 class="text-lg font-medium text-gray-900">Research Analysis</h4>
            <div class="flex gap-3">
              <button @click="regenerate"
                class="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 transition-colors">
                <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                </svg>
                Regenerate
              </button>
              <button @click="generatePosts"
                :disabled="postsGenerated || !researchData || generatingPosts"
                class="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 transition-colors">
                <div v-if="generatingPosts" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                <svg v-else class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/>
                </svg>
                {{ generatingPosts ? 'Generating...' : postsGenerated ? 'Posts Generated' : 'Generate Posts' }}
              </button>
            </div>
          </div>

          <div v-if="researchData" class="space-y-6">
            <!-- About -->
            <div v-if="researchData.about" class="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6 border border-blue-200">
              <div class="flex items-center mb-4">
                <div class="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
                  <svg class="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/>
                  </svg>
                </div>
                <h5 class="font-medium text-gray-900">About</h5>
                <div v-if="currentlyLoading === 'about'" class="ml-3 w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
              </div>
              <div class="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap">{{ researchData.about }}</div>
            </div>

            <!-- 2-column grid -->
            <div class="grid md:grid-cols-2 gap-6">
              <!-- History -->
              <div class="bg-green-50 rounded-lg p-6 border border-green-200">
                <div class="flex items-center mb-4">
                  <div class="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center mr-3">
                    <svg class="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                  </div>
                  <h5 class="font-medium text-gray-900">History</h5>
                  <div v-if="currentlyLoading === 'batch1'" class="ml-3 w-4 h-4 border-2 border-green-600 border-t-transparent rounded-full animate-spin"></div>
                </div>
                <div class="text-sm text-gray-700 whitespace-pre-wrap">
                  <span v-if="researchData.history">{{ researchData.history }}</span>
                  <span v-else-if="currentlyLoading === 'batch1'" class="text-gray-500 italic">Researching historical information...</span>
                  <span v-else class="text-gray-500 italic">Historical information will appear here</span>
                </div>
              </div>

              <!-- Current Affairs -->
              <div class="bg-purple-50 rounded-lg p-6 border border-purple-200">
                <div class="flex items-center mb-4">
                  <div class="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center mr-3">
                    <svg class="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 5c7.18 0 13 5.82 13 13M6 11a7 7 0 017 7M6 17a1 1 0 110-2 1 1 0 010 2z"/>
                    </svg>
                  </div>
                  <h5 class="font-medium text-gray-900">Current Affairs</h5>
                  <div v-if="currentlyLoading === 'batch1'" class="ml-3 w-4 h-4 border-2 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
                </div>
                <div class="text-sm text-gray-700 whitespace-pre-wrap">
                  <span v-if="researchData.current_affairs">{{ researchData.current_affairs }}</span>
                  <span v-else-if="currentlyLoading === 'batch1'" class="text-gray-500 italic">Researching current affairs...</span>
                  <span v-else class="text-gray-500 italic">Current affairs will appear here</span>
                </div>
              </div>

              <!-- Competitors -->
              <div class="bg-blue-50 rounded-lg p-6 border border-blue-200">
                <div class="flex items-center mb-4">
                  <div class="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
                    <svg class="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"/>
                    </svg>
                  </div>
                  <h5 class="font-medium text-gray-900">Competitors</h5>
                  <div v-if="currentlyLoading === 'batch2'" class="ml-3 w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                </div>
                <div class="text-sm text-gray-700 whitespace-pre-wrap">
                  <span v-if="researchData.competitors">{{ researchData.competitors }}</span>
                  <span v-else-if="currentlyLoading === 'batch2'" class="text-gray-500 italic">Analyzing competitors...</span>
                  <span v-else class="text-gray-500 italic">Competitor analysis will appear here</span>
                </div>
              </div>

              <!-- Challenges -->
              <div class="bg-orange-50 rounded-lg p-6 border border-orange-200">
                <div class="flex items-center mb-4">
                  <div class="w-8 h-8 bg-orange-100 rounded-lg flex items-center justify-center mr-3">
                    <svg class="w-5 h-5 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                    </svg>
                  </div>
                  <h5 class="font-medium text-gray-900">Challenges</h5>
                  <div v-if="currentlyLoading === 'batch2'" class="ml-3 w-4 h-4 border-2 border-orange-600 border-t-transparent rounded-full animate-spin"></div>
                </div>
                <div class="text-sm text-gray-700 whitespace-pre-wrap">
                  <span v-if="researchData.challenges">{{ researchData.challenges }}</span>
                  <span v-else-if="currentlyLoading === 'batch2'" class="text-gray-500 italic">Identifying challenges...</span>
                  <span v-else class="text-gray-500 italic">Challenges will appear here</span>
                </div>
              </div>

              <!-- Plus Points -->
              <div class="bg-emerald-50 rounded-lg p-6 border border-emerald-200">
                <div class="flex items-center mb-4">
                  <div class="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center mr-3">
                    <svg class="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                  </div>
                  <h5 class="font-medium text-gray-900">Plus Points</h5>
                  <div v-if="currentlyLoading === 'batch3'" class="ml-3 w-4 h-4 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin"></div>
                </div>
                <div class="text-sm text-gray-700 whitespace-pre-wrap">
                  <span v-if="researchData.plus_points">{{ researchData.plus_points }}</span>
                  <span v-else-if="currentlyLoading === 'batch3'" class="text-gray-500 italic">Identifying advantages...</span>
                  <span v-else class="text-gray-500 italic">Advantages will appear here</span>
                </div>
              </div>

              <!-- Negative Points -->
              <div class="bg-red-50 rounded-lg p-6 border border-red-200">
                <div class="flex items-center mb-4">
                  <div class="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center mr-3">
                    <svg class="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                  </div>
                  <h5 class="font-medium text-gray-900">Negative Points</h5>
                  <div v-if="currentlyLoading === 'batch3'" class="ml-3 w-4 h-4 border-2 border-red-600 border-t-transparent rounded-full animate-spin"></div>
                </div>
                <div class="text-sm text-gray-700 whitespace-pre-wrap">
                  <span v-if="researchData.negative_points">{{ researchData.negative_points }}</span>
                  <span v-else-if="currentlyLoading === 'batch3'" class="text-gray-500 italic">Identifying disadvantages...</span>
                  <span v-else class="text-gray-500 italic">Disadvantages will appear here</span>
                </div>
              </div>
            </div>
          </div>

          <div v-else-if="loading" class="text-center py-12">
            <div class="inline-flex items-center">
              <div class="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mr-3"></div>
              <span class="text-gray-600">Researching query...</span>
            </div>
          </div>

          <div v-else class="text-center py-12 text-gray-500">
            <svg class="w-12 h-12 mx-auto mb-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0118 0z"/>
            </svg>
            <p>Click Analyze to start research</p>
          </div>
        </div>

        <!-- Social Posts Tab -->
        <div v-if="activeTab === 'posts'">
          <div v-if="generatingPosts" class="text-center py-12">
            <div class="inline-flex items-center">
              <div class="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mr-3"></div>
              <span class="text-gray-600">Generating social media posts...</span>
            </div>
          </div>
          <div v-else-if="!postsData" class="text-center py-12 text-gray-500">
            <svg class="w-12 h-12 mx-auto mb-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <p>Generate posts from the Research tab first</p>
          </div>
          <div v-else class="grid gap-6">
            <div v-if="postsData.facebook_posts?.length" class="bg-blue-50 rounded-lg p-6 border border-blue-200">
              <h5 class="font-medium text-gray-900 mb-4">Facebook Posts</h5>
              <div v-for="post in postsData.facebook_posts" :key="post.content" class="bg-white rounded-lg p-4 mb-4 border">
                <p class="text-gray-700 mb-3">{{ post.content }}</p>
                <div class="flex justify-between items-center">
                  <span class="text-sm text-gray-500">{{ post.call_to_action }}</span>
                  <button @click="goToPostCreator(post.content)"
                    class="inline-flex items-center px-3 py-1 border border-transparent text-sm font-medium rounded text-white bg-blue-600 hover:bg-blue-700 transition-colors">
                    Post
                    <svg class="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
                    </svg>
                  </button>
                </div>
              </div>
            </div>
            <div v-if="postsData.twitter_posts?.length" class="bg-cyan-50 rounded-lg p-6 border border-cyan-200">
              <h5 class="font-medium text-gray-900 mb-4">Twitter/X Posts</h5>
              <div v-for="post in postsData.twitter_posts" :key="post.content" class="bg-white rounded-lg p-4 mb-4 border">
                <p class="text-gray-700 mb-3">{{ post.content }}</p>
                <div class="flex justify-end">
                  <button @click="goToPostCreator(post.content)"
                    class="inline-flex items-center px-3 py-1 border border-transparent text-sm font-medium rounded text-white bg-cyan-500 hover:bg-cyan-600 transition-colors">
                    Post
                    <svg class="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const queryInput = ref('')
const currentQuery = ref('')
const activeTab = ref('research')
const showResults = ref(false)
const loading = ref(false)
const isFromCache = ref(false)
const postsGenerated = ref(false)
const generatingPosts = ref(false)
const currentlyLoading = ref(null)

const researchData = ref(null)
const postsData = ref(null)
const errorMsg = ref('')

const tabs = [
  { id: 'research', name: 'Research' },
  { id: 'posts', name: 'Social Posts' },
]

const CACHE_PREFIX = 'smartradar_research_'
const CACHE_TTL = 60 * 60 * 1000

function getCached(query) {
  try {
    const raw = localStorage.getItem(CACHE_PREFIX + query.toLowerCase().trim())
    if (!raw) return null
    const { timestamp, data } = JSON.parse(raw)
    if (Date.now() - timestamp > CACHE_TTL) { localStorage.removeItem(CACHE_PREFIX + query.toLowerCase().trim()); return null }
    return data
  } catch { return null }
}

function setCache(query, data) {
  try {
    localStorage.setItem(CACHE_PREFIX + query.toLowerCase().trim(), JSON.stringify({ timestamp: Date.now(), data }))
  } catch { /* ignore quota errors */ }
}

function clearResults() {
  researchData.value = null
  postsData.value = null
  showResults.value = false
  postsGenerated.value = false
  if (currentQuery.value) localStorage.removeItem(CACHE_PREFIX + currentQuery.value.toLowerCase().trim())
}

async function startResearch() {
  const query = queryInput.value.trim()
  if (!query) return

  currentQuery.value = query
  showResults.value = true
  activeTab.value = 'research'

  const cached = getCached(query)
  if (cached?.about) {
    researchData.value = cached
    isFromCache.value = true
    return
  }

  loading.value = true
  isFromCache.value = false
  errorMsg.value = ''
  currentlyLoading.value = null
  researchData.value = { query, about: null, history: null, current_affairs: null, competitors: null, challenges: null, plus_points: null, negative_points: null }

  const post = (path, params) => {
    const body = new URLSearchParams(params)
    return fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    })
  }

  try {
    // Step 1: About
    currentlyLoading.value = 'about'
    const aboutRes = await post('/research/about', { query })
    if (aboutRes.ok) researchData.value.about = (await aboutRes.json()).about
    const understanding = researchData.value.about || ''

    // Step 2: history + current_affairs in parallel
    currentlyLoading.value = 'batch1'
    const [histRes, caRes] = await Promise.all([
      post('/research/history', { query, understanding }),
      post('/research/current-affairs', { query, understanding }),
    ])
    if (histRes.ok) researchData.value.history = (await histRes.json()).history
    if (caRes.ok) researchData.value.current_affairs = (await caRes.json()).current_affairs

    // Step 3: competitors + challenges in parallel
    currentlyLoading.value = 'batch2'
    const [compRes, chalRes] = await Promise.all([
      post('/research/competitors', { query, understanding }),
      post('/research/challenges', { query, understanding }),
    ])
    if (compRes.ok) researchData.value.competitors = (await compRes.json()).competitors
    if (chalRes.ok) researchData.value.challenges = (await chalRes.json()).challenges

    // Step 4: plus_points + negative_points in parallel
    currentlyLoading.value = 'batch3'
    const [ppRes, npRes] = await Promise.all([
      post('/research/plus-points', { query, understanding }),
      post('/research/negative-points', { query, understanding }),
    ])
    if (ppRes.ok) researchData.value.plus_points = (await ppRes.json()).plus_points
    if (npRes.ok) researchData.value.negative_points = (await npRes.json()).negative_points

    setCache(query, researchData.value)

  } catch (e) {
    console.error('Research error:', e)
    errorMsg.value = `Research failed: ${e.message}. Make sure the OmniPush backend is running on port 8001.`
  } finally {
    loading.value = false
    currentlyLoading.value = null
  }
}

async function regenerate() {
  localStorage.removeItem(CACHE_PREFIX + currentQuery.value.toLowerCase().trim())
  researchData.value = null
  postsData.value = null
  postsGenerated.value = false
  queryInput.value = currentQuery.value
  await startResearch()
}

async function generatePosts() {
  if (!currentQuery.value || !researchData.value) return
  generatingPosts.value = true
  try {
    const body = new URLSearchParams({
      city: currentQuery.value,
      openai_analysis: researchData.value?.about || '',
      perplexity_research: researchData.value?.current_affairs || '',
    })
    const res = await fetch('/generate-social-posts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    })
    if (res.ok) {
      postsData.value = await res.json()
      postsGenerated.value = true
      activeTab.value = 'posts'
    }
  } catch (e) {
    console.error('Generate posts error:', e)
  } finally {
    generatingPosts.value = false
  }
}

function goToPostCreator(content) {
  localStorage.setItem('postContent', content)
  router.push('/post-creator')
}
</script>

<style scoped>
.prose { max-width: none; }
</style>
