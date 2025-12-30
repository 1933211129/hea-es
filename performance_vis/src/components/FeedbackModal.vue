<template>
  <Teleport to="body">
    <transition name="modal">
      <div v-if="show" class="fixed inset-0 z-[9999] flex items-center justify-center p-2 sm:p-4 overflow-y-auto" @click.self="close" style="min-height: 100vh;">
        <!-- 背景遮罩 -->
        <div class="fixed inset-0 bg-black/50 backdrop-blur-sm"></div>
        
        <!-- 弹窗内容 -->
        <div class="bg-white rounded-lg sm:rounded-xl shadow-2xl w-full max-w-[calc(100vw-1rem)] sm:max-w-2xl max-h-[calc(100vh-1rem)] sm:max-h-[90vh] flex flex-col relative z-10 my-2 sm:my-0">
          <!-- 头部 -->
          <div class="p-4 border-b border-slate-200 flex justify-between items-center bg-slate-50 rounded-t-lg sm:rounded-t-xl flex-shrink-0">
            <h3 class="text-lg font-bold text-slate-800">问题反馈</h3>
            <button 
              @click="close" 
              class="text-slate-400 hover:text-slate-600 p-1 rounded-full hover:bg-slate-100 transition-colors flex-shrink-0"
              aria-label="关闭"
            >
              <i class="ph ph-x text-xl"></i>
            </button>
          </div>

          <!-- 表单内容 -->
          <div class="p-4 sm:p-6 overflow-y-auto flex-1 min-h-0" @click="showDropdown = false">
            <form @submit.prevent="submitFeedback" class="space-y-4" @click.stop>
              <!-- Alloy ID 选择 -->
              <div @click.stop>
                <label class="block text-sm font-medium text-slate-700 mb-2">
                  Alloy ID <span class="text-red-500">*</span>
                </label>
                <div class="relative" @click.stop>
                  <input
                    v-model="searchQuery"
                    @input="handleSearchInput"
                    @focus="showDropdown = true"
                    type="text"
                    placeholder="搜索或选择 alloy_id..."
                    class="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  >
                  <i class="ph ph-magnifying-glass absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"></i>
                  
                  <!-- 下拉选项 -->
                  <div
                    v-if="showDropdown && filteredAlloyIds.length > 0"
                    class="absolute z-20 w-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg max-h-60 overflow-y-auto"
                  >
                    <button
                      v-for="alloyId in filteredAlloyIds"
                      :key="alloyId"
                      type="button"
                      @click="selectAlloyId(alloyId)"
                      class="w-full text-left px-4 py-2 hover:bg-indigo-50 transition-colors"
                    >
                      {{ alloyId }}
                    </button>
                  </div>
                </div>
                <div v-if="form.alloy_id" class="mt-2 text-sm text-slate-600">
                  已选择: <span class="font-medium">{{ form.alloy_id }}</span>
                </div>
              </div>

              <!-- Location 选择 -->
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-2">
                  问题位置 <span class="text-red-500">*</span>
                </label>
                <select
                  v-model="form.location"
                  class="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                >
                  <option value="">请选择问题位置</option>
                  <option value="alloy">alloy</option>
                  <option value="实验条件">实验条件</option>
                  <option value="实验性能">实验性能</option>
                  <option value="其他">其他</option>
                </select>
              </div>

              <!-- Type 选择 -->
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-2">
                  错误类型 <span class="text-red-500">*</span>
                </label>
                <select
                  v-model="form.type"
                  class="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                >
                  <option value="">请选择错误类型</option>
                  <option value="文本">文本</option>
                  <option value="表格">表格</option>
                  <option value="图片">图片</option>
                </select>
              </div>

              <!-- Problem 描述 -->
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-2">
                  问题描述 <span class="text-red-500">*</span>
                </label>
                <textarea
                  v-model="form.problem"
                  rows="5"
                  placeholder="请详细描述遇到的问题..."
                  class="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
                ></textarea>
              </div>

              <!-- 提交按钮 -->
              <div class="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  @click="close"
                  class="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
                >
                  取消
                </button>
                <button
                  type="submit"
                  :disabled="!isFormValid || submitting"
                  class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <i v-if="submitting" class="ph ph-circle-notch animate-spin"></i>
                  <span>{{ submitting ? '提交中...' : '提交' }}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { feedbackApi } from '../utils/api'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  identifier: {
    type: String,
    required: true
  },
  alloyIds: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['close', 'success'])

const form = ref({
  alloy_id: '',
  location: '',
  type: '',
  problem: ''
})

const searchQuery = ref('')
const showDropdown = ref(false)
const submitting = ref(false)
const submitSuccess = ref(false)

const filteredAlloyIds = computed(() => {
  if (!searchQuery.value) {
    return props.alloyIds
  }
  const query = searchQuery.value.toLowerCase()
  return props.alloyIds.filter(id => 
    id.toLowerCase().includes(query)
  )
})

const isFormValid = computed(() => {
  return form.value.alloy_id && 
         form.value.location && 
         form.value.type && 
         form.value.problem.trim()
})

const handleSearchInput = () => {
  showDropdown.value = true
}

const selectAlloyId = (alloyId) => {
  form.value.alloy_id = alloyId
  searchQuery.value = alloyId
  showDropdown.value = false
}

const close = () => {
  emit('close')
  // 延迟重置表单，等待动画完成
  setTimeout(() => {
    resetForm()
  }, 300)
}

const resetForm = () => {
  form.value = {
    alloy_id: '',
    location: '',
    type: '',
    problem: ''
  }
  searchQuery.value = ''
  showDropdown.value = false
  submitting.value = false
  submitSuccess.value = false
}

const submitFeedback = async () => {
  if (!isFormValid.value || submitting.value) return

  submitting.value = true
  try {
    await feedbackApi.submitFeedback({
      identifier: props.identifier,
      alloy_id: form.value.alloy_id,
      location: form.value.location,
      type: form.value.type,
      problem: form.value.problem.trim()
    })
    
    submitSuccess.value = true
    emit('success')
    
    // 显示成功提示
    alert('反馈提交成功！')
    
    // 重置表单
    resetForm()
    
    // 关闭弹窗
    close()
  } catch (error) {
    console.error('Failed to submit feedback:', error)
    alert('提交失败，请稍后重试。')
  } finally {
    submitting.value = false
  }
}

// 监听弹窗关闭，点击外部时关闭下拉框
watch(() => props.show, (newVal) => {
  if (!newVal) {
    showDropdown.value = false
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

