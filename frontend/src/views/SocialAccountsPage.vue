<template>
  <div class="p-6 max-w-7xl mx-auto space-y-8">

    <!-- ── Header ─────────────────────────────────────────────────── -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Social Accounts & Channel Groups</h1>
        <p class="text-gray-500 mt-1">Manage your connected accounts and group them for publishing.</p>
      </div>
      <button @click="openConnectModal()"
        class="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg shadow-sm transition-colors">
        <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        Connect Account
      </button>
    </div>

    <!-- Global Error -->
    <div v-if="error" class="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
      <svg class="w-5 h-5 text-red-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
      </svg>
      <span class="text-red-700 text-sm flex-1">{{ error }}</span>
      <button @click="error = null" class="text-red-400 hover:text-red-600">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
    </div>

    <!-- ── SECTION 1: Connected Accounts ──────────────────────────── -->
    <div>
      <!-- Section header + filters -->
      <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div class="flex items-center gap-3">
          <h2 class="text-base font-semibold text-gray-900">Connected Accounts</h2>
          <span class="text-xs bg-gray-100 text-gray-600 px-2.5 py-1 rounded-full font-medium">
            {{ accounts.length }} total
          </span>
        </div>

        <!-- Platform filter chips -->
        <div class="flex flex-wrap gap-2">
          <button v-for="f in platformFilters" :key="f.value" @click="platformFilter = f.value"
            :class="[
              'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all border',
              platformFilter === f.value
                ? 'border-transparent text-white shadow-sm'
                : 'border-gray-200 text-gray-600 bg-white hover:border-gray-300 hover:bg-gray-50'
            ]"
            :style="platformFilter === f.value && f.color ? { background: f.color } : {}">
            <span v-if="f.svg" class="w-3.5 h-3.5 flex items-center justify-center" v-html="f.svg"></span>
            {{ f.label }}
            <span v-if="f.value !== 'all'" class="opacity-75">({{ accountCountByPlatform[f.value] || 0 }})</span>
          </button>
        </div>
      </div>

      <!-- Selection bar -->
      <div v-if="selectedAccountIds.length > 0"
        class="mb-4 flex items-center justify-between bg-blue-50 border border-blue-200 rounded-xl px-5 py-3">
        <span class="text-sm font-medium text-blue-800">
          {{ selectedAccountIds.length }} account(s) selected
        </span>
        <div class="flex gap-2">
          <button @click="selectedAccountIds = []"
            class="text-xs text-blue-600 hover:text-blue-800 border border-blue-300 px-3 py-1.5 rounded-lg transition-colors">
            Clear
          </button>
          <button @click="createGroupFromSelection"
            class="inline-flex items-center gap-1.5 text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg transition-colors">
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
            </svg>
            Create Group from Selection
          </button>
        </div>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loadingAccounts" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        <div v-for="i in 8" :key="i" class="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 animate-pulse">
          <div class="flex items-center gap-3 mb-4">
            <div class="w-11 h-11 rounded-xl bg-gray-200"></div>
            <div class="flex-1">
              <div class="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
              <div class="h-3 bg-gray-100 rounded w-1/2"></div>
            </div>
          </div>
          <div class="h-8 bg-gray-100 rounded-lg"></div>
        </div>
      </div>

      <!-- Empty -->
      <div v-else-if="filteredAccounts.length === 0 && accounts.length === 0"
        class="bg-white rounded-2xl border border-gray-200 shadow-sm p-16 text-center">
        <div class="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <svg class="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
          </svg>
        </div>
        <h3 class="text-sm font-semibold text-gray-900 mb-1">No accounts connected</h3>
        <p class="text-sm text-gray-500 mb-5">Connect your first social account to start publishing.</p>
        <button @click="openConnectModal()"
          class="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors">
          Connect Account
        </button>
      </div>

      <div v-else-if="filteredAccounts.length === 0"
        class="bg-white rounded-2xl border border-gray-200 shadow-sm p-12 text-center">
        <p class="text-sm text-gray-500">No accounts for this platform.</p>
      </div>

      <!-- Account cards grid -->
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        <div v-for="acc in filteredAccounts" :key="acc.id"
          :class="[
            'bg-white rounded-2xl border shadow-sm p-5 flex flex-col gap-4 transition-all cursor-pointer hover:shadow-md',
            selectedAccountIds.includes(acc.id)
              ? 'border-blue-400 ring-1 ring-blue-400 bg-blue-50/30'
              : 'border-gray-200 hover:border-gray-300'
          ]"
          @click="toggleSelectAccount(acc.id)">

          <!-- Card top: icon + name -->
          <div class="flex items-start gap-3">
            <div class="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm"
              :style="{ background: platformColor(acc.platform) }"
              v-html="platformSvgLarge(acc.platform)">
            </div>
            <div class="flex-1 min-w-0">
              <div class="font-semibold text-sm text-gray-900 truncate leading-tight">
                {{ acc.account_name || acc.account_id }}
              </div>
              <div class="text-xs text-gray-400 truncate mt-0.5 capitalize">{{ acc.platform }}</div>
            </div>
            <!-- Selected check -->
            <div v-if="selectedAccountIds.includes(acc.id)"
              class="w-5 h-5 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
              <svg class="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
              </svg>
            </div>
          </div>

          <!-- Account ID chip -->
          <div class="text-xs text-gray-400 bg-gray-50 rounded-lg px-2.5 py-1.5 truncate font-mono">
            {{ acc.account_id }}
          </div>

          <!-- Footer: status + actions -->
          <div class="flex items-center justify-between pt-1 border-t border-gray-100">
            <span :class="[
              'text-xs font-medium px-2 py-0.5 rounded-full',
              acc.status === 'connected' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
            ]">
              {{ acc.status === 'connected' ? 'Connected' : acc.status || 'Active' }}
            </span>
            <button @click.stop="handleDisconnect(acc.id)" :disabled="disconnecting === acc.id"
              class="text-xs text-red-500 hover:text-red-700 disabled:opacity-40 transition-colors font-medium">
              {{ disconnecting === acc.id ? 'Removing…' : 'Disconnect' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── SECTION 2: Channel Groups ──────────────────────────────── -->
    <div>
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-3">
          <h2 class="text-base font-semibold text-gray-900">Channel Groups</h2>
          <span class="text-xs bg-purple-100 text-purple-700 px-2.5 py-1 rounded-full font-medium">
            {{ channelGroups.length }} group(s)
          </span>
        </div>
        <button @click="openGroupModal(null)"
          class="inline-flex items-center px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium rounded-lg shadow-sm transition-colors">
          <svg class="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          New Group
        </button>
      </div>

      <!-- Loading -->
      <div v-if="loadingGroups" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="i in 3" :key="i" class="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 animate-pulse">
          <div class="h-5 bg-gray-200 rounded w-2/3 mb-3"></div>
          <div class="h-4 bg-gray-100 rounded w-1/3 mb-4"></div>
          <div class="flex gap-1 mb-4">
            <div v-for="j in 3" :key="j" class="w-7 h-7 bg-gray-200 rounded-full"></div>
          </div>
          <div class="h-8 bg-gray-100 rounded-lg"></div>
        </div>
      </div>

      <!-- Empty -->
      <div v-else-if="channelGroups.length === 0"
        class="bg-white rounded-2xl border border-dashed border-gray-300 p-14 text-center">
        <div class="w-14 h-14 bg-purple-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <svg class="w-7 h-7 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
          </svg>
        </div>
        <h3 class="text-sm font-semibold text-gray-900 mb-1">No channel groups yet</h3>
        <p class="text-sm text-gray-500 mb-5">Bundle accounts together so you can publish to multiple channels at once.</p>
        <button @click="openGroupModal(null)"
          class="inline-flex items-center px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium rounded-lg transition-colors">
          Create First Group
        </button>
      </div>

      <!-- Group card grid -->
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="grp in channelGroups" :key="grp.id"
          class="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 flex flex-col gap-4 hover:shadow-md transition-shadow">

          <!-- Group header -->
          <div class="flex items-start justify-between gap-2">
            <div class="flex-1 min-w-0">
              <h3 class="font-semibold text-gray-900 text-sm leading-snug truncate">{{ grp.name }}</h3>
              <p v-if="grp.description" class="text-xs text-gray-400 mt-0.5 line-clamp-1">{{ grp.description }}</p>
            </div>
            <span class="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium flex-shrink-0">
              {{ grp.social_account_ids?.length || 0 }}
            </span>
          </div>

          <!-- Member platform icon stack -->
          <div class="flex flex-wrap items-center gap-1.5">
            <template v-for="(accId, i) in (grp.social_account_ids || []).slice(0, 8)" :key="accId">
              <div class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 shadow-sm"
                :style="{ background: platformColor(getAccountById(accId)?.platform) }"
                :title="getAccountById(accId)?.account_name || accId"
                v-html="platformSvgSmall(getAccountById(accId)?.platform)">
              </div>
            </template>
            <span v-if="(grp.social_account_ids?.length || 0) > 8"
              class="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full font-medium">
              +{{ grp.social_account_ids.length - 8 }}
            </span>
            <!-- Unique platform summary -->
            <div class="ml-auto flex items-center gap-1">
              <span v-for="plt in getGroupPlatforms(grp)" :key="plt"
                class="text-xs text-gray-500 capitalize bg-gray-50 border border-gray-200 px-1.5 py-0.5 rounded">
                {{ plt }}
              </span>
            </div>
          </div>

          <!-- Account name preview (first 3) -->
          <div class="space-y-1">
            <div v-for="accId in (grp.social_account_ids || []).slice(0, 3)" :key="accId"
              class="flex items-center gap-2 text-xs text-gray-500">
              <span class="w-4 h-4 rounded flex items-center justify-center flex-shrink-0"
                :style="{ background: platformColor(getAccountById(accId)?.platform) }"
                v-html="platformSvgTiny(getAccountById(accId)?.platform)"></span>
              <span class="truncate">{{ getAccountById(accId)?.account_name || getAccountById(accId)?.account_id || accId }}</span>
            </div>
            <div v-if="(grp.social_account_ids?.length || 0) > 3" class="text-xs text-gray-400 pl-6">
              +{{ grp.social_account_ids.length - 3 }} more accounts
            </div>
          </div>

          <!-- Actions -->
          <div class="flex gap-2 pt-1 border-t border-gray-100">
            <button @click="openGroupModal(grp)"
              class="flex-1 text-xs font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 py-2 rounded-lg transition-colors">
              Edit
            </button>
            <button @click="deleteGroup(grp.id)" :disabled="deletingGroup === grp.id"
              class="flex-1 text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 py-2 rounded-lg disabled:opacity-40 transition-colors">
              {{ deletingGroup === grp.id ? 'Deleting…' : 'Delete' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Connect Account Modal ──────────────────────────────────── -->
    <div v-if="showConnectModal" class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md">
        <div class="p-6 border-b border-gray-100 flex items-center justify-between">
          <h2 class="text-lg font-semibold text-gray-900">Connect Social Account</h2>
          <button @click="showConnectModal = false" class="text-gray-400 hover:text-gray-600">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <form @submit.prevent="handleConnect" class="p-6 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Platform</label>
            <select v-model="connectForm.platform" required
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="">Select platform…</option>
              <option value="instagram">Instagram</option>
              <option value="facebook">Facebook</option>
              <option value="twitter">Twitter / X</option>
              <option value="linkedin">LinkedIn</option>
              <option value="whatsapp">WhatsApp</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Account Name</label>
            <input v-model="connectForm.account_name" required placeholder="Display name"
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"/>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Account ID / Periskope ID</label>
            <input v-model="connectForm.account_id" required placeholder="e.g. 120363422905991225@g.us"
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"/>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Access Token (optional)</label>
            <input v-model="connectForm.access_token" type="password" placeholder="Paste access token"
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"/>
          </div>
          <div v-if="connectError" class="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
            {{ connectError }}
          </div>
          <div class="flex gap-3 pt-1">
            <button type="button" @click="showConnectModal = false"
              class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2 rounded-lg text-sm">Cancel</button>
            <button type="submit" :disabled="connecting"
              class="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 rounded-lg text-sm disabled:opacity-50">
              {{ connecting ? 'Connecting…' : 'Connect' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- ── Create/Edit Channel Group Modal ───────────────────────── -->
    <div v-if="showGroupModal" class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] flex flex-col">
        <div class="p-6 border-b border-gray-100 flex items-center justify-between flex-shrink-0">
          <h2 class="text-lg font-semibold text-gray-900">
            {{ editingGroup ? 'Edit Channel Group' : 'Create Channel Group' }}
          </h2>
          <button @click="showGroupModal = false" class="text-gray-400 hover:text-gray-600">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <div class="p-6 space-y-4 overflow-y-auto flex-1">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Group Name *</label>
            <input v-model="groupForm.name" required placeholder="e.g. Tamil Nadu News Channels"
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"/>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Description (optional)</label>
            <input v-model="groupForm.description" placeholder="What is this group for?"
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"/>
          </div>
          <div>
            <div class="flex items-center justify-between mb-2">
              <label class="block text-sm font-medium text-gray-700">Select Accounts *</label>
              <span class="text-xs text-purple-600 font-medium">{{ groupForm.social_account_ids.length }} selected</span>
            </div>
            <div class="flex gap-2 mb-3">
              <button type="button" @click="selectAllAccounts"
                class="text-xs px-3 py-1.5 border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-600 transition-colors">Select All</button>
              <button type="button" @click="groupForm.social_account_ids = []"
                class="text-xs px-3 py-1.5 border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-600 transition-colors">Clear</button>
            </div>
            <div class="space-y-1 max-h-64 overflow-y-auto border border-gray-200 rounded-xl p-2">
              <label v-for="acc in accounts" :key="acc.id"
                class="flex items-center gap-3 p-2.5 rounded-xl hover:bg-purple-50 cursor-pointer transition-colors"
                :class="groupForm.social_account_ids.includes(acc.id) ? 'bg-purple-50' : ''">
                <input type="checkbox" :value="acc.id" v-model="groupForm.social_account_ids"
                  class="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300 rounded"/>
                <span class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                  :style="{ background: platformColor(acc.platform) }"
                  v-html="platformSvgLarge(acc.platform)"></span>
                <div class="min-w-0 flex-1">
                  <div class="text-sm font-medium text-gray-900 truncate">{{ acc.account_name || acc.account_id }}</div>
                  <div class="text-xs text-gray-400 capitalize">{{ acc.platform }}</div>
                </div>
              </label>
              <div v-if="accounts.length === 0" class="text-center py-6 text-sm text-gray-500">
                No accounts connected yet.
              </div>
            </div>
          </div>
          <div v-if="groupError" class="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
            {{ groupError }}
          </div>
        </div>
        <div class="px-6 py-4 border-t border-gray-100 flex gap-3 flex-shrink-0">
          <button type="button" @click="showGroupModal = false"
            class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2.5 rounded-xl text-sm">Cancel</button>
          <button type="button" @click="saveGroup"
            :disabled="savingGroup || !groupForm.name.trim() || groupForm.social_account_ids.length === 0"
            class="flex-1 bg-purple-600 hover:bg-purple-700 text-white font-medium py-2.5 rounded-xl text-sm disabled:opacity-50">
            {{ savingGroup ? 'Saving…' : editingGroup ? 'Update Group' : 'Create Group' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { smartPostApi } from '@/services/smartpost.js'

// ── SVGs & colors ──────────────────────────────────────────────────
const PLATFORM_SVG = {
  twitter:   `<svg viewBox="0 0 24 24" fill="white"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.746l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>`,
  facebook:  `<svg viewBox="0 0 24 24" fill="white"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>`,
  linkedin:  `<svg viewBox="0 0 24 24" fill="white"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>`,
  instagram: `<svg viewBox="0 0 24 24" fill="white"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg>`,
  whatsapp:  `<svg viewBox="0 0 24 24" fill="white"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>`,
}

const PLATFORM_COLOR = {
  twitter:   '#000000',
  facebook:  '#1877F2',
  linkedin:  '#0A66C2',
  instagram: 'linear-gradient(135deg,#f09433,#e6683c 25%,#dc2743 50%,#cc2366 75%,#bc1888)',
  whatsapp:  '#25D366',
}

function wrapSvg(svgStr, size) {
  return svgStr.replace('<svg ', `<svg width="${size}" height="${size}" `)
}

const platformSvgLarge = (p) => wrapSvg(PLATFORM_SVG[p?.toLowerCase()] || `<svg viewBox="0 0 24 24" fill="white"><circle cx="12" cy="12" r="10"/></svg>`, 20)
const platformSvgSmall = (p) => wrapSvg(PLATFORM_SVG[p?.toLowerCase()] || `<svg viewBox="0 0 24 24" fill="white"><circle cx="12" cy="12" r="10"/></svg>`, 16)
const platformSvgTiny  = (p) => wrapSvg(PLATFORM_SVG[p?.toLowerCase()] || `<svg viewBox="0 0 24 24" fill="white"><circle cx="12" cy="12" r="10"/></svg>`, 12)
const platformColor    = (p) => PLATFORM_COLOR[p?.toLowerCase()] || '#6B7280'

// ── Platform filter config ─────────────────────────────────────────
const platformFilters = [
  { value: 'all',       label: 'All',       color: '#374151', svg: null },
  { value: 'whatsapp',  label: 'WhatsApp',  color: '#25D366', svg: wrapSvg(PLATFORM_SVG.whatsapp, 12) },
  { value: 'instagram', label: 'Instagram', color: '#dc2743', svg: wrapSvg(PLATFORM_SVG.instagram, 12) },
  { value: 'facebook',  label: 'Facebook',  color: '#1877F2', svg: wrapSvg(PLATFORM_SVG.facebook, 12) },
  { value: 'linkedin',  label: 'LinkedIn',  color: '#0A66C2', svg: wrapSvg(PLATFORM_SVG.linkedin, 12) },
  { value: 'twitter',   label: 'X',         color: '#000000', svg: wrapSvg(PLATFORM_SVG.twitter, 12) },
]

// ── State ──────────────────────────────────────────────────────────
const accounts          = ref([])
const channelGroups     = ref([])
const error             = ref(null)
const loadingAccounts   = ref(false)
const loadingGroups     = ref(false)
const disconnecting     = ref(null)
const deletingGroup     = ref(null)
const platformFilter    = ref('all')
const selectedAccountIds = ref([])

const showConnectModal = ref(false)
const connecting       = ref(false)
const connectError     = ref(null)
const connectForm      = ref({ platform: '', account_name: '', account_id: '', access_token: '' })

const showGroupModal = ref(false)
const editingGroup   = ref(null)
const savingGroup    = ref(false)
const groupError     = ref(null)
const groupForm      = ref({ name: '', description: '', social_account_ids: [] })

// ── Computed ───────────────────────────────────────────────────────
const filteredAccounts = computed(() => {
  if (platformFilter.value === 'all') return accounts.value
  return accounts.value.filter(a => a.platform?.toLowerCase() === platformFilter.value)
})

const accountCountByPlatform = computed(() => {
  const counts = {}
  accounts.value.forEach(a => {
    const p = a.platform?.toLowerCase()
    counts[p] = (counts[p] || 0) + 1
  })
  return counts
})

function getAccountById(id) {
  return accounts.value.find(a => a.id === id || a.account_id === id)
}

function getGroupPlatforms(grp) {
  const platforms = new Set()
  ;(grp.social_account_ids || []).forEach(id => {
    const acc = getAccountById(id)
    if (acc?.platform) platforms.add(acc.platform.toLowerCase())
  })
  return [...platforms].slice(0, 3)
}

// ── Account selection ──────────────────────────────────────────────
function toggleSelectAccount(id) {
  const idx = selectedAccountIds.value.indexOf(id)
  if (idx === -1) selectedAccountIds.value.push(id)
  else selectedAccountIds.value.splice(idx, 1)
}

function createGroupFromSelection() {
  openGroupModal(null)
  groupForm.value.social_account_ids = [...selectedAccountIds.value]
  selectedAccountIds.value = []
}

// ── Data loading ───────────────────────────────────────────────────
async function fetchAccounts() {
  loadingAccounts.value = true
  try {
    const res = await smartPostApi.getAllSocialAccounts()
    accounts.value = Array.isArray(res.data) ? res.data : (res.data?.accounts ?? [])
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Failed to load accounts.'
  } finally {
    loadingAccounts.value = false
  }
}

async function fetchGroups() {
  loadingGroups.value = true
  try {
    const res = await smartPostApi.getChannelGroups()
    channelGroups.value = res.data?.channel_groups ?? []
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Failed to load channel groups.'
  } finally {
    loadingGroups.value = false
  }
}

// ── Account actions ────────────────────────────────────────────────
function openConnectModal() {
  connectForm.value = { platform: '', account_name: '', account_id: '', access_token: '' }
  connectError.value = null
  showConnectModal.value = true
}

async function handleConnect() {
  connecting.value = true
  connectError.value = null
  try {
    const { platform, account_name, account_id, access_token } = connectForm.value
    await smartPostApi.connectSocialAccount({
      platform,
      connection_method: 'manual',
      account_name,
      account_id,
      periskope_id: account_id,
      ...(access_token ? { access_token } : {}),
    })
    showConnectModal.value = false
    await fetchAccounts()
  } catch (e) {
    connectError.value = e.response?.data?.detail ?? 'Connection failed.'
  } finally {
    connecting.value = false
  }
}

async function handleDisconnect(id) {
  if (!confirm('Disconnect this account?')) return
  disconnecting.value = id
  error.value = null
  try {
    await smartPostApi.disconnectSocialAccount(id)
    await fetchAccounts()
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Failed to disconnect.'
  } finally {
    disconnecting.value = null
  }
}

// ── Channel Group actions ──────────────────────────────────────────
function openGroupModal(grp) {
  editingGroup.value = grp
  groupError.value = null
  groupForm.value = {
    name: grp?.name ?? '',
    description: grp?.description ?? '',
    social_account_ids: [...(grp?.social_account_ids ?? [])],
  }
  showGroupModal.value = true
}

function selectAllAccounts() {
  groupForm.value.social_account_ids = accounts.value.map(a => a.id)
}

async function saveGroup() {
  if (!groupForm.value.name.trim() || groupForm.value.social_account_ids.length === 0) return
  savingGroup.value = true
  groupError.value = null
  try {
    const payload = {
      name: groupForm.value.name.trim(),
      description: groupForm.value.description.trim() || undefined,
      social_account_ids: groupForm.value.social_account_ids,
    }
    if (editingGroup.value) {
      await smartPostApi.updateChannelGroup(editingGroup.value.id, payload)
    } else {
      await smartPostApi.createChannelGroup(payload)
    }
    showGroupModal.value = false
    await fetchGroups()
  } catch (e) {
    groupError.value = e.response?.data?.detail ?? 'Failed to save group.'
  } finally {
    savingGroup.value = false
  }
}

async function deleteGroup(id) {
  if (!confirm('Delete this channel group?')) return
  deletingGroup.value = id
  error.value = null
  try {
    await smartPostApi.deleteChannelGroup(id)
    await fetchGroups()
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Failed to delete group.'
  } finally {
    deletingGroup.value = null
  }
}

onMounted(async () => {
  await Promise.all([fetchAccounts(), fetchGroups()])
})
</script>
