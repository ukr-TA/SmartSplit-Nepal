import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Eye, EyeOff, LogIn } from 'lucide-react'
import { getErrorMessage } from '../api/client'
import { Button, Field } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useUI } from '../context/UIContext'
import AuthLayout from './AuthLayout'

export default function Login() {
  const { login } = useAuth()
  const { toast } = useUI()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [form, setForm] = useState({ identifier: '', password: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const next = params.get('next')
  const submit = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.identifier.trim() || !form.password) {
      setError('Enter your email or phone number and password.')
      return
    }
    setLoading(true)
    try {
      await login(form.identifier.trim(), form.password)
      toast('Welcome back!')
      navigate(next && next.startsWith('/') ? next : '/', { replace: true })
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Welcome back" subtitle="Log in with your email or Nepali mobile number.">
      <form className="stack" onSubmit={submit} noValidate>
        {error && <div className="alert alert-error">{error}</div>}
        <Field label="Email or phone number">
          <input
            className="input"
            name="identifier"
            autoComplete="username"
            placeholder="you@example.com or 98XXXXXXXX"
            value={form.identifier}
            onChange={(e) => setForm({ ...form, identifier: e.target.value })}
            autoFocus
          />
        </Field>
        <Field label="Password">
          <div className="input-with-btn">
            <input
              className="input"
              name="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              placeholder="Your password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
            <button type="button" className="icon-btn" onClick={() => setShowPassword((s) => !s)} aria-label="Show password">
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
        </Field>
        <Button type="submit" loading={loading} className="btn-primary btn-block btn-lg">
          <LogIn size={18} /> Log in
        </Button>
      </form>
      <p className="auth-switch">
        New to SmartSplit? <Link to={`/register${next ? `?next=${encodeURIComponent(next)}` : ''}`}>Create an account</Link>
      </p>
    </AuthLayout>
  )
}
