<template>
  <div v-if="hasSource" ref="containerRef" class="mt-3 space-y-2">
    <div class="text-xs font-semibold text-slate-500 uppercase mb-2">来源信息</div>
    
    <!-- Table Source -->
    <div v-if="isTable" class="space-y-2">
      <div v-if="tableLocation" class="bg-slate-50 border border-slate-200 rounded-lg p-2">
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-1">位置</div>
        <div class="text-xs font-mono text-slate-800 break-words">{{ tableLocation }}</div>
      </div>
      
      <div v-if="tableRefs.length" class="bg-slate-50 border border-slate-200 rounded-lg p-2">
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-2">文本内容</div>
        <ul class="space-y-1.5">
          <li 
            v-for="(r, i) in tableRefs" 
            :key="i" 
            class="bg-white border border-slate-200 rounded px-2 py-1.5 text-xs text-slate-700 latex-content break-words"
            v-html="getHighlightedText(r)"
          ></li>
        </ul>
      </div>
      
      <div v-if="tableHtml" class="bg-white border border-slate-200 rounded-lg p-2">
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-2">表格内容</div>
        <div class="overflow-x-auto raw-html-table" v-html="highlightedTableHtml"></div>
      </div>
    </div>
    
    <!-- Text Source -->
    <div v-else class="space-y-1.5">
      <div 
        v-for="(s, i) in normalizedSource" 
        :key="i" 
        class="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-xs text-slate-700 latex-content break-words"
        v-html="getHighlightedText(s)"
      ></div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch, nextTick, onMounted, ref } from 'vue'
import {
  normalizeSource,
  isTableSource,
  getTableRefs,
  getTableLocation,
  getTableHtml,
  hasAnySource
} from '../utils/source'
import { renderLatex, renderLatexInElement, renderLatexWithHighlight } from '../utils/latex'

const props = defineProps({
  source: {
    type: [Array, Object],
    default: null
  },
  // 用于高亮的指标值（可以是字符串、数组或对象）
  highlightValues: {
    type: [String, Number, Array, Object],
    default: null
  }
})

const hasSource = computed(() => hasAnySource(props.source))
const isTable = computed(() => isTableSource(props.source))
const normalizedSource = computed(() => normalizeSource(props.source))
const tableRefs = computed(() => getTableRefs(props.source))
const tableLocation = computed(() => getTableLocation(props.source))
const tableHtml = computed(() => getTableHtml(props.source))

// 提取要高亮的值
const extractHighlightValues = () => {
  if (!props.highlightValues) return null
  
  if (typeof props.highlightValues === 'string' || typeof props.highlightValues === 'number') {
    return [String(props.highlightValues)]
  }
  
  if (Array.isArray(props.highlightValues)) {
    return props.highlightValues.map(v => String(v)).filter(v => v && v !== '—' && v !== 'null')
  }
  
  if (typeof props.highlightValues === 'object') {
    const values = []
    for (const key in props.highlightValues) {
      const val = props.highlightValues[key]
      if (val !== null && val !== undefined && val !== '' && val !== '—') {
        values.push(String(val))
      }
    }
    return values.length > 0 ? values : null
  }
  
  return null
}

// 表格高亮函数
const highlightFullTableSimple = (htmlContent, targetValues) => {
  if (!targetValues || !htmlContent) {
    return htmlContent || ''
  }
  
  let highlighted = htmlContent
  const values = Array.isArray(targetValues) ? targetValues : [targetValues]
  
  values.forEach(targetValue => {
    if (!targetValue) return
    
    // 转义特殊字符
    const escapedTarget = String(targetValue).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    // 创建全局匹配正则
    const regex = new RegExp(escapedTarget, 'g')
    // 定义高亮模板（红底白字）
    const highlightTemplate = `<span style="background-color: #ff0000; color: white; font-weight: bold; padding: 0 2px;">$&</span>`
    // 全局替换
    highlighted = highlighted.replace(regex, highlightTemplate)
  })
  
  return highlighted
}

// 获取高亮后的表格 HTML
const highlightedTableHtml = computed(() => {
  if (!tableHtml.value) return ''
  const values = extractHighlightValues()
  if (!values) return tableHtml.value
  return highlightFullTableSimple(tableHtml.value, values)
})

// 获取高亮后的文本
const getHighlightedText = (text) => {
  if (!text) return ''
  const values = extractHighlightValues()
  if (!values) {
    return renderLatex(text)
  }
  return renderLatexWithHighlight(text, values)
}

// 渲染 LaTeX
const containerRef = ref(null)

onMounted(() => {
  nextTick(() => {
    if (containerRef.value) {
      const elements = containerRef.value.querySelectorAll('.latex-content')
      elements.forEach(el => {
        renderLatexInElement(el)
      })
    }
  })
})
</script>

