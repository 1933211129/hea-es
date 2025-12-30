<template>
  <details 
    v-if="hasSource" 
    class="mt-2 text-xs"
  >
    <summary class="cursor-pointer text-indigo-600 hover:underline">
      Sources
      <span v-if="sourceCount > 0" class="text-slate-500">({{ sourceCount }})</span>
    </summary>
    
    <!-- Table Source -->
    <div v-if="isTable" class="mt-1 space-y-2 text-slate-700">
      <div v-if="tableLocation" class="text-sm font-mono bg-slate-50 px-2 py-1 rounded border border-slate-200">
        {{ tableLocation }}
      </div>
      <div v-if="tableRefs.length" class="space-y-1">
        <div class="text-slate-500 text-xs uppercase tracking-wide">References</div>
        <ul class="list-disc list-inside space-y-1">
          <li 
            v-for="(r, i) in tableRefs" 
            :key="i" 
            class="bg-slate-50 border border-slate-200 rounded px-2 py-1"
          >
            {{ r }}
          </li>
        </ul>
      </div>
      <div 
        v-if="tableHtml" 
        class="bg-white border border-slate-200 rounded p-2 overflow-x-auto raw-html-table" 
        v-html="tableHtml"
      ></div>
    </div>
    
    <!-- Text Source -->
    <ul v-else class="mt-1 space-y-1 text-slate-600">
      <li 
        v-for="(s, i) in normalizedSource" 
        :key="i" 
        class="bg-slate-50 border border-slate-200 rounded px-2 py-1"
      >
        {{ s }}
      </li>
    </ul>
  </details>
</template>

<script setup>
import { computed } from 'vue'
import {
  normalizeSource,
  isTableSource,
  getTableRefs,
  getTableLocation,
  getTableHtml,
  hasAnySource,
  getSourceCount
} from '../utils/source'

const props = defineProps({
  source: {
    type: [Array, Object],
    default: null
  }
})

const hasSource = computed(() => hasAnySource(props.source))
const sourceCount = computed(() => getSourceCount(props.source))
const isTable = computed(() => isTableSource(props.source))
const normalizedSource = computed(() => normalizeSource(props.source))
const tableRefs = computed(() => getTableRefs(props.source))
const tableLocation = computed(() => getTableLocation(props.source))
const tableHtml = computed(() => getTableHtml(props.source))
</script>

