// One place for every API call the app makes.
import api from './client'

const data = (promise) => promise.then((res) => res.data)

export const authApi = {
  register: (body) => data(api.post('/auth/register/', body)),
  login: (identifier, password) => data(api.post('/auth/login/', { identifier, password })),
  logout: () => api.post('/auth/logout/'),
  changePassword: (body) => data(api.post('/auth/change-password/', body)),
  profile: () => data(api.get('/profile/')),
  updateProfile: (body) => {
    const isForm = body instanceof FormData
    return data(api.patch('/profile/', body, isForm ? { headers: { 'Content-Type': 'multipart/form-data' } } : {}))
  },
  searchUsers: (q) => data(api.get('/users/search/', { params: { q } })),
  health: () => data(api.get('/health/')),
}

export const groupApi = {
  list: () => data(api.get('/groups/')),
  get: (id) => data(api.get(`/groups/${id}/`)),
  create: (body) => data(api.post('/groups/', body)),
  update: (id, body) => data(api.patch(`/groups/${id}/`, body)),
  remove: (id) => api.delete(`/groups/${id}/`),
  addMember: (id, userId) => data(api.post(`/groups/${id}/members/`, { user_id: userId })),
  removeMember: (id, userId) => api.delete(`/groups/${id}/members/${userId}/`),
  invite: (id, regenerate = false) => data(api.post(`/groups/${id}/invite/`, { regenerate })),
  previewInvite: (token) => data(api.get(`/groups/join/${token}/`)),
  join: (token) => data(api.post(`/groups/join/${token}/`)),
  balances: (id) => data(api.get(`/groups/${id}/balances/`)),
  suggestions: (id) => data(api.get(`/groups/${id}/settlement-suggestions/`)),
  activity: (id) => data(api.get(`/groups/${id}/activity/`)),
  analytics: (id) => data(api.get(`/groups/${id}/analytics/`)),
  forecast: (id) => data(api.get(`/groups/${id}/forecast/`)),
}

export const expenseApi = {
  list: (params) => data(api.get('/expenses/', { params })),
  get: (id) => data(api.get(`/expenses/${id}/`)),
  preview: (body) => data(api.post('/expenses/preview/', body)),
  create: (body) => data(api.post('/expenses/', body)),
  update: (id, body) => data(api.patch(`/expenses/${id}/`, body)),
  remove: (id) => api.delete(`/expenses/${id}/`),
  uploadReceipt: (id, file) => {
    const form = new FormData()
    form.append('receipt', file)
    return data(api.post(`/expenses/${id}/receipt/`, form, { headers: { 'Content-Type': 'multipart/form-data' } }))
  },
  removeReceipt: (id) => data(api.delete(`/expenses/${id}/receipt/`)),
}

export const settlementApi = {
  list: (params) => data(api.get('/settlements/', { params })),
  get: (id) => data(api.get(`/settlements/${id}/`)),
  create: (body) => data(api.post('/settlements/', body)),
  confirm: (id, pin) => data(api.post(`/settlements/${id}/confirm/`, { pin })),
  cancel: (id) => data(api.post(`/settlements/${id}/cancel/`)),
  verifyEsewa: (id, body) => data(api.post(`/settlements/${id}/verify-esewa/`, body)),
  verifyKhalti: (id, pidx) => data(api.post(`/settlements/${id}/verify-khalti/`, { pidx })),
  paymentConfig: () => data(api.get('/payments/config/')),
}

/** Machine-learning helpers (models trained in ml/notebooks/smartsplit_ml.ipynb). */
export const mlApi = {
  suggestCategory: (description, amount) =>
    data(api.post('/ml/suggest-category/', { description, amount: amount || null })),
  info: () => data(api.get('/ml/info/')),
}

export const miscApi = {
  dashboard: () => data(api.get('/dashboard/')),
  activity: () => data(api.get('/activity/')),
  notifications: () => data(api.get('/notifications/')),
  markRead: (id) => data(api.patch(`/notifications/${id}/`, { is_read: true })),
  markAllRead: () => data(api.post('/notifications/mark-all-read/')),
}
