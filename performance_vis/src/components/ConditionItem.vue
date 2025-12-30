<template>
  <div class="border border-slate-200 rounded-lg p-4">
    <div class="text-xs font-semibold text-slate-500 uppercase mb-2 flex items-center gap-1">
      <i :class="`ph ${icon} ${iconColor}`"></i> {{ title }}
    </div>
    <div class="text-sm text-slate-800 space-y-1">
      <template v-if="title === 'Electrolyte'">
        <div>Composition: {{ data?.electrolyte_composition || '—' }}</div>
        <div>Concentration: {{ data?.concentration_molar || '—' }}</div>
        <div>pH: {{ data?.ph_value ?? '—' }}</div>
      </template>
      <template v-else-if="title === 'Test Setup'">
        <div>Substrate: {{ data?.substrate || '—' }}</div>
        <div>Scan Rate: {{ data?.scan_rate || '—' }}</div>
        <div>IR Compensation: {{ data?.ir_compensation ?? '—' }}</div>
      </template>
      <template v-else-if="title === 'Synthesis'">
        <div>Method: {{ data?.method || '—' }}</div>
        <div>Key Params: {{ data?.key_parameters || '—' }}</div>
      </template>
    </div>
    <SourceInline :source="source" :highlight-values="getHighlightValues()" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import SourceInline from './SourceInline.vue'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  icon: {
    type: String,
    required: true
  },
  iconColor: {
    type: String,
    required: true
  },
  data: {
    type: Object,
    default: null
  },
  source: {
    type: [Array, Object],
    default: null
  }
})

// 根据 title 提取要高亮的值
const getHighlightValues = () => {
  if (!props.data) return null
  
  if (props.title === 'Electrolyte') {
    const values = []
    if (props.data.electrolyte_composition) values.push(props.data.electrolyte_composition)
    if (props.data.concentration_molar) values.push(props.data.concentration_molar)
    if (props.data.ph_value) values.push(props.data.ph_value)
    return values.length > 0 ? values : null
  }
  
  if (props.title === 'Test Setup') {
    const values = []
    if (props.data.substrate) values.push(props.data.substrate)
    if (props.data.scan_rate) values.push(props.data.scan_rate)
    if (props.data.ir_compensation) values.push(props.data.ir_compensation)
    return values.length > 0 ? values : null
  }
  
  if (props.title === 'Synthesis') {
    const values = []
    if (props.data.method) values.push(props.data.method)
    if (props.data.key_parameters) values.push(props.data.key_parameters)
    return values.length > 0 ? values : null
  }
  
  return null
}
</script>

