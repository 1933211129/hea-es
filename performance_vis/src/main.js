import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'
import 'katex/dist/katex.min.css'

// 动态加载 KaTeX auto-render
import('katex/dist/contrib/auto-render').then((module) => {
  if (typeof window !== 'undefined') {
    window.renderMathInElement = module.default || module
  }
}).catch((err) => {
  console.warn('Failed to load KaTeX auto-render:', err)
})

createApp(App).use(router).mount('#app')

