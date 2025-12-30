<template>
  <div v-if="figureSource" ref="containerRef" class="mt-3 space-y-2">
    <div class="text-xs font-semibold text-slate-500 uppercase mb-2">图片来源</div>
    
    <div class="space-y-2">
      <div v-if="figureSource.location" class="bg-slate-50 border border-slate-200 rounded-lg p-2">
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-1">Caption</div>
        <div class="text-xs font-mono text-slate-800 break-words">{{ figureSource.location }}</div>
      </div>
      
      <div v-if="figureRefs.length" class="bg-slate-50 border border-slate-200 rounded-lg p-2">
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-2">文本内容</div>
        <ul class="space-y-1.5">
          <li 
            v-for="(r, i) in figureRefs" 
            :key="i" 
            class="bg-white border border-slate-200 rounded px-2 py-1.5 text-xs text-slate-700 latex-content break-words"
            v-html="getHighlightedText(r)"
          ></li>
        </ul>
      </div>
      
      <div v-if="figureSource.img_path" class="bg-white border border-slate-200 rounded-lg p-2">
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-2">图片</div>
        <div class="border border-slate-200 rounded-lg overflow-hidden bg-slate-50 p-1">
          <img 
            :src="imageUrl" 
            alt="Extracted Figure" 
            class="max-w-full h-auto object-contain max-h-[250px] mx-auto rounded"
            @error="(e) => e.target.style.display = 'none'"
          >
          <div class="text-xs text-slate-400 font-mono mt-1 text-center break-all px-1 select-all">
            {{ figureSource.img_path }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, nextTick, ref } from 'vue'
import { getFigureRefs } from '../utils/source'
import { renderLatex, renderLatexInElement, renderLatexWithHighlight } from '../utils/latex'
import { paperApi } from '../utils/api'

const props = defineProps({
  figureSource: {
    type: Object,
    default: null
  },
  highlightValues: {
    type: [String, Number, Array, Object],
    default: null
  }
})

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

