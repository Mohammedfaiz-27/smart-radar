<template>
  <div 
    class="card p-6 cursor-pointer transform transition-all duration-200 hover:scale-105 hover:shadow-lg"
    @click="handleClick"
  >
    <div class="flex items-center">
      <div class="flex-shrink-0">
        <div :class="iconClasses">
          <component :is="icon" class="h-6 w-6" />
        </div>
      </div>
      <div class="ml-5 w-0 flex-1">
        <dl>
          <dt class="text-sm font-medium text-gray-500 truncate">
            {{ title }}
          </dt>
          <dd class="text-lg font-semibold text-gray-900">
            {{ value }}
          </dd>
        </dl>
      </div>
      <!-- Click indicator -->
      <div class="flex-shrink-0 ml-3 opacity-50">
        <svg class="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { 
  UserGroupIcon, 
  BuildingOfficeIcon, 
  ExclamationTriangleIcon, 
  ChartBarIcon 
} from '@heroicons/vue/24/outline'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: [Number, String],
    required: true
  },
  color: {
    type: String,
    default: 'blue',
    validator: (value) => ['blue', 'green', 'orange', 'red'].includes(value)
  }
})

const emit = defineEmits(['click'])

const handleClick = () => {
  emit('click', props.title)
}

const iconClasses = computed(() => {
  const baseClasses = 'p-2 rounded-lg'
  const colorMap = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    orange: 'bg-orange-100 text-orange-600',
    red: 'bg-red-100 text-red-600'
  }
  return `${baseClasses} ${colorMap[props.color]}`
})

const icon = computed(() => {
  const iconMap = {
    'Our Posts': UserGroupIcon,
    'Competitor Posts': BuildingOfficeIcon,
    'Threats Detected': ExclamationTriangleIcon,
    'Total Posts': ChartBarIcon
  }
  return iconMap[props.title] || ChartBarIcon
})
</script>