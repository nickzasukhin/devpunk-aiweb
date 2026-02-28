import { api } from './client'
export const getDocuments = () => api.get('/admin/documents')
export const uploadDocument = (file: File) => { const fd = new FormData(); fd.append('file', file); return api.post('/admin/documents/upload', fd) }
export const deleteDocument = (id: string) => api.delete(`/admin/documents/${id}`)
export const reindexDocument = (id: string) => api.post(`/admin/documents/${id}/reindex`)
export const getConfig = () => api.get('/admin/config')
export const updateConfig = (data: Record<string, string>) => api.put('/admin/config', data)
export const getUsers = () => api.get('/admin/users')
export const createUser = (email: string, password: string) => api.post('/admin/users', { email, password })
export const toggleUser = (id: string) => api.patch(`/admin/users/${id}/toggle`)
export const resetPassword = (id: string, password: string) => api.patch(`/admin/users/${id}/password`, { password })
export const getAuditLog = (limit = 100, offset = 0) => api.get('/admin/audit-log', { params: { limit, offset } })
export const getVisitors = () => api.get('/admin/conversations/visitors')
export const getVisitorConversations = (id: string) => api.get(`/admin/conversations/visitors/${id}`)
