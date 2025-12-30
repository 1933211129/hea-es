<template>
  <div class="bg-white rounded-xl border border-slate-200 shadow-sm mb-6 overflow-hidden" :data-alloy-index="index">
    <div class="px-4 py-3 bg-slate-50 border-b border-slate-100">
      <div class="flex items-center justify-between mb-2">
        <div class="flex items-center gap-3 flex-wrap">
          <span class="font-mono text-sm px-2 py-1 rounded bg-indigo-50 text-indigo-700 border border-indigo-100">合金ID</span>
          <span class="text-lg font-bold text-slate-900">{{ alloy.alloy_id || 'Unknown Alloy' }}</span>
          <div class="flex items-center gap-2">
            <span 
              v-if="evidenceSummary.text > 0"
              class="px-2 py-1 rounded-full text-xs font-semibold"
              :class="evidenceBadgeClass('text')"
            >
              Text {{ evidenceSummary.text }}
            </span>
            <span 
              v-if="evidenceSummary.table > 0"
              class="px-2 py-1 rounded-full text-xs font-semibold"
              :class="evidenceBadgeClass('table')"
            >
              Table {{ evidenceSummary.table }}
            </span>
            <span 
              v-if="evidenceSummary.figure > 0"
              class="px-2 py-1 rounded-full text-xs font-semibold"
              :class="evidenceBadgeClass('figure')"
            >
              Figure {{ evidenceSummary.figure }}
            </span>
          </div>
        </div>
        <div class="text-xs text-slate-500">#{{ index + 1 }}</div>
      </div>
      
      <!-- 合金详细信息 -->
      <div v-if="alloy.alloy_details" class="mt-2 pt-2 border-t border-slate-200">
        <div class="space-y-1.5 text-sm">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div v-if="alloy.alloy_details.type" class="flex items-start">
              <span class="text-slate-500 font-medium min-w-[80px]">类型:</span>
              <span class="ml-2 text-slate-800 break-words">{{ alloy.alloy_details.type }}</span>
            </div>
            <div v-if="alloy.alloy_details.composition" class="flex items-start">
              <span class="text-slate-500 font-medium min-w-[100px]">成分:</span>
              <span class="ml-2 text-slate-800 font-mono break-all">{{ alloy.alloy_details.composition }}</span>
            </div>
            <div v-if="alloy.alloy_details.precursor_id" class="flex items-start">
              <span class="text-slate-500 font-medium min-w-[110px]">前驱体ID:</span>
              <span class="ml-2 text-slate-800 font-mono break-all">{{ alloy.alloy_details.precursor_id }}</span>
            </div>
          </div>
          <div v-if="alloy.alloy_details.aliases && alloy.alloy_details.aliases.length > 0" class="flex items-start">
            <span class="text-slate-500 font-medium min-w-[80px]">文中别名:</span>
            <div class="ml-2 flex flex-wrap gap-1 flex-1">
              <span 
                v-for="(alias, i) in alloy.alloy_details.aliases" 
                :key="i"
                class="px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-xs"
              >
                {{ alias }}
              </span>
            </div>
          </div>
          <div v-if="alloy.alloy_details.evidence_source && alloy.alloy_details.evidence_source.length > 0" class="flex items-start">
            <span class="text-slate-500 font-medium min-w-[80px]">来源:</span>
            <div class="ml-2 flex-1">
              <details class="text-xs" @toggle="handleDetailsToggle">
                <summary class="cursor-pointer text-indigo-600 hover:underline">
                  Evidence Source ({{ alloy.alloy_details.evidence_source.length }})
                </summary>
                <div class="mt-2 space-y-2">
                  <div 
                    v-for="(evidence, i) in alloy.alloy_details.evidence_source" 
                    :key="i"
                    class="bg-slate-50 border border-slate-200 rounded px-3 py-2 text-slate-700 latex-content"
                    v-html="renderLatex(evidence)"
                  ></div>
                </div>
              </details>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="p-4">
      <!-- 整合展示：条件 + 性能 -->
      <div class="space-y-2">
        <!-- 实验条件摘要 -->
        <div class="bg-slate-50 border border-slate-200 rounded-lg p-3">
          <div class="text-xs font-semibold text-slate-500 uppercase mb-2 flex items-center gap-2">
            <i class="ph ph-flask text-indigo-500"></i> 实验条件
          </div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
            <div>
              <div class="text-slate-500 text-xs mb-1">Electrolyte</div>
              <div class="text-slate-800 font-medium cursor-pointer hover:text-indigo-600 transition-colors" 
                   @click="openSourceModal(alloy.experimental_conditions?.electrolyte?.source, [alloy.experimental_conditions?.electrolyte?.electrolyte_composition, alloy.experimental_conditions?.electrolyte?.concentration_molar, alloy.experimental_conditions?.electrolyte?.ph_value].filter(v => v))">
                {{ alloy.experimental_conditions?.electrolyte?.electrolyte_composition || '—' }}
              </div>
              <div class="text-slate-600 text-xs mt-0.5">
                {{ alloy.experimental_conditions?.electrolyte?.concentration_molar || '' }}
                <span v-if="alloy.experimental_conditions?.electrolyte?.ph_value">
                  (pH {{ alloy.experimental_conditions?.electrolyte?.ph_value }})
                </span>
              </div>
            </div>
            <div>
              <div class="text-slate-500 text-xs mb-1">Substrate</div>
              <div class="text-slate-800 font-medium cursor-pointer hover:text-indigo-600 transition-colors"
                   @click="openSourceModal(alloy.experimental_conditions?.test_setup?.source, [alloy.experimental_conditions?.test_setup?.substrate, alloy.experimental_conditions?.test_setup?.scan_rate, alloy.experimental_conditions?.test_setup?.ir_compensation].filter(v => v))">
                {{ alloy.experimental_conditions?.test_setup?.substrate || '—' }}
              </div>
              <div class="text-slate-600 text-xs mt-0.5">
                {{ alloy.experimental_conditions?.test_setup?.scan_rate || '' }}
              </div>
            </div>
            <div>
              <div class="text-slate-500 text-xs mb-1">Synthesis</div>
              <div class="text-slate-800 font-medium text-xs cursor-pointer hover:text-indigo-600 transition-colors"
                   @click="openSourceModal(alloy.experimental_conditions?.synthesis_method?.source, [alloy.experimental_conditions?.synthesis_method?.method, alloy.experimental_conditions?.synthesis_method?.key_parameters].filter(v => v))">
                {{ alloy.experimental_conditions?.synthesis_method?.method || '—' }}
              </div>
            </div>
            <div>
              <div class="text-slate-500 text-xs mb-1">Other Params</div>
              <div v-if="(alloy.experimental_conditions?.other_environmental_params || []).length === 0" class="text-sm text-slate-400">
                —
              </div>
              <div v-else class="space-y-1">
                <div 
                  v-for="(param, i) in alloy.experimental_conditions?.other_environmental_params || []" 
                  :key="i"
                  class="text-xs cursor-pointer hover:text-indigo-600 transition-colors"
                  @click="openSourceModal(param.source, [param.key, param.value].filter(v => v))"
                >
                  <span class="text-slate-600">{{ param.key }}:</span>
                  <span class="text-slate-800 font-medium ml-1">{{ param.value }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 性能指标表格 -->
        <div class="border border-slate-200 rounded-lg overflow-hidden">
          <div class="bg-slate-50 border-b border-slate-200 px-3 py-1.5">
            <div class="text-xs font-semibold text-slate-600 flex items-center gap-2">
              <i class="ph ph-lightning text-indigo-500"></i> 实验性能
            </div>
          </div>
          <div class="p-3">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              <!-- Overpotential -->
              <div class="border-l-2 border-amber-400 pl-3">
                <div class="text-xs text-slate-500 mb-1">Overpotential</div>
                <div v-if="(alloy.performance?.overpotential || []).length === 0" class="text-sm text-slate-400">
                  —
                </div>
                <div v-else class="space-y-1">
                  <div 
                    v-for="(op, i) in alloy.performance?.overpotential || []" 
                    :key="i"
                    class="text-sm font-semibold text-slate-800 cursor-pointer hover:text-indigo-600 transition-colors"
                    @click="openSourceModal(op.source, [op.value, op.current_density].filter(v => v))"
                  >
                    {{ op.value || '—' }} {{ op.unit || '' }}
                    <span v-if="op.current_density" class="text-xs text-slate-500 font-normal">
                      @ {{ op.current_density }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- Tafel Slope -->
              <div class="border-l-2 border-emerald-400 pl-3">
                <div class="text-xs text-slate-500 mb-1">Tafel Slope</div>
                <div v-if="alloy.performance?.tafel_slope === null" class="text-sm text-slate-400">
                  —
                </div>
                <div v-else 
                     class="text-sm font-semibold text-slate-800 cursor-pointer hover:text-indigo-600 transition-colors"
                     @click="openSourceModal(alloy.performance?.tafel_slope?.source, alloy.performance?.tafel_slope?.value)">
                  {{ alloy.performance?.tafel_slope?.value || '—' }} {{ alloy.performance?.tafel_slope?.unit || '' }}
                </div>
              </div>

              <!-- Stability -->
              <div class="border-l-2 border-rose-400 pl-3">
                <div class="text-xs text-slate-500 mb-1">Stability</div>
                <div class="text-sm space-y-0.5">
                  <div v-if="alloy.performance?.stability?.cycle_count" 
                       class="text-slate-800 cursor-pointer hover:text-indigo-600 transition-colors"
                       @click="openSourceModal(alloy.performance?.stability?.source, {
                         cycle_count: alloy.performance?.stability?.cycle_count,
                         duration_hours: alloy.performance?.stability?.duration_hours,
                         test_method: alloy.performance?.stability?.test_method,
                         degradation_details: alloy.performance?.stability?.degradation_details,
                         performance_retention: alloy.performance?.stability?.performance_retention
                       })">
                    <span class="font-medium">{{ alloy.performance.stability.cycle_count }}</span> cycles
                  </div>
                  <div v-else-if="alloy.performance?.stability?.duration_hours" 
                       class="text-slate-800 cursor-pointer hover:text-indigo-600 transition-colors"
                       @click="openSourceModal(alloy.performance?.stability?.source, {
                         cycle_count: alloy.performance?.stability?.cycle_count,
                         duration_hours: alloy.performance?.stability?.duration_hours,
                         test_method: alloy.performance?.stability?.test_method,
                         degradation_details: alloy.performance?.stability?.degradation_details,
                         performance_retention: alloy.performance?.stability?.performance_retention
                       })">
                    <span class="font-medium">{{ alloy.performance.stability.duration_hours }}</span> h
                  </div>
                  <div v-if="alloy.performance?.stability?.test_method && alloy.performance.stability.test_method !== 'Unknown'" class="text-slate-600 text-xs">
                    {{ alloy.performance.stability.test_method }}
                  </div>
                  <div v-if="!alloy.performance?.stability?.cycle_count && !alloy.performance?.stability?.duration_hours" class="text-slate-400">
                    —
                  </div>
                </div>
              </div>

              <!-- Supplementary -->
              <div class="border-l-2 border-blue-400 pl-3">
                <div class="text-xs text-slate-500 mb-1">Supplementary</div>
                <div v-if="(alloy.performance?.supplementary_performance || []).length === 0" class="text-sm text-slate-400">
                  —
                </div>
                <div v-else class="space-y-1">
                  <div 
                    v-for="(sp, i) in alloy.performance?.supplementary_performance || []" 
                    :key="i"
                    class="text-xs cursor-pointer hover:text-indigo-600 transition-colors"
                    @click="openSourceModal(sp.source, [sp.key, sp.value].filter(v => v))"
                  >
                    <span class="text-slate-600">{{ sp.key }}:</span>
                    <span class="text-slate-800 font-medium ml-1">{{ sp.value }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 详细信息（可展开） -->
        <details class="border border-slate-200 rounded-lg">
          <summary class="cursor-pointer px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-sm font-medium text-slate-700 flex items-center gap-2">
            <i class="ph ph-caret-down text-xs"></i>
            <span>查看详细信息</span>
          </summary>
          <div class="p-3 grid grid-cols-1 lg:grid-cols-2 gap-4 border-t border-slate-200">
            <ExperimentalConditions :alloy="alloy" />
            <PerformanceMetrics :alloy="alloy" />
          </div>
        </details>
      </div>
    </div>
    
    <!-- 来源弹窗 -->
    <SourceModal
      :show="showSourceModal"
      :source="currentSource"
      :highlight-values="currentHighlightValues"
      @close="closeSourceModal"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import ExperimentalConditions from './ExperimentalConditions.vue'
import PerformanceMetrics from './PerformanceMetrics.vue'
import SourceModal from './SourceModal.vue'
import { getEvidenceSummary, hasAnySource } from '../utils/source'
import { renderLatex, renderLatexInElement } from '../utils/latex'

const props = defineProps({
  alloy: {
    type: Object,
    required: true
  },
  index: {
    type: Number,
    required: true
  }
})

const evidenceSummary = computed(() => getEvidenceSummary(props.alloy))

// 来源弹窗状态
const showSourceModal = ref(false)
const currentSource = ref(null)
const currentHighlightValues = ref(null)

const evidenceBadgeClass = (type) => {
  const map = {
    text: 'bg-emerald-50 text-emerald-700 border border-emerald-100',
    table: 'bg-sky-50 text-sky-700 border border-sky-100',
    figure: 'bg-amber-50 text-amber-700 border border-amber-100'
  }
  return map[type] || 'bg-slate-100 text-slate-600'
}

// 打开来源弹窗
const openSourceModal = (source, highlightValues) => {
  if (!hasAnySource(source)) {
    return // 如果没有来源，不打开弹窗
  }
  currentSource.value = source
  currentHighlightValues.value = highlightValues
  showSourceModal.value = true
}

// 关闭来源弹窗
const closeSourceModal = () => {
  showSourceModal.value = false
  currentSource.value = null
  currentHighlightValues.value = null
}

// 渲染 LaTeX（在 details 展开时调用）
const renderLatexInDetails = () => {
  nextTick(() => {
    // 只渲染当前组件内的 LaTeX 内容
    const cardElement = document.querySelector(`[data-alloy-index="${props.index}"]`)
    if (cardElement) {
      const elements = cardElement.querySelectorAll('.latex-content')
      elements.forEach(el => {
        renderLatexInElement(el)
      })
    }
  })
}

// 监听 details 展开事件
const handleDetailsToggle = (event) => {
  if (event.target.open) {
    renderLatexInDetails()
  }
}
</script>

