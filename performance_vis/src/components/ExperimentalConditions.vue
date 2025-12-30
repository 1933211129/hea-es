<template>
  <div>
    <h3 class="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
      <i class="ph ph-flask text-indigo-500"></i> 实验条件
    </h3>
    <div class="space-y-4">
      <!-- Electrolyte -->
      <ConditionItem
        title="Electrolyte"
        icon="ph-flask"
        icon-color="text-amber-500"
        :data="alloy.experimental_conditions?.electrolyte"
        :source="alloy.experimental_conditions?.electrolyte?.source"
      />

      <!-- Test Setup -->
      <ConditionItem
        title="Test Setup"
        icon="ph-gear"
        icon-color="text-sky-500"
        :data="alloy.experimental_conditions?.test_setup"
        :source="alloy.experimental_conditions?.test_setup?.source"
      />

      <!-- Synthesis -->
      <ConditionItem
        title="Synthesis"
        icon="ph-flask"
        icon-color="text-emerald-500"
        :data="alloy.experimental_conditions?.synthesis_method"
        :source="alloy.experimental_conditions?.synthesis_method?.source"
      />

      <!-- Other Params -->
      <div class="border border-slate-200 rounded-lg p-4">
        <div class="text-xs font-semibold text-slate-500 uppercase mb-2 flex items-center gap-1">
          <i class="ph ph-list-bullets text-purple-500"></i> Other Params
        </div>
        <div v-if="(alloy.experimental_conditions?.other_environmental_params || []).length === 0" class="text-sm text-slate-400">
          None
        </div>
        <div v-else class="space-y-2">
          <div 
            v-for="(param, i) in alloy.experimental_conditions?.other_environmental_params || []" 
            :key="i" 
            class="p-2 rounded border border-slate-200 bg-slate-50"
          >
            <div class="text-sm font-semibold text-slate-800">{{ param.key || '—' }}</div>
            <div class="text-sm text-slate-700">{{ param.value || '—' }}</div>
            <SourceInline :source="param.source" :highlight-values="[param.key, param.value].filter(v => v)" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import ConditionItem from './ConditionItem.vue'
import SourceInline from './SourceInline.vue'

defineProps({
  alloy: {
    type: Object,
    required: true
  }
})
</script>

