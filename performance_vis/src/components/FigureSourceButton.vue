<template>
  <button
    v-if="figureSource"
    @click="openModal"
    class="mt-2 text-xs text-amber-600 hover:text-amber-700 hover:underline cursor-pointer flex items-center gap-1"
  >
    <i class="ph ph-image text-xs"></i>
    <span>图片来源</span>
  </button>
  
  <FigureSourceModal
    :show="showModal"
    :figure-source="figureSource"
    :highlight-values="highlightValues"
    @close="closeModal"
  />
</template>

<script setup>
import { ref } from 'vue'
import FigureSourceModal from './FigureSourceModal.vue'

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

const showModal = ref(false)

const openModal = () => {
  showModal.value = true
}

const closeModal = () => {
  showModal.value = false
}
</script>

