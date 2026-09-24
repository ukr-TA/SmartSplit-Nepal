import axios from 'axios'

// Base URL of the Django REST API. Override with VITE_API_BASE_URL in frontend/.env
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'

export const TOKEN_KEY = 'smartsplit_token'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
})

// Attach the auth token to every request
api.interceptors.request.use((config) => {
  let token = null
  try {
    token = localStorage.getItem(TOKEN_KEY)
  } catch {
    token = null
  }
  if (token) config.headers.Authorization = `Token ${token}`
  return config
})

// If the server says our token is no longer valid, log out everywhere
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !error.config?.url?.includes('/auth/')) {
      window.dispatchEvent(new Event('smartsplit:unauthorized'))
    }
    return Promise.reject(error)
  },
)

const FIELD_LABELS = {
  full_name: 'Name',
  phone_number: 'Phone',
  email: 'Email',
  password: 'Password',
  amount: 'Amount',
  splits: 'Split',
  description: 'Description',
  paid_by: 'Payer',
  end_date: 'End date',
  name: 'Name',
}

/** Turn any axios error into a short, human-readable message. */
export function getErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  if (!error?.response) {
    return 'Cannot reach the SmartSplit server. Is the backend running on port 8000?'
  }
  const { data, status } = error.response
  if (status >= 500) return 'The server had a problem. Check the backend terminal for details.'
  if (typeof data === 'string') return data.length < 200 ? data : fallback
  if (Array.isArray(data)) return String(data[0])
  if (data?.detail) return data.detail
  if (data && typeof data === 'object') {
    const [field, messages] = Object.entries(data)[0] || []
    const msg = Array.isArray(messages) ? messages[0] : messages
    if (field && msg) {
      if (field === 'non_field_errors') return String(msg)
      const label = FIELD_LABELS[field]
      return label && typeof msg === 'string' ? `${label}: ${msg}` : String(msg)
    }
  }
  return fallback
}

/** Field-level errors ({field: "message"}) for highlighting form inputs. */
export function getFieldErrors(error) {
  const data = error?.response?.data
  if (!data || typeof data !== 'object' || Array.isArray(data)) return {}
  return Object.fromEntries(
    Object.entries(data).map(([k, v]) => [k, Array.isArray(v) ? String(v[0]) : String(v)]),
  )
}

export default api
