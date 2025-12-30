<template>
  <aside class="w-96 bg-white border-r border-slate-200 flex flex-col h-full shadow-lg z-10 flex-shrink-0">
    <!-- 侧边栏头部 -->
    <div class="p-5 border-b border-slate-100">
      <div class="flex items-center justify-between gap-3 mb-4">
        <h1 class="font-bold text-lg tracking-tight text-slate-800">性能抽取展示</h1>
        <button
          @click="goToNewTask"
          class="flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition-colors shadow-sm hover:shadow-md"
          title="新建抽取任务"
        >
          <i class="ph ph-plus text-base"></i>
        </button>
      </div>
      
      <!-- 搜索框 -->
      <div class="relative group">
        <i class="ph ph-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-indigo-500 transition-colors"></i>
        <input 
          type="text" 
          :value="searchQuery"
          @input="handleInput"
          placeholder="搜索论文标题..." 
          class="w-full pl-9 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all placeholder:text-slate-400"
        >
        <div v-if="loading" class="absolute right-3 top-1/2 -translate-y-1/2">
          <i class="ph ph-spinner animate-spin text-indigo-500"></i>
        </div>
      </div>
    </div>

    <!-- 列表区域 -->
    <div class="flex-1 overflow-y-auto p-3 space-y-1">
      <div v-if="papers.length === 0 && !loading" class="text-center py-10 text-slate-400">
        <i class="ph ph-files text-3xl mb-2"></i>
        <p class="text-sm">No papers found</p>
      </div>

      <div 
        v-for="paper in papers" 
        :key="paper.identifier"
        @click="$emit('select', paper.identifier)"
        class="group p-3 rounded-lg cursor-pointer transition-all duration-200 border border-transparent hover:bg-slate-50"
        :class="{'bg-indigo-50 border-indigo-100 shadow-sm ring-1 ring-indigo-200': selectedId === paper.identifier}"
      >
        <div class="flex justify-between items-start gap-2 mb-1">
          <span 
            class="font-mono text-xs px-1.5 py-0.5 rounded text-slate-500 bg-slate-100 group-hover:bg-white transition-colors"
            :class="{'bg-indigo-100 text-indigo-700 font-medium': selectedId === paper.identifier}"
          >
            {{ paper.identifier }}
          </span>
          <i v-if="selectedId === paper.identifier" class="ph ph-caret-right text-indigo-500"></i>
        </div>
        <h3 
          class="text-sm font-medium text-slate-700 leading-snug line-clamp-2 group-hover:text-indigo-600 transition-colors"
          :class="{'text-indigo-900': selectedId === paper.identifier}"
        >
          {{ paper.title || 'Untitled Paper' }}
        </h3>
      </div>
    </div>
    
    <!-- 底部状态栏 -->
    <div class="p-3 border-t border-slate-100 text-xs text-slate-400 flex justify-between items-center bg-slate-50">
      <span>{{ papers.length }} 篇论文加载完成</span>
      <div class="flex items-center gap-1.5">
        <div class="w-2 h-2 rounded-full bg-emerald-500"></div>
        <span>API 连接成功</span>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  papers: {
    type: Array,
    default: () => []
  },
  selectedId: {
    type: String,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['select', 'search'])

const router = useRouter()
const searchQuery = ref('')
let searchTimeout = null

const handleInput = (e) => {
  searchQuery.value = e.target.value
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    emit('search', searchQuery.value)
  }, 500)
}

const goToNewTask = () => {
  router.push('/new-task')
}
</script>

