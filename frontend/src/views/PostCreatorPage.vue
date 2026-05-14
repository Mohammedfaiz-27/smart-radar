<template>
  <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

    <!-- Header -->
    <div class="bg-white rounded-lg shadow p-6">
      <div class="text-center mb-8">
        <div class="w-20 h-20 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg class="w-10 h-10 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
          </svg>
        </div>
        <h2 class="text-2xl font-bold text-gray-900 mb-2">Create Content</h2>
        <p class="text-gray-600">Craft engaging posts for social media</p>

        <!-- Post Mode Indicator -->
        <div v-if="canPublish" class="mt-4 inline-flex items-center px-3 py-1 rounded-full text-xs font-medium"
          :class="postModeBadgeClass">
          <span>{{ postModeLabel }}</span>
        </div>
      </div>

      <form @submit.prevent class="space-y-8">

        <!-- News Item Source Banner -->
        <div v-if="newsItemSource" class="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div class="flex items-start">
            <svg class="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
            </svg>
            <div class="ml-3 flex-1">
              <h3 class="text-sm font-medium text-blue-800">Content from News Item</h3>
              <p class="mt-1 text-sm text-blue-700"><strong>{{ newsItemSource.title }}</strong></p>
            </div>
            <button @click="newsItemSource = null" class="text-blue-400 hover:text-blue-600 ml-2">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- Content Textarea -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            <svg class="w-4 h-4 inline mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/>
            </svg>
            Your Content
          </label>
          <div class="space-y-3">
            <div class="relative">
              <textarea
                v-model="contentInput"
                rows="6"
                placeholder="Write your content here... Tell a story, share insights, or announce something exciting!"
                class="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-purple-500 resize-none text-base transition-colors"
                :class="{
                  'border-gray-300 focus:border-purple-500': !contentInput.trim(),
                  'border-green-300 bg-green-50': contentInput.trim() && contentInput.length <= 280,
                  'border-yellow-300 bg-yellow-50': contentInput.length > 280 && contentInput.length <= 500,
                  'border-red-300 bg-red-50': contentInput.length > 500
                }"
              ></textarea>
              <div v-if="contentInput.length > 0" class="absolute top-2 right-2">
                <div class="flex items-center px-2 py-1 rounded-full text-xs font-medium"
                  :class="contentInput.length <= 280 ? 'bg-green-100 text-green-800' : contentInput.length <= 500 ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'">
                  {{ contentInput.length }} chars
                </div>
              </div>
            </div>

            <!-- Toolbar -->
            <div class="flex items-center justify-between flex-wrap gap-2">
              <div class="flex gap-2 flex-wrap">
                <button type="button" @click="contentInput = ''"
                  :disabled="!contentInput.trim()"
                  class="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
                  <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                  </svg>
                  Clear
                </button>
                <button type="button" @click="insertEmoji"
                  class="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 transition-colors">
                  <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                  Emoji
                </button>
                <button type="button" @click="showTemplates = !showTemplates"
                  class="inline-flex items-center px-3 py-2 border border-indigo-300 text-sm font-medium rounded-md text-indigo-700 bg-indigo-50 hover:bg-indigo-100 transition-colors">
                  <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                  </svg>
                  Templates
                </button>
                <button type="button" @click="enhanceWithAI"
                  :disabled="!contentInput.trim() || aiLoading"
                  class="inline-flex items-center px-3 py-2 border border-yellow-300 text-sm font-medium rounded-md text-yellow-700 bg-yellow-50 hover:bg-yellow-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
                  <svg v-if="aiLoading" class="w-4 h-4 mr-1 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                  </svg>
                  <svg v-else class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/>
                  </svg>
                  {{ aiLoading ? 'Enhancing...' : 'AI Enhance' }}
                </button>
              </div>
              <div class="text-xs text-gray-500">
                <span :class="contentInput.length <= 280 ? 'text-green-600' : 'text-red-600'">Twitter: 280</span>
                <span class="mx-2" :class="contentInput.length <= 2200 ? 'text-green-600' : 'text-red-600'">LinkedIn: 2200</span>
              </div>
            </div>

            <!-- Templates Panel -->
            <div v-if="showTemplates" class="mt-2 p-4 bg-gray-50 rounded-lg border">
              <h4 class="text-sm font-medium text-gray-900 mb-3">Quick Templates</h4>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                <button v-for="tpl in contentTemplates" :key="tpl.name" type="button"
                  @click="applyTemplate(tpl)"
                  class="text-left p-3 rounded-md border border-gray-200 bg-white hover:border-purple-300 transition-colors">
                  <div class="font-medium text-sm text-gray-900">{{ tpl.name }}</div>
                  <div class="text-xs text-gray-500 mt-1">{{ tpl.preview }}</div>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Channel Group Selection -->
        <div class="border rounded-lg p-4"
          :class="selectedGroupIds.length > 0 ? 'bg-green-50 border-green-200' : 'bg-blue-50 border-blue-200'">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-lg font-medium text-blue-900">Publishing Destination</h3>
            <div class="flex items-center gap-2">
              <span v-if="selectedGroupIds.length > 0" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                {{ selectedGroupIds.length }} group(s)
              </span>
              <button @click="openCreateGroupModal"
                class="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md bg-purple-600 text-white hover:bg-purple-700 transition-colors">
                <svg class="w-3.5 h-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                </svg>
                New Group
              </button>
            </div>
          </div>

          <label class="block text-sm font-medium text-blue-800 mb-2">Select Channel Groups *</label>

          <div v-if="loadingChannels" class="text-center py-4">
            <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p class="mt-2 text-sm text-gray-500">Loading channel groups...</p>
          </div>
          <div v-else-if="channelError" class="text-center py-4 text-red-600 text-sm bg-red-50 rounded-lg border border-red-200 p-3">
            {{ channelError }}
            <button @click="loadChannelGroups" class="ml-2 underline hover:no-underline">Retry</button>
          </div>
          <div v-else-if="channelGroups.length === 0" class="text-center py-8 bg-gray-50 rounded-lg border border-gray-200">
            <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"/>
            </svg>
            <p class="mt-2 text-sm text-gray-600">No channel groups available</p>
            <p class="mt-1 text-xs text-gray-500">Create a group from your connected accounts to publish</p>
            <button @click="createDefaultGroup" :disabled="creatingDefaultGroup"
              class="mt-4 inline-flex items-center px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors">
              <div v-if="creatingDefaultGroup" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
              <svg v-else class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
              </svg>
              {{ creatingDefaultGroup ? 'Creating...' : 'Create Default Group' }}
            </button>
          </div>
          <div v-else class="space-y-2 max-h-60 overflow-y-auto border border-blue-200 rounded-md p-3">
            <label v-for="group in channelGroups" :key="group.id"
              class="flex items-start p-3 rounded-lg border border-gray-200 hover:bg-blue-50 cursor-pointer transition-colors"
              :class="{ 'bg-blue-50 border-blue-300': selectedGroupIds.includes(group.id) }">
              <input type="checkbox" :value="group.id" v-model="selectedGroupIds"
                class="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"/>
              <div class="ml-3 flex-1">
                <div class="font-medium text-gray-900">{{ group.name }}</div>
                <div class="text-sm text-gray-500">{{ group.social_account_ids?.length || 0 }} account(s)</div>
              </div>
            </label>
          </div>

          <div v-if="selectedGroupIds.length > 0" class="mt-3 bg-white rounded p-3 border border-blue-200">
            <div class="flex flex-wrap gap-1">
              <span v-for="gid in selectedGroupIds" :key="gid"
                class="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800">
                {{ getGroupName(gid) }}
              </span>
            </div>
          </div>
        </div>

        <!-- News Card Template Selector -->
        <div class="border rounded-lg p-4 bg-amber-50 border-amber-200">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-lg font-medium text-amber-900">
              News Card Template
              <span class="text-sm font-normal text-amber-600 ml-1">(optional)</span>
            </h3>
            <span v-if="selectedTemplate" class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              Selected
            </span>
          </div>

          <!-- Selected template chip -->
          <div v-if="selectedTemplate" class="flex items-center justify-between bg-white border border-amber-300 rounded-lg px-4 py-3 mb-3">
            <div class="flex items-center gap-2">
              <svg class="w-5 h-5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              <div>
                <div class="text-sm font-semibold text-gray-900">{{ selectedTemplate.template_display_name || selectedTemplate.name }}</div>
                <div v-if="selectedTemplate.description" class="text-xs text-gray-500">{{ selectedTemplate.description }}</div>
              </div>
            </div>
            <button @click="selectedTemplate = null" class="text-gray-400 hover:text-red-500 transition-colors ml-3">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <!-- Pick button -->
          <button type="button" @click="openTemplatePicker"
            class="w-full flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-amber-300 rounded-lg text-amber-700 hover:bg-amber-100 hover:border-amber-400 transition-colors text-sm font-medium">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/>
            </svg>
            {{ selectedTemplate ? 'Change Template' : 'Choose a News Card Template' }}
          </button>
        </div>

        <!-- Media Upload -->
        <div class="border rounded-lg p-4 bg-green-50 border-green-200">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-lg font-medium text-green-900">
              Media
              <span v-if="selectedImages.length > 0" class="text-sm font-normal ml-2 text-green-700">({{ selectedImages.length }} image(s))</span>
            </h3>
            <span v-if="selectedImages.length > 0" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
              {{ selectedImages.length }} selected
            </span>
          </div>

          <!-- Drop Zone -->
          <div class="border-2 border-dashed rounded-lg p-6 text-center transition-colors"
            :class="isDragging ? 'border-green-500 bg-green-100' : 'border-green-300 hover:border-green-400'"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop">
            <input ref="fileInput" type="file" multiple accept="image/*,video/*" @change="handleFileInput" class="hidden"/>

            <div v-if="uploadProgress.length === 0">
              <div class="flex justify-center space-x-4 mb-3">
                <svg class="h-12 w-12 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                </svg>
              </div>
              <div class="flex flex-wrap justify-center gap-4 mb-2">
                <button type="button" @click="fileInput?.click()"
                  class="inline-flex items-center px-4 py-2 text-green-600 font-medium border border-green-300 rounded-lg hover:bg-green-50 transition-colors">
                  <svg class="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
                  </svg>
                  Upload images / videos
                </button>
                <button type="button" @click="searchImageQuery = contentInput.trim().slice(0, 50); showImageSearch = true"
                  class="inline-flex items-center px-4 py-2 text-purple-600 font-medium border border-purple-300 rounded-lg hover:bg-purple-50 transition-colors">
                  <svg class="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0118 0z"/>
                  </svg>
                  Search images
                </button>
              </div>
              <p class="text-sm text-gray-500">or drag and drop · PNG, JPG, GIF, MP4 up to 100MB · Max 4 files</p>
            </div>

            <!-- Upload Progress -->
            <div v-if="uploadProgress.length > 0" class="space-y-2">
              <div v-for="(p, i) in uploadProgress" :key="i" class="text-left">
                <div class="flex items-center justify-between mb-1">
                  <span class="text-sm font-medium text-gray-700">{{ p.name }}</span>
                  <span class="text-sm text-gray-500">{{ p.percent }}%</span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2">
                  <div class="bg-green-600 h-2 rounded-full transition-all" :style="{ width: p.percent + '%' }"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Selected Images Grid -->
          <div v-if="selectedImages.length > 0" class="mt-3">
            <h4 class="text-sm font-medium text-gray-700 mb-2">Selected Images ({{ selectedImages.length }})</h4>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <div v-for="(img, i) in selectedImages" :key="i" class="relative group">
                <img :src="img.preview" :alt="img.name" class="w-full h-20 object-cover rounded-lg"/>
                <button type="button" @click="removeImage(i)"
                  class="absolute top-1 right-1 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                  <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Image Search Modal -->
        <div v-if="showImageSearch" class="fixed inset-0 z-50 overflow-y-auto">
          <div class="flex items-center justify-center min-h-screen p-4">
            <div class="fixed inset-0 bg-gray-500 bg-opacity-75" @click="showImageSearch = false"></div>
            <div class="relative bg-white rounded-lg shadow-xl w-full max-w-2xl">
              <div class="p-6">
                <div class="flex items-center justify-between mb-4">
                  <h3 class="text-lg font-medium text-gray-900">Search Images</h3>
                  <button @click="showImageSearch = false" class="text-gray-400 hover:text-gray-600">
                    <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                  </button>
                </div>
                <div class="flex gap-2 mb-4">
                  <input v-model="searchImageQuery" type="text" placeholder="Search for images..."
                    class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                    @keypress.enter="searchImages"/>
                  <button @click="searchImages" :disabled="searchingImages"
                    class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50">
                    {{ searchingImages ? 'Searching...' : 'Search' }}
                  </button>
                </div>
                <div v-if="imageSearchResults.length > 0" class="grid grid-cols-3 gap-3 max-h-80 overflow-y-auto">
                  <div v-for="(img, i) in imageSearchResults" :key="i"
                    class="cursor-pointer rounded-lg overflow-hidden border-2 hover:border-purple-400 transition-colors"
                    @click="selectSearchImage(img)">
                    <img :src="img.thumbnail" :alt="img.title" class="w-full h-24 object-cover"/>
                  </div>
                </div>
                <div v-else-if="searchingImages" class="text-center py-8">
                  <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
                </div>
                <div v-else class="text-center py-8 text-gray-500 text-sm">
                  Enter a search term and click Search
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex justify-center gap-4">
          <!-- Save Draft -->
          <button type="button" @click="saveDraft"
            :disabled="!contentInput.trim() || saving"
            class="flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-lg transition-all h-36 flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
            :class="contentInput.trim() ? 'border-gray-300 bg-gray-50 text-gray-700 hover:bg-gray-100 hover:scale-105' : 'border-gray-200 text-gray-400'">
            <svg class="w-10 h-10 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/>
            </svg>
            <span class="font-bold text-base">{{ saving ? 'Saving...' : 'Save Draft' }}</span>
            <small class="text-xs mt-1 opacity-75">Save for later</small>
          </button>

          <!-- Schedule -->
          <button type="button" @click="showScheduleModal = true"
            :disabled="!canPublish"
            class="flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-lg transition-all h-36 flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
            :class="canPublish ? 'border-blue-300 bg-blue-50 text-blue-700 hover:bg-blue-100 hover:scale-105' : 'border-gray-200 text-gray-400'">
            <svg class="w-10 h-10 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <span class="font-bold text-base">Schedule</span>
            <small class="text-xs mt-1 opacity-75">Choose date & time</small>
          </button>

          <!-- Publish Now -->
          <button type="button" @click="publishNow"
            :disabled="!canPublish || publishing"
            class="flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-lg transition-all h-36 flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
            :class="canPublish ? 'border-purple-300 bg-purple-50 text-purple-700 hover:bg-purple-100 hover:scale-105' : 'border-gray-200 text-gray-400'">
            <svg class="w-10 h-10 mb-2" :class="publishing && 'animate-bounce'" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
            </svg>
            <span class="font-bold text-base">{{ publishing ? 'Publishing...' : 'Publish Now' }}</span>
            <small class="text-xs mt-1 opacity-75">Post to all channels</small>
          </button>
        </div>

      </form>
    </div>

    <!-- Publish Results -->
    <div v-if="publishResults.length > 0" class="bg-white rounded-lg shadow border border-gray-200">
      <div class="px-6 py-4 border-b border-gray-200">
        <h3 class="text-base font-semibold text-gray-900">Publishing Results</h3>
      </div>
      <div class="p-6 space-y-3">
        <div v-for="r in publishResults" :key="r.platform"
          class="flex items-start p-4 rounded-lg border"
          :class="r.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'">
          <svg v-if="r.success" class="w-5 h-5 text-green-500 mr-3 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <svg v-else class="w-5 h-5 text-red-500 mr-3 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
          </svg>
          <div class="flex-1 min-w-0">
            <h4 class="text-sm font-medium capitalize" :class="r.success ? 'text-green-800' : 'text-red-800'">{{ r.platform }}</h4>
            <p class="text-sm" :class="r.success ? 'text-green-700' : 'text-red-700'">{{ r.message }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Template Picker Modal -->
    <div v-if="showTemplatePicker" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex min-h-screen items-center justify-center p-4">
        <div class="fixed inset-0 bg-black bg-opacity-40" @click="showTemplatePicker = false"></div>
        <div class="relative bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col">

          <!-- Header -->
          <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between flex-shrink-0">
            <div>
              <h3 class="text-lg font-semibold text-gray-900">Choose a Template</h3>
              <p class="text-sm text-gray-500 mt-0.5">Select a news card design template to use for this post</p>
            </div>
            <button @click="showTemplatePicker = false" class="text-gray-400 hover:text-gray-600 p-1 rounded">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <!-- Search bar -->
          <div class="px-6 py-3 border-b border-gray-100 flex-shrink-0">
            <input v-model="templateSearch" type="text" placeholder="Search templates…"
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"/>
          </div>

          <!-- Body -->
          <div class="overflow-y-auto flex-1 p-6">

            <!-- Loading -->
            <div v-if="loadingTemplates" class="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div v-for="i in 6" :key="i" class="bg-gray-100 rounded-xl p-4 animate-pulse h-24"></div>
            </div>

            <!-- Empty -->
            <div v-else-if="filteredPickerTemplates.length === 0" class="text-center py-12">
              <svg class="mx-auto h-10 w-10 text-gray-300 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              <p class="text-sm text-gray-500">No templates found</p>
            </div>

            <!-- Template grid -->
            <div v-else class="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <button v-for="tpl in filteredPickerTemplates" :key="tpl.id ?? tpl._id"
                type="button"
                @click="selectTemplate(tpl)"
                :class="[
                  'text-left p-4 rounded-xl border-2 transition-all hover:shadow-md',
                  selectedTemplate && (selectedTemplate.id ?? selectedTemplate._id) === (tpl.id ?? tpl._id)
                    ? 'border-amber-400 bg-amber-50 ring-1 ring-amber-400'
                    : 'border-gray-200 bg-white hover:border-amber-300'
                ]">
                <div class="w-8 h-8 bg-amber-100 rounded-lg flex items-center justify-center mb-2">
                  <svg class="w-4 h-4 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/>
                  </svg>
                </div>
                <div class="font-semibold text-sm text-gray-900 leading-tight">
                  {{ tpl.template_display_name || cleanTemplateName(tpl.template_name || tpl.name || '') }}
                </div>
                <div v-if="tpl.description" class="text-xs text-gray-400 mt-1 line-clamp-2">{{ tpl.description }}</div>
                <div class="mt-2 flex items-center justify-between">
                  <span :class="['text-xs font-medium px-1.5 py-0.5 rounded-full', tpl.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500']">
                    {{ tpl.is_active ? 'Active' : 'Inactive' }}
                  </span>
                  <svg v-if="selectedTemplate && (selectedTemplate.id ?? selectedTemplate._id) === (tpl.id ?? tpl._id)"
                    class="w-4 h-4 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
                  </svg>
                </div>
              </button>
            </div>
          </div>

          <!-- Footer -->
          <div class="px-6 py-4 border-t border-gray-100 flex items-center justify-between flex-shrink-0 bg-gray-50 rounded-b-xl">
            <button type="button" @click="selectedTemplate = null; showTemplatePicker = false"
              class="text-sm text-gray-500 hover:text-gray-700 transition-colors">
              Clear selection
            </button>
            <button type="button" @click="showTemplatePicker = false"
              class="px-5 py-2 bg-amber-500 hover:bg-amber-600 text-white text-sm font-medium rounded-lg transition-colors">
              Done
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Schedule Modal -->
    <div v-if="showScheduleModal" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-center justify-center min-h-screen p-4">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75" @click="showScheduleModal = false"></div>
        <div class="relative bg-white rounded-lg shadow-xl w-full max-w-lg">
          <div class="p-6">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-medium text-gray-900">Schedule Post</h3>
              <button @click="showScheduleModal = false" class="text-gray-400 hover:text-gray-600">
                <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>
            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Select Date</label>
                <input v-model="scheduleDate" type="date" :min="todayStr"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500"/>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Select Time</label>
                <input v-model="scheduleTime" type="time"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500"/>
              </div>
              <div class="bg-blue-50 p-4 rounded-lg">
                <p class="text-sm font-medium text-blue-800">Schedule your post</p>
                <p class="text-sm text-blue-600 mt-1">Your content will be published automatically at the selected time</p>
              </div>
            </div>
          </div>
          <div class="bg-gray-50 px-6 py-3 flex flex-row-reverse gap-2">
            <button @click="schedulePost" :disabled="!scheduleDate || !scheduleTime || scheduling"
              class="inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
              {{ scheduling ? 'Scheduling...' : 'Schedule Post' }}
            </button>
            <button @click="showScheduleModal = false"
              class="inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50">
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>

  </div>

  <!-- Create Channel Group Modal -->
  <div v-if="showCreateGroupModal" class="fixed inset-0 z-50 overflow-y-auto">
    <div class="flex min-h-screen items-center justify-center p-4">
      <div class="fixed inset-0 bg-black bg-opacity-40" @click="showCreateGroupModal = false"></div>
      <div class="relative bg-white rounded-xl shadow-2xl w-full max-w-lg">

        <!-- Modal Header -->
        <div class="flex items-center justify-between p-5 border-b">
          <div>
            <h3 class="text-lg font-semibold text-gray-900">Create Channel Group</h3>
            <p class="text-sm text-gray-500 mt-0.5">Name your group and pick which accounts to include</p>
          </div>
          <button @click="showCreateGroupModal = false" class="text-gray-400 hover:text-gray-600 p-1 rounded">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Modal Body -->
        <div class="p-5 space-y-4 max-h-[70vh] overflow-y-auto">

          <!-- Group Name -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Group Name *</label>
            <input v-model="newGroupName" type="text" placeholder="e.g. WhatsApp, Instagram, All Platforms..."
              class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"/>
          </div>

          <!-- Account Selection -->
          <div>
            <div class="flex items-center justify-between mb-2">
              <label class="block text-sm font-medium text-gray-700">Select Accounts *</label>
              <div class="flex gap-2 text-xs">
                <button @click="selectAllGroupAccounts" class="text-purple-600 hover:text-purple-800 underline">All</button>
                <button @click="newGroupAccountIds = []" class="text-gray-500 hover:text-gray-700 underline">None</button>
              </div>
            </div>

            <div v-if="loadingGroupAccounts" class="text-center py-6">
              <div class="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-purple-600"></div>
            </div>
            <div v-else-if="!groupAccountsByPlatform.length" class="text-center py-6 text-sm text-gray-500 bg-gray-50 rounded-lg">
              No connected accounts found. Connect accounts in Social Accounts page first.
            </div>
            <div v-else class="space-y-3">
              <div v-for="group in groupAccountsByPlatform" :key="group.platform">
                <!-- Platform header -->
                <div class="flex items-center gap-2 mb-1">
                  <span class="inline-flex items-center justify-center w-6 h-6 rounded-full text-white text-xs font-bold"
                    :style="{ backgroundColor: platformColor(group.platform) }">
                    {{ group.platform.charAt(0).toUpperCase() }}
                  </span>
                  <span class="text-sm font-semibold text-gray-700 capitalize">{{ group.platform }}</span>
                  <span class="text-xs text-gray-400">({{ group.accounts.length }})</span>
                  <button @click="togglePlatformAccounts(group.platform, group.accounts)"
                    class="ml-auto text-xs text-purple-600 hover:text-purple-800 underline">
                    {{ isPlatformFullySelected(group.accounts) ? 'Deselect' : 'Select all' }}
                  </button>
                </div>
                <!-- Accounts in platform -->
                <div class="space-y-1 pl-8">
                  <label v-for="acc in group.accounts" :key="acc.id"
                    class="flex items-center gap-3 p-2 rounded-lg border border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors"
                    :class="{ 'bg-purple-50 border-purple-200': newGroupAccountIds.includes(acc.id) }">
                    <input type="checkbox" :value="acc.id" v-model="newGroupAccountIds"
                      class="h-4 w-4 text-purple-600 rounded border-gray-300 focus:ring-purple-500"/>
                    <div class="flex-1 min-w-0">
                      <p class="text-sm font-medium text-gray-900 truncate">{{ acc.account_name }}</p>
                      <p class="text-xs text-gray-400 truncate">{{ acc.account_id }}</p>
                    </div>
                    <span class="text-xs px-1.5 py-0.5 rounded font-medium"
                      :class="acc.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'">
                      {{ acc.status }}
                    </span>
                  </label>
                </div>
              </div>
            </div>
          </div>

          <p v-if="createGroupError" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{{ createGroupError }}</p>
        </div>

        <!-- Modal Footer -->
        <div class="flex items-center justify-between px-5 py-4 border-t bg-gray-50 rounded-b-xl">
          <span class="text-xs text-gray-500">{{ newGroupAccountIds.length }} account(s) selected</span>
          <div class="flex gap-2">
            <button @click="showCreateGroupModal = false"
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
              Cancel
            </button>
            <button @click="submitCreateGroup" :disabled="!newGroupName.trim() || !newGroupAccountIds.length || creatingGroup"
              class="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors">
              <span v-if="creatingGroup" class="inline-flex items-center gap-1.5">
                <div class="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Creating...
              </span>
              <span v-else>Create Group</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  </div>

</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { smartPostApi } from '@/services/smartpost'
import { useSmartPostStore } from '@/stores/smartpost'

const store = useSmartPostStore()

const contentInput = ref('')
const newsItemSource = ref(null)
const showTemplates = ref(false)
const aiLoading = ref(false)
const channelError = ref('')
const apiError = ref('')

const loadingChannels = ref(false)
const channelGroups = ref([])
const selectedGroupIds = ref([])

// ── Template picker ───────────────────────────────────────────────
const showTemplatePicker  = ref(false)
const loadingTemplates    = ref(false)
const templates           = ref([])
const selectedTemplate    = ref(null)
const templateSearch      = ref('')

const filteredPickerTemplates = computed(() => {
  const q = templateSearch.value.toLowerCase()
  return templates.value.filter(t => {
    const name = (t.template_display_name || t.name || t.template_name || '').toLowerCase()
    return !q || name.includes(q)
  })
})

function cleanTemplateName(name = '') {
  return name.replace(/^(template_|news_card_|card_)/i, '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

async function openTemplatePicker() {
  showTemplatePicker.value = true
  templateSearch.value = ''
  if (templates.value.length === 0) {
    loadingTemplates.value = true
    try {
      const res = await smartPostApi.getTemplates()
      templates.value = res.data?.templates ?? res.data ?? []
    } catch (e) {
      // silently ignore — user sees empty state
    } finally {
      loadingTemplates.value = false
    }
  }
}

function selectTemplate(tpl) {
  selectedTemplate.value = tpl
  showTemplatePicker.value = false
}

const selectedImages = ref([])
const isDragging = ref(false)
const uploadProgress = ref([])
const fileInput = ref(null)

const showImageSearch = ref(false)
const searchImageQuery = ref('')
const searchingImages = ref(false)
const imageSearchResults = ref([])

const saving = ref(false)
const publishing = ref(false)
const scheduling = ref(false)
const creatingDefaultGroup = ref(false)
const publishResults = ref([])

// Create Group Modal
const showCreateGroupModal = ref(false)
const newGroupName = ref('')
const newGroupAccountIds = ref([])
const allGroupAccounts = ref([])
const loadingGroupAccounts = ref(false)
const creatingGroup = ref(false)
const createGroupError = ref('')

const showScheduleModal = ref(false)
const scheduleDate = ref('')
const scheduleTime = ref('')

const todayStr = new Date().toISOString().split('T')[0]

const contentTemplates = [
  { name: 'Announcement', preview: 'We are excited to announce...', text: 'We are excited to announce that [your news here]! Stay tuned for more updates.' },
  { name: 'Question', preview: 'What do you think about...', text: 'What do you think about [topic]? Share your thoughts in the comments below!' },
  { name: 'Tip', preview: 'Pro tip: Did you know...', text: 'Pro tip: Did you know that [tip]? This can help you [benefit]. Try it today!' },
  { name: 'Call to Action', preview: 'Join us and...', text: 'Join us and [action]. Together we can [goal]. Learn more at [link].' },
]

const canPublish = computed(() => contentInput.value.trim().length > 0 && selectedGroupIds.value.length > 0)

const postModeBadgeClass = computed(() => {
  if (selectedImages.value.length > 0 && contentInput.value.trim()) return 'bg-purple-100 text-purple-800'
  if (selectedImages.value.length > 0) return 'bg-blue-100 text-blue-800'
  return 'bg-green-100 text-green-800'
})

const postModeLabel = computed(() => {
  if (selectedImages.value.length > 0 && contentInput.value.trim()) return 'Text + Image Mode'
  if (selectedImages.value.length > 0) return 'Image Post Mode'
  return 'Text Post Mode'
})

function getGroupName(id) {
  return channelGroups.value.find(g => g.id === id)?.name ?? id
}

const groupAccountsByPlatform = computed(() => {
  const map = {}
  for (const acc of allGroupAccounts.value) {
    const p = acc.platform || 'other'
    if (!map[p]) map[p] = []
    map[p].push(acc)
  }
  return Object.entries(map).map(([platform, accounts]) => ({ platform, accounts }))
})

const PLATFORM_COLORS = {
  facebook: '#1877F2',
  instagram: '#E1306C',
  twitter: '#1DA1F2',
  x: '#000000',
  linkedin: '#0A66C2',
  whatsapp: '#25D366',
  youtube: '#FF0000',
  tiktok: '#010101',
}

function platformColor(platform) {
  return PLATFORM_COLORS[platform?.toLowerCase()] ?? '#6B7280'
}

function isPlatformFullySelected(accounts) {
  return accounts.every(a => newGroupAccountIds.value.includes(a.id))
}

function togglePlatformAccounts(platform, accounts) {
  const allSelected = isPlatformFullySelected(accounts)
  const ids = accounts.map(a => a.id)
  if (allSelected) {
    newGroupAccountIds.value = newGroupAccountIds.value.filter(id => !ids.includes(id))
  } else {
    const existing = new Set(newGroupAccountIds.value)
    ids.forEach(id => existing.add(id))
    newGroupAccountIds.value = [...existing]
  }
}

function selectAllGroupAccounts() {
  newGroupAccountIds.value = allGroupAccounts.value.map(a => a.id)
}

async function openCreateGroupModal() {
  showCreateGroupModal.value = true
  newGroupName.value = ''
  newGroupAccountIds.value = []
  createGroupError.value = ''
  loadingGroupAccounts.value = true
  try {
    const res = await smartPostApi.getAllSocialAccounts()
    allGroupAccounts.value = Array.isArray(res.data) ? res.data : (res.data?.accounts ?? [])
  } catch {
    allGroupAccounts.value = []
  } finally {
    loadingGroupAccounts.value = false
  }
}

async function submitCreateGroup() {
  if (!newGroupName.value.trim() || !newGroupAccountIds.value.length) return
  creatingGroup.value = true
  createGroupError.value = ''
  try {
    await smartPostApi.createChannelGroup({
      name: newGroupName.value.trim(),
      description: `${newGroupAccountIds.value.length} account(s)`,
      social_account_ids: newGroupAccountIds.value,
    })
    showCreateGroupModal.value = false
    await loadChannelGroups()
    // Auto-select the newly created group
    const latest = channelGroups.value[channelGroups.value.length - 1]
    if (latest && !selectedGroupIds.value.includes(latest.id)) {
      selectedGroupIds.value.push(latest.id)
    }
  } catch (e) {
    createGroupError.value = e?.response?.data?.detail || 'Failed to create group. Please try again.'
  } finally {
    creatingGroup.value = false
  }
}

function applyTemplate(tpl) {
  contentInput.value = tpl.text
  showTemplates.value = false
}

const emojis = ['🎉', '🚀', '💡', '🌟', '👋', '🔥', '💪', '✅', '📢', '🎯']
let emojiIndex = 0
function insertEmoji() {
  contentInput.value += emojis[emojiIndex++ % emojis.length]
}

async function enhanceWithAI() {
  if (!contentInput.value.trim()) return
  aiLoading.value = true
  try {
    const res = await smartPostApi.optimizeContent({ content: contentInput.value })
    if (res.data?.optimized_content) contentInput.value = res.data.optimized_content
  } catch { /* silent */ } finally {
    aiLoading.value = false
  }
}

function handleFileInput(e) {
  processFiles(Array.from(e.target.files || []))
  if (fileInput.value) fileInput.value.value = ''
}

function handleDrop(e) {
  isDragging.value = false
  processFiles(Array.from(e.dataTransfer?.files || []))
}

function processFiles(files) {
  const imageFiles = files.filter(f => f.type.startsWith('image/') || f.type.startsWith('video/')).slice(0, 4 - selectedImages.value.length)
  imageFiles.forEach(file => {
    const reader = new FileReader()
    reader.onload = (ev) => {
      selectedImages.value.push({ name: file.name, preview: ev.target?.result, file })
    }
    reader.readAsDataURL(file)
  })
}

function removeImage(index) {
  selectedImages.value.splice(index, 1)
}

async function searchImages() {
  if (!searchImageQuery.value.trim()) return
  searchingImages.value = true
  imageSearchResults.value = []
  try {
    const res = await smartPostApi.searchImages({ query: searchImageQuery.value })
    imageSearchResults.value = res.data?.images ?? res.data ?? []
  } catch { imageSearchResults.value = [] } finally {
    searchingImages.value = false
  }
}

function selectSearchImage(img) {
  selectedImages.value.push({ name: img.title || 'image', preview: img.thumbnail || img.url, file: null, url: img.url })
  showImageSearch.value = false
}

async function publishNow() {
  if (!canPublish.value) return
  publishing.value = true
  publishResults.value = []
  try {
    // Resolve image URL: upload local files, use direct URL for search images
    let imageUrl = null
    if (selectedImages.value.length > 0) {
      const img = selectedImages.value[0]
      if (img.url) {
        imageUrl = img.url
      } else if (img.file) {
        const formData = new FormData()
        formData.append('file', img.file)
        const uploadRes = await smartPostApi.uploadMedia(formData)
        imageUrl = uploadRes.data?.url || uploadRes.data?.file_url || null
      }
    }

    const tplName = selectedTemplate.value
      ? (selectedTemplate.value.template_name || selectedTemplate.value.name)
      : null

    const payload = {
      post_id: crypto.randomUUID(),
      title: contentInput.value.trim().slice(0, 50) || 'Post',
      content: contentInput.value,
      channel_group_ids: selectedGroupIds.value,
      // When a template is chosen → news_card mode so the backend renders the card
      // image_url becomes the background image inside the news card (optional)
      mode: tplName ? 'news_card' : (imageUrl ? 'image' : 'text'),
      ...(imageUrl && { image_url: imageUrl }),
      ...(tplName && { template_name: tplName }),
    }
    const res = await smartPostApi.publishNow(payload)
    const channels = res.data?.channels ?? {}
    const channelResults = Object.entries(channels).map(([k, v]) => ({
      platform: k,
      success: v?.success ?? false,
      message: v?.message ?? (v?.success ? 'Published' : 'Failed'),
    }))
    publishResults.value = channelResults.length
      ? channelResults
      : [{ platform: 'All channels', success: true, message: 'Published successfully' }]
    if (res.data?.success || publishResults.value.some(r => r.success)) {
      contentInput.value = ''
      selectedImages.value = []
      selectedGroupIds.value = []
      selectedTemplate.value = null
    }
  } catch (e) {
    publishResults.value = [{ platform: 'Error', success: false, message: e?.response?.data?.detail || 'Failed to publish' }]
  } finally {
    publishing.value = false
  }
}

async function saveDraft() {
  if (!contentInput.value.trim()) return
  saving.value = true
  try {
    await smartPostApi.createDraft({
      title: contentInput.value.trim().slice(0, 50) || 'Draft',
      content: { text: contentInput.value },
      channels: [],
      channel_group_ids: selectedGroupIds.value.length ? selectedGroupIds.value : undefined,
    })
    publishResults.value = [{ platform: 'Draft', success: true, message: 'Draft saved successfully' }]
    contentInput.value = ''
    selectedGroupIds.value = []
  } catch (e) {
    publishResults.value = [{ platform: 'Error', success: false, message: e?.response?.data?.detail || 'Failed to save draft' }]
  } finally {
    saving.value = false
  }
}

async function schedulePost() {
  if (!scheduleDate.value || !scheduleTime.value || !contentInput.value.trim()) return
  scheduling.value = true
  try {
    const scheduledAt = new Date(`${scheduleDate.value}T${scheduleTime.value}`).toISOString()
    await smartPostApi.createDraft({
      title: contentInput.value.trim().slice(0, 50) || 'Scheduled Post',
      content: { text: contentInput.value },
      channels: [],
      channel_group_ids: selectedGroupIds.value.length ? selectedGroupIds.value : undefined,
      scheduled_at: scheduledAt,
    })
    publishResults.value = [{ platform: 'Scheduled', success: true, message: `Post scheduled for ${scheduleDate.value} at ${scheduleTime.value}` }]
    showScheduleModal.value = false
    contentInput.value = ''
    selectedGroupIds.value = []
  } catch (e) {
    publishResults.value = [{ platform: 'Error', success: false, message: e?.response?.data?.detail || 'Failed to schedule post' }]
  } finally {
    scheduling.value = false
  }
}

async function createDefaultGroup() {
  creatingDefaultGroup.value = true
  channelError.value = ''
  try {
    // Fetch all connected social accounts (plain list, no pagination)
    const accountsRes = await smartPostApi.getAllSocialAccounts()
    const accounts = Array.isArray(accountsRes.data) ? accountsRes.data : (accountsRes.data?.accounts ?? [])
    if (!accounts.length) {
      channelError.value = 'No connected social accounts found. Please connect accounts in Social Accounts page first.'
      return
    }
    // Create a "All Accounts" channel group with every connected account
    await smartPostApi.createChannelGroup({
      name: 'All Accounts',
      description: 'Default group — all connected accounts',
      social_account_ids: accounts.map(a => a.id),
    })
    // Reload groups and auto-select the new one
    await loadChannelGroups()
    if (channelGroups.value.length > 0) {
      selectedGroupIds.value = [channelGroups.value[0].id]
    }
  } catch (e) {
    channelError.value = e?.response?.data?.detail || 'Failed to create default group'
  } finally {
    creatingDefaultGroup.value = false
  }
}

async function loadChannelGroups() {
  loadingChannels.value = true
  channelError.value = ''
  try {
    const res = await smartPostApi.getChannelGroups()
    channelGroups.value = res.data?.channel_groups ?? []
  } catch (e) {
    channelGroups.value = []
    channelError.value = e?.response?.data?.detail || 'Failed to load channel groups'
  } finally {
    loadingChannels.value = false
  }
}

onMounted(() => {
  loadChannelGroups()
  const stored = localStorage.getItem('postContent')
  if (stored) {
    contentInput.value = stored
    localStorage.removeItem('postContent')
  }
})
</script>
