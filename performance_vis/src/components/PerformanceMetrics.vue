<template>
  <div>
    <h3 class="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
      <i class="ph ph-lightning text-indigo-500"></i> 实验性能
    </h3>
    <div class="space-y-4">
      <!-- Overpotential -->
      <div class="border border-slate-200 rounded-lg p-4">
        <div class="text-xs font-semibold text-slate-500 uppercase mb-2 flex items-center gap-1">
          <i class="ph ph-lightning text-amber-500"></i> Overpotential
        </div>
        <div v-if="(alloy.performance?.overpotential || []).length === 0" class="text-sm text-slate-400">
          None
        </div>
        <div v-else class="space-y-2">
          <div 
            v-for="(op, i) in alloy.performance?.overpotential || []" 
            :key="i" 
            class="p-2 rounded border border-slate-200 bg-slate-50"
          >
            <div class="text-sm font-semibold text-slate-800">
              {{ op.value || '—' }} {{ op.unit || '' }}
              <span v-if="op.current_density" class="text-xs text-slate-500 ml-2">
                (@ {{ op.current_density }})
              </span>
            </div>
            <SourceInline :source="op.source" :highlight-values="[op.value, op.current_density].filter(v => v)" />
            <FigureSourceInline v-if="op.figure_source" :figure-source="op.figure_source" :highlight-values="[op.value, op.current_density].filter(v => v)" />
          </div>
        </div>
      </div>

      <!-- Tafel Slope -->
      <div 
        v-if="alloy.performance?.tafel_slope !== null" 
        class="border border-slate-200 rounded-lg p-4"
      >
        <div class="text-xs font-semibold text-slate-500 uppercase mb-2 flex items-center gap-1">
          <i class="ph ph-trend-up text-emerald-500"></i> Tafel Slope
        </div>
        <div class="text-sm font-semibold text-slate-800">
          {{ alloy.performance?.tafel_slope?.value || '—' }} {{ alloy.performance?.tafel_slope?.unit || '' }}
        </div>
        <SourceInline :source="alloy.performance?.tafel_slope?.source" :highlight-values="alloy.performance?.tafel_slope?.value" />
      </div>

      <!-- Stability -->
      <div class="border border-slate-200 rounded-lg p-4">
        <div class="text-xs font-semibold text-slate-500 uppercase mb-2 flex items-center gap-1">
          <i class="ph ph-timer text-rose-500"></i> Stability
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm text-slate-800">
          <div>Cycle Count: {{ alloy.performance?.stability?.cycle_count ?? '—' }}</div>
          <div>Method: {{ alloy.performance?.stability?.test_method || '—' }}</div>
          <div>Duration: {{ alloy.performance?.stability?.duration_hours ?? '—' }}</div>
          <div>Retention: {{ alloy.performance?.stability?.performance_retention ?? '—' }}</div>
          <div class="sm:col-span-2">
            Degradation: {{ alloy.performance?.stability?.degradation_details || '—' }}
          </div>
        </div>
        <SourceInline 
          :source="alloy.performance?.stability?.source" 
          :highlight-values="{
            cycle_count: alloy.performance?.stability?.cycle_count,
            duration_hours: alloy.performance?.stability?.duration_hours,
            test_method: alloy.performance?.stability?.test_method,
            degradation_details: alloy.performance?.stability?.degradation_details,
            performance_retention: alloy.performance?.stability?.performance_retention
          }"
        />
      </div>

      <!-- Supplementary Performance -->
      <div class="border border-slate-200 rounded-lg p-4">
        <div class="text-xs font-semibold text-slate-500 uppercase mb-2 flex items-center gap-1">
          <i class="ph ph-list-bullets text-blue-500"></i> Supplementary Performance
        </div>
        <div v-if="(alloy.performance?.supplementary_performance || []).length === 0" class="text-sm text-slate-400">
          None
        </div>
        <div v-else class="space-y-2">
          <div 
            v-for="(sp, i) in alloy.performance?.supplementary_performance || []" 
            :key="i" 
            class="p-2 rounded border border-slate-200 bg-slate-50"
          >
            <div class="text-sm font-semibold text-slate-800">{{ sp.key || '—' }}</div>
            <div class="text-sm text-slate-700">{{ sp.value || '—' }}</div>
            <SourceInline :source="sp.source" :highlight-values="[sp.key, sp.value].filter(v => v)" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import SourceInline from './SourceInline.vue'
import FigureSourceInline from './FigureSourceInline.vue'

defineProps({
  alloy: {
    type: Object,
    required: true
  }
})
</script>

