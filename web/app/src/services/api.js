import axios from 'axios'
import router from '../router'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add token to requests
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401s and global errors
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

export default api

export const disciplineApi = {
  getAll: () => api.get('/admin/disciplines'),
  create: (data) => api.post('/admin/disciplines', data),
  update: (slug, data) => api.patch(`/admin/disciplines/${slug}`, data),
  delete: (slug) => api.delete(`/admin/disciplines/${slug}`),
}

export const userApi = {
  getUsers: (params) => api.get('/admin/users', { params }),
}

export const chatApi = {
  getChats: (params) => api.get('/admin/chats', { params }),
  syncChat: (chatId) => api.post(`/admin/chats/${chatId}/sync`),
  createInviteLink: (chatId, data) => api.post(`/admin/chats/${chatId}/invite-link`, data),
}

export const authApi = {
  requestOtp: (identifier) => api.post('/admin/auth/otp/request', { identifier }),
  verifyOtp: (telegramId, code) => api.post('/admin/auth/otp/verify', { telegram_id: telegramId, code }),
  loginTelegramWebApp: (initData) => api.post('/auth/telegram/webapp', { init_data: initData }),
}

export const staffApi = {
  getPending: () => api.get('/admin/staff/pending'),
  createPending: (data) => api.post('/admin/staff/pending', data),
  deletePending: (id) => api.delete(`/admin/staff/pending/${id}`),
  importCsv: (formData) => api.post('/admin/staff/pending/import-csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  importText: (rawText) => api.post('/admin/staff/pending/import-text', { raw_text: rawText }),
}

