<template>
  <Teleport to="body">
    <transition name="modal">
      <div v-if="show" class="fixed inset-0 z-[9999] flex items-start sm:items-center justify-center p-2 sm:p-4 overflow-y-auto" @click.self="close" style="min-height: 100vh;">
        <!-- 背景遮罩 -->
        <div class="fixed inset-0 bg-black/50 backdrop-blur-sm"></div>
        
        <!-- 弹窗内容 -->
        <div class="bg-white rounded-lg sm:rounded-xl shadow-2xl w-full max-w-[calc(100vw-1rem)] sm:max-w-4xl max-h-[calc(100vh-1rem)] sm:max-h-[85vh] flex flex-col relative z-10 my-2 sm:my-0">
          <!-- 头部 -->
        <div class="p-3 sm:p-4 border-b border-slate-200 flex justify-between items-center bg-slate-50 rounded-t-lg sm:rounded-t-xl flex-shrink-0">
          <h3 class="text-sm sm:text-lg font-bold text-slate-800 truncate pr-2">来源信息</h3>
          <button 
            @click="close" 
            class="text-slate-400 hover:text-slate-600 p-1 rounded-full hover:bg-slate-100 transition-colors flex-shrink-0"
            aria-label="关闭"
          >
            <i class="ph ph-x text-base sm:text-xl"></i>
          </button>
        </div>

        <!-- 内容区域 -->
        <div class="p-3 sm:p-6 overflow-y-auto flex-1 min-h-0">
          <!-- Table Source -->
          <div v-if="isTable" class="space-y-2 sm:space-y-4">
            <div v-if="tableLocation" class="bg-slate-50 border border-slate-200 rounded-lg p-2 sm:p-3">
              <div class="text-xs text-slate-500 uppercase tracking-wide mb-1">位置</div>
              <div class="text-xs sm:text-sm font-mono text-slate-800 break-words">{{ tableLocation }}</div>
            </div>
            
            <div v-if="tableRefs.length" class="bg-slate-50 border border-slate-200 rounded-lg p-2 sm:p-3">
              <div class="text-xs text-slate-500 uppercase tracking-wide mb-2">文本内容</div>
              <ul class="space-y-1.5 sm:space-y-2">
                <li 
                  v-for="(r, i) in tableRefs" 
                  :key="i" 
                  class="bg-white border border-slate-200 rounded px-2 sm:px-3 py-1.5 sm:py-2 text-xs sm:text-sm text-slate-700 latex-content break-words"
                  v-html="getHighlightedText(r)"
                ></li>
              </ul>
            </div>
            
            <div v-if="tableHtml" class="bg-white border border-slate-200 rounded-lg p-2 sm:p-3">
              <div class="text-xs text-slate-500 uppercase tracking-wide mb-2">表格内容</div>
              <div class="overflow-x-auto raw-html-table" v-html="highlightedTableHtml"></div>
            </div>
          </div>
          
          <!-- Text Source -->
          <div v-else class="space-y-1.5 sm:space-y-3">
            <div 
              v-for="(s, i) in normalizedSource" 
              :key="i" 
              class="bg-slate-50 border border-slate-200 rounded-lg px-2 sm:px-4 py-1.5 sm:py-3 text-xs sm:text-sm text-slate-700 latex-content break-words"
              v-html="getHighlightedText(s)"
            ></div>
          </div>
        </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, watch, nextTick } from 'vue'
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
  show: {
    type: Boolean,
    default: false
  },
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

const emit = defineEmits(['close'])

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

// 表格高亮函数（参考表格字符匹配.html）
const highlightFullTableSimple = (htmlContent, targetValues) => {
  if (!targetValues || !htmlContent) {
    return htmlContent || ''
  }
  
  let highlighted = htmlContent
  const values = Array.isArray(targetValues) ? targetValues : [targetValues]
  
  values.forEach(targetValue => {
    if (!targetValue) return
    
    // 转义特殊字符（类似 re.escape）
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

const close = () => {
  emit('close')
}

// 当弹窗打开时渲染 LaTeX
watch(() => props.show, (newVal) => {
  if (newVal) {
    nextTick(() => {
      const modalElement = document.querySelector('.fixed.inset-0.z-\\[9999\\]')
      if (modalElement) {
        const elements = modalElement.querySelectorAll('.latex-content')
        elements.forEach(el => {
          renderLatexInElement(el)
        })
      }
    })
  }
})
</script>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>

