import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  base: '/hea/',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      // 代理 API 请求到后端
      '/papers': {
        target: 'http://localhost:8003',
        changeOrigin: true
      },
      '/feedback': {
        target: 'http://localhost:8003',
        changeOrigin: true
      },
      '/static_images': {
        target: 'http://localhost:8003',
        changeOrigin: true
      },
      '/static_pdfs': {
        target: 'http://localhost:8003',
        changeOrigin: true
      }
    }
  }
})

