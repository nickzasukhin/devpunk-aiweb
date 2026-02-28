import axios from 'axios'

const BASE = (import.meta.env.VITE_API_URL as string) || ''

export const api = axios.create({ baseURL: BASE })

const attach = (instance: typeof api) => {
  instance.interceptors.request.use(cfg => {
    const token = localStorage.getItem('access_token')
    if (token) cfg.headers.Authorization = `Bearer ${token}`
    return cfg
  })
  instance.interceptors.response.use(r => r, err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  })
}
attach(api)
