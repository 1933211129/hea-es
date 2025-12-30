<template>
  <div class="flex-1 overflow-y-auto p-8 relative z-0">
    <!-- 论文头部信息 -->
    <div class="max-w-6xl mx-auto mb-8">
      <div class="flex items-start justify-between gap-4 mb-6">
        <h1 class="text-3xl font-bold text-slate-900 leading-tight tracking-tight flex-1">
          {{ paper.title }}
        </h1>
        <div class="flex items-center gap-2 flex-shrink-0">
          <button
            @click="showFeedbackModal = true"
            class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm hover:shadow-md bg-amber-500 text-white hover:bg-amber-600"
          >
            <i class="ph ph-warning text-base"></i>
            <span>问题反馈</span>
          </button>
          <button
            v-if="pdfUrl || pdfLoading"
            @click="openPdf"
            :disabled="!pdfUrl || pdfLoading"
            class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
            :class="pdfUrl ? 'bg-indigo-600 text-white hover:bg-indigo-700' : 'bg-slate-200 text-slate-500'"
          >
            <i v-if="pdfLoading" class="ph ph-circle-notch animate-spin text-base"></i>
            <i v-else class="ph ph-file-pdf text-base"></i>
            <span>{{ pdfLoading ? 'Loading...' : 'PDF' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 性能数据部分 -->
    <div class="max-w-6xl mx-auto mb-8">
      <div class="flex items-center gap-3 mb-6">
        <i class="ph ph-chart-polar text-2xl text-indigo-600"></i>
        <h2 class="text-xl font-bold text-slate-800">实验数据</h2>
        <div class="h-px bg-slate-200 flex-1"></div>
      </div>

      <div class="pb-10 min-h-[300px]">
        <!-- Loading State -->
        <div v-if="!performanceData" class="flex flex-col items-center justify-center py-10 text-slate-400">
          <i class="ph ph-circle-notch animate-spin text-3xl mb-2 text-indigo-400"></i>
          <p>加载性能数据...</p>
        </div>

        <!-- Alloy cards -->
        <div v-else>
          <div v-if="alloyResults.length === 0" class="bg-white rounded-xl border border-dashed border-slate-200 p-8 text-center text-slate-400">
            没有找到性能数据。
          </div>

          <AlloyCard
            v-for="(alloy, idx) in alloyResults"
            :key="idx"
            :alloy="alloy"
            :index="idx"
          />
        </div>
      </div>
    </div>

    <!-- 研究概览卡片 -->
    <div class="max-w-6xl mx-auto space-y-6 mb-8">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Alloy Elements -->
        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
          <div class="flex items-center gap-2 mb-3 text-slate-400">
            <i class="ph ph-flask text-lg text-indigo-500"></i>
            <span class="text-xs font-semibold uppercase tracking-wider">合金元素</span>
          </div>
          <div v-if="formattedAlloyElements" class="flex flex-wrap gap-2">
            <div 
              v-for="(element, index) in formattedAlloyElements" 
              :key="index"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 border border-indigo-100 hover:bg-indigo-100 transition-colors"
            >
              <span class="font-mono font-semibold text-indigo-700 text-sm">{{ element.symbol }}</span>
              <span v-if="element.ratio !== null && element.ratio !== undefined" class="text-xs text-indigo-500 font-medium">
                {{ element.ratio }}
              </span>
            </div>
          </div>
          <div v-else class="text-slate-400 text-sm">N/A</div>
        </div>

        <!-- Research Topic -->
        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
          <div class="flex items-center gap-2 mb-3 text-slate-400">
            <i class="ph ph-lightbulb text-lg text-amber-500"></i>
            <span class="text-xs font-semibold uppercase tracking-wider">研究主题</span>
          </div>
          <div 
            class="text-slate-700 text-sm leading-relaxed latex-content"
            v-html="renderLatex(paper.topic || 'No topic summary available.')"
          ></div>
        </div>
      </div>

      <!-- Abstract -->
      <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div class="flex items-center justify-between mb-4 cursor-pointer" @click="showAbstract = !showAbstract">
          <div class="flex items-center gap-2 text-slate-400">
            <i class="ph ph-article text-lg text-slate-600"></i>
            <span class="text-xs font-semibold uppercase tracking-wider">摘要</span>
          </div>
          <i class="ph ph-caret-down text-slate-400 transition-transform duration-300" :class="{'rotate-180': showAbstract}"></i>
        </div>
        <transition name="list">
          <div 
            v-if="showAbstract" 
            class="text-slate-600 leading-relaxed text-sm text-justify latex-content"
            v-html="renderLatex(paper.abstract || 'No abstract available.')"
          ></div>
        </transition>
      </div>
    </div>

    <!-- 反馈弹窗 -->
    <FeedbackModal
      :show="showFeedbackModal"
      :identifier="paper.identifier"
      :alloy-ids="alloyIdList"
      @close="showFeedbackModal = false"
      @success="handleFeedbackSuccess"
    />
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted } from 'vue'
import AlloyCard from './AlloyCard.vue'
import FeedbackModal from './FeedbackModal.vue'
import { renderLatex, renderLatexInElement } from '../utils/latex'
import { paperApi } from '../utils/api'

const props = defineProps({
  paper: {
    type: Object,
    required: true
  },
  performanceData: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const showAbstract = ref(true)
const pdfUrl = ref(null)
const pdfLoading = ref(false)
const showFeedbackModal = ref(false)

// 获取 PDF URL
const fetchPdfUrl = async (identifier) => {
  if (!identifier) {
    pdfUrl.value = null
    return
  }
  
  pdfLoading.value = true
  try {
    const url = await paperApi.getPdfUrl(identifier)
    pdfUrl.value = url
  } catch (error) {
    console.warn('Failed to fetch PDF URL:', error)
    pdfUrl.value = null
  } finally {
    pdfLoading.value = false
  }
}

// 初始化时获取 PDF URL
onMounted(async () => {
  if (props.paper?.identifier) {
    await fetchPdfUrl(props.paper.identifier)
  }
})

// 监听 paper 变化，重新获取 PDF URL
watch(() => props.paper?.identifier, async (newIdentifier) => {
  await fetchPdfUrl(newIdentifier)
}, { immediate: false })

// 打开 PDF
const openPdf = () => {
  if (pdfUrl.value) {
    window.open(pdfUrl.value, '_blank')
  }
}

const formattedAlloyElements = computed(() => {
  if (!props.paper || !props.paper.alloy_elements) return null
  
  try {
    let alloyData = props.paper.alloy_elements
    if (typeof alloyData === 'string') {
      alloyData = JSON.parse(alloyData)
    }
    
    if (alloyData && alloyData.elements && Array.isArray(alloyData.elements)) {
      return alloyData.elements.map(el => ({
        symbol: el.symbol || '',
        ratio: el.ratio !== null && el.ratio !== undefined ? String(el.ratio) : null
      }))
    }
    
    return null
  } catch (error) {
    console.error('Error parsing alloy_elements:', error)
    return null
  }
})

const alloyResults = computed(() => {
  if (props.performanceData) {
    if (props.performanceData.extraction_results) {
      return props.performanceData.extraction_results
    }
    if (props.performanceData.merge_result && props.performanceData.merge_result.extraction_results) {
      return props.performanceData.merge_result.extraction_results
    }
  }
  if (props.paper && props.paper.performance && props.paper.performance.extraction_results) {
    return props.paper.performance.extraction_results
  }
  return []
})

// 提取所有 alloy_id 列表
const alloyIdList = computed(() => {
  const alloys = alloyResults.value
  if (!alloys || !Array.isArray(alloys)) return []
  return alloys
    .map(alloy => alloy.alloy_id)
    .filter(id => id && id.trim())
    .filter((id, index, self) => self.indexOf(id) === index) // 去重
    .sort()
})

const handleFeedbackSuccess = () => {
  // 反馈提交成功后的处理
  console.log('Feedback submitted successfully')
}

const renderLatexInElementWrapper = () => {
  nextTick(() => {
    const elements = document.querySelectorAll('.latex-content')
    elements.forEach(el => {
      renderLatexInElement(el)
    })
  })
}

watch(() => props.paper, () => {
  renderLatexInElementWrapper()
}, { immediate: true })

watch(() => showAbstract.value, (val) => {
  if (val) {
    renderLatexInElementWrapper()
  }
})
</script>

<style scoped>
.list-enter-active,
.list-leave-active {
  transition: all 0.3s ease;
}

.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}
</style>

