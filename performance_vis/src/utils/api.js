import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8003'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
})

export const paperApi = {
  // 获取所有论文列表
  async getPapers() {
    const response = await api.get('/papers')
    return response.data
  },

  // 搜索论文
  async searchPapers(query) {
    const response = await api.get('/papers/search', {
      params: { q: query }
    })
    return response.data
  },

  // 获取论文详情
  async getPaperDetail(identifier) {
    const response = await api.get(`/papers/${identifier}`)
    return response.data
  },

  // 获取论文性能数据
  async getPaperPerformance(identifier) {
    const response = await api.get(`/papers/${identifier}/performance`)
    return response.data
  },

  // 获取图片 URL
  getImageUrl(path) {
    if (!path) return ''
    const cleanPath = path.startsWith('/') ? path.substring(1) : path
    return `${API_BASE_URL}/static_images/${cleanPath}`
  },

  // 获取 PDF URL
  async getPdfUrl(identifier) {
    try {
      const response = await api.get(`/papers/${identifier}/pdf`)
      if (response.data && response.data.url) {
        return `${API_BASE_URL}${response.data.url}`
      }
      return null
    } catch (error) {
      console.error('Error fetching PDF URL:', error)
      return null
    }
  }
}

export const feedbackApi = {
  // 提交问题反馈
  async submitFeedback(data) {
    const response = await api.post('/feedback', data)
    return response.data
  }
}

export default api

