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
          <h3 class="text-sm sm:text-lg font-bold text-slate-800 truncate pr-2">图片来源</h3>
          <button 
            @click="close" 
            class="text-slate-400 hover:text-slate-600 p-1 rounded-full hover:bg-slate-100 transition-colors flex-shrink-0"
            aria-label="关闭"
          >
            <i class="ph ph-x text-base sm:text-xl"></i>
          </button>
        </div>

        <!-- 内容区域 -->
        <div class="p-3 sm:p-6 overflow-y-auto flex-1 min-h-0 space-y-2 sm:space-y-4">
          <div v-if="figureSource.location" class="bg-slate-50 border border-slate-200 rounded-lg p-2 sm:p-3">
            <div class="text-xs text-slate-500 uppercase tracking-wide mb-1">Caption</div>
            <div class="text-xs sm:text-sm font-mono text-slate-800 break-words">{{ figureSource.location }}</div>
          </div>
          
          <div v-if="figureRefs.length" class="bg-slate-50 border border-slate-200 rounded-lg p-2 sm:p-3">
            <div class="text-xs text-slate-500 uppercase tracking-wide mb-2">文本内容</div>
              <ul class="space-y-1.5 sm:space-y-2">
                <li 
                  v-for="(r, i) in figureRefs" 
                  :key="i" 
                  class="bg-white border border-slate-200 rounded px-2 sm:px-3 py-1.5 sm:py-2 text-xs sm:text-sm text-slate-700 latex-content break-words"
                  v-html="getHighlightedText(r)"
                ></li>
              </ul>
          </div>
          
          <div v-if="figureSource.img_path" class="bg-white border border-slate-200 rounded-lg p-2 sm:p-3">
            <div class="text-xs text-slate-500 uppercase tracking-wide mb-2">图片</div>
            <div class="border border-slate-200 rounded-lg overflow-hidden bg-slate-50 p-1 sm:p-2">
              <img 
                :src="imageUrl" 
                alt="Extracted Figure" 
                class="max-w-full h-auto object-contain max-h-[250px] sm:max-h-[500px] mx-auto rounded"
                @error="(e) => e.target.style.display = 'none'"
              >
              <div class="text-xs text-slate-400 font-mono mt-1 sm:mt-2 text-center break-all px-1 sm:px-2 select-all">
                {{ figureSource.img_path }}
              </div>
            </div>
          </div>
        </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, watch, nextTick } from 'vue'
import { getFigureRefs } from '../utils/source'
import { renderLatex, renderLatexInElement, renderLatexWithHighlight } from '../utils/latex'
import { paperApi } from '../utils/api'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  figureSource: {
    type: Object,
    default: null
  },
  highlightValues: {
    type: [String, Number, Array, Object],
    default: null
  }
})

const emit = defineEmits(['close'])

const figureRefs = computed(() => getFigureRefs(props.figureSource))
const imageUrl = computed(() => {
  if (props.figureSource?.img_path) {
    return paperApi.getImageUrl(props.figureSource.img_path)
  }
  return ''
})

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

