<template>
  <button
    v-if="hasSource"
    @click="openModal"
    class="mt-2 text-xs text-indigo-600 hover:text-indigo-700 hover:underline cursor-pointer flex items-center gap-1"
  >
    <i class="ph ph-link text-xs"></i>
    <span>来源 ({{ sourceCount }})</span>
  </button>
  
  <SourceModal
    :show="showModal"
    :source="source"
    :highlight-values="highlightValues"
    @close="closeModal"
  />
</template>

<script setup>
import { ref, computed } from 'vue'
import SourceModal from './SourceModal.vue'
import { hasAnySource, getSourceCount } from '../utils/source'

const props = defineProps({
  source: {
    type: [Array, Object],
    default: null
  },
  // 用于高亮的指标值（可以是字符串或数组）
  highlightValues: {
    type: [String, Array, Object],
    default: null
  }
})

const showModal = ref(false)
const hasSource = computed(() => hasAnySource(props.source))
const sourceCount = computed(() => getSourceCount(props.source))

const openModal = () => {
  showModal.value = true
}

const closeModal = () => {
  showModal.value = false
}
</script>

