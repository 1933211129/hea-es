<template>
  <div class="text-slate-800 h-screen overflow-hidden flex flex-col" v-cloak>
    <!-- 顶部导航栏 -->
    <div class="bg-white border-b border-slate-200 shadow-sm flex-shrink-0">
      <div class="max-w-7xl mx-auto px-6 py-4 flex items-center gap-4">
        <button
          @click="goBack"
          class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-100 transition-colors"
        >
          <i class="ph ph-arrow-left text-base"></i>
          <span>返回抽取历史</span>
        </button>
        <div class="h-6 w-px bg-slate-200"></div>
        <h1 class="text-lg font-bold text-slate-800">新建抽取任务</h1>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="flex-1 bg-slate-50 overflow-y-auto">
      <div class="max-w-4xl mx-auto px-6 py-12">
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-12">
          <div class="text-center">
            <div class="w-24 h-24 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <i class="ph ph-wrench text-4xl text-indigo-600"></i>
            </div>
            <h2 class="text-2xl font-bold text-slate-800 mb-3">待开发</h2>
            <p class="text-slate-600 text-lg">...</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const goBack = () => {
  router.push('/')
}
</script>

<style scoped>
[v-cloak] {
  display: none;
}
</style>

