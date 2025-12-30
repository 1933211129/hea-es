<template>
  <details class="mt-2 text-xs">
    <summary class="cursor-pointer text-amber-600 hover:underline flex items-center gap-1">
      <i class="ph ph-image"></i>
      <span>Figure Source</span>
    </summary>
    <div class="mt-1 space-y-2 text-slate-700">
      <div 
        v-if="figureSource.location" 
        class="text-sm font-mono bg-slate-50 px-2 py-1 rounded border border-slate-200"
      >
        {{ figureSource.location }}
      </div>
      <div v-if="figureRefs.length" class="space-y-1">
        <div class="text-slate-500 text-xs uppercase tracking-wide">References</div>
        <ul class="list-disc list-inside space-y-1">
          <li 
            v-for="(r, j) in figureRefs" 
            :key="j" 
            class="bg-slate-50 border border-slate-200 rounded px-2 py-1"
          >
            {{ r }}
          </li>
        </ul>
      </div>
      <div 
        v-if="figureSource.img_path" 
        class="border border-slate-200 rounded-lg overflow-hidden bg-slate-50 p-2"
      >
        <img 
          :src="imageUrl" 
          alt="Extracted Figure" 
          class="max-w-full h-auto object-contain max-h-[400px] mx-auto rounded"
          @error="(e) => e.target.style.display = 'none'"
        >
        <div class="text-xs text-slate-400 font-mono mt-2 text-center break-all px-2 select-all">
          {{ figureSource.img_path }}
        </div>
      </div>
    </div>
  </details>
</template>

<script setup>
import { computed } from 'vue'
import { getFigureRefs } from '../utils/source'
import { paperApi } from '../utils/api'

const props = defineProps({
  figureSource: {
    type: Object,
    required: true
  }
})

const figureRefs = computed(() => getFigureRefs(props.figureSource))
const imageUrl = computed(() => paperApi.getImageUrl(props.figureSource.img_path))
</script>

