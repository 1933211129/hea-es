<template>
  <div class="text-slate-800 h-screen overflow-hidden flex" v-cloak>
    <!-- 左侧侧边栏：论文列表 -->
    <PaperList
      :papers="papers"
      :selected-id="selectedId"
      :loading="loadingList"
      @select="selectPaper"
      @search="handleSearch"
    />

    <!-- 右侧主内容区 -->
    <main class="flex-1 bg-slate-50 h-full overflow-hidden flex flex-col relative">
      <!-- 顶部装饰背景 -->
      <div class="absolute top-0 left-0 w-full h-64 bg-gradient-to-b from-indigo-50/50 to-transparent pointer-events-none"></div>

      <PaperDetail
        v-if="selectedPaper"
        :paper="selectedPaper"
        :performance-data="performanceData"
        :loading="loadingDetail"
      />

      <!-- 空状态：未选择论文 -->
      <div v-else class="flex-1 flex flex-col items-center justify-center text-slate-400 h-full">
        <div v-if="loadingDetail" class="flex flex-col items-center">
          <i class="ph ph-circle-notch animate-spin text-4xl text-indigo-500 mb-4"></i>
          <p class="text-slate-500 animate-pulse">加载论文详情...</p>
        </div>
        <div v-else class="text-center p-8 max-w-md">
          <div class="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-6 text-slate-300">
            <i class="ph ph-cursor-click text-4xl"></i>
          </div>
          <h2 class="text-xl font-bold text-slate-700 mb-2">选择文章</h2>
          <p class="text-slate-500">从侧边栏选择文章，查看其详细分析和性能指标。</p>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import PaperList from '../components/PaperList.vue'
import PaperDetail from '../components/PaperDetail.vue'
import { paperApi } from '../utils/api'

const papers = ref([])
const selectedId = ref(null)
const selectedPaper = ref(null)
const performanceData = ref(null)
const loadingList = ref(false)
const loadingDetail = ref(false)

const fetchPapers = async () => {
  loadingList.value = true
  try {
    papers.value = await paperApi.getPapers()
  } catch (error) {
    console.error('Error fetching papers:', error)
    alert('Failed to load papers. Please ensure the backend API is running.')
  } finally {
    loadingList.value = false
  }
}

const handleSearch = async (query) => {
  if (!query.trim()) {
    return fetchPapers()
  }
  
  loadingList.value = true
  try {
    papers.value = await paperApi.searchPapers(query)
  } catch (error) {
    console.error('Error searching papers:', error)
  } finally {
    loadingList.value = false
  }
}

const selectPaper = async (identifier) => {
  if (selectedId.value === identifier) return
  
  selectedId.value = identifier
  selectedPaper.value = null
  performanceData.value = null
  loadingDetail.value = true
  
  try {
    const [detailRes, perfRes] = await Promise.all([
      paperApi.getPaperDetail(identifier),
      paperApi.getPaperPerformance(identifier)
    ])
    
    selectedPaper.value = detailRes
    const perf = perfRes
    performanceData.value = (perf && typeof perf === 'object' && perf.merge_result !== undefined)
      ? (perf.merge_result || {})
      : (perf || {})
  } catch (error) {
    console.error('Error fetching paper detail:', error)
    alert('Failed to load paper details.')
  } finally {
    loadingDetail.value = false
  }
}

onMounted(() => {
  fetchPapers()
})
</script>

<style scoped>
[v-cloak] {
  display: none;
}
</style>

