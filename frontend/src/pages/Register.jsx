import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { UserPlus } from 'lucide-react'
import { getErrorMessage, getFieldErrors } from '../api/client'
import { Button, Field } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useUI } from '../context/UIContext'
import AuthLayout from './AuthLayout'

const PHONE_RE = /^9[78]\d{8}$/

export default function Register() {
  const { register } = useAuth()
  const { toast } = useUI()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [form, setForm] = useState({ full_name: '', email: '', phone_number: '', password: '', confirm: '' })
  const [errors, setErrors] = useState({})
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  const validate = () => {
    const errs = {}
    if (form.full_name.trim().length < 2) errs.full_name = 'Enter your full name.'
    if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) errs.email = 'Enter a valid email address.'
    const phone = form.phone_number.replace(/\D/g, '').replace(/^977(?=\d{10}$)/, '')
    if (!PHONE_RE.test(phone)) errs.phone_number = 'Enter a 10-digit Nepali mobile number (98XXXXXXXX).'
    if (form.password.length < 8) errs.password = 'Use at least 8 characters.'
    if (form.password !== form.confirm) errs.confirm = 'Passwords do not match.'
    return errs
  }

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    const errs = validate()
    setErrors(errs)
    if (Object.keys(errs).length) return
    setLoading(true)
    try {
      await register({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        phone_number: form.phone_number,
        password: form.password,
      })
      toast('Account created successfully. Welcome to SmartSplit!')
      const next = params.get('next')
      navigate(next && next.startsWith('/') ? next : '/', { replace: true })
    } catch (err) {
      setErrors(getFieldErrors(err))
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Create your account" subtitle="Friends can find you by your phone number.">
      <form className="stack" onSubmit={submit} noValidate>
        {error && <div className="alert alert-error">{error}</div>}
        <Field label="Full name" error={errors.full_name}>
          <input className="input" name="full_name" autoComplete="name" placeholder="Utsuk Kharel" value={form.full_name} onChange={set('full_name')} autoFocus />
        </Field>
        <div className="grid-2">
          <Field label="Email" error={errors.email}>
            <input className="input" name="email" type="email" autoComplete="email" placeholder="you@example.com" value={form.email} onChange={set('email')} />
          </Field>
          <Field label="Mobile number" error={errors.phone_number}>
            <div className="input-prefix">
              <span>+977</span>
              <input className="input" name="phone_number" inputMode="numeric" autoComplete="tel-national" placeholder="98XXXXXXXX" maxLength={14} value={form.phone_number} onChange={set('phone_number')} />
            </div>
          </Field>
        </div>
        <div className="grid-2">
          <Field label="Password" error={errors.password} hint="At least 8 characters, not too common.">
            <input className="input" name="password" type="password" autoComplete="new-password" value={form.password} onChange={set('password')} />
          </Field>
          <Field label="Confirm password" error={errors.confirm}>
            <input className="input" name="confirm" type="password" autoComplete="new-password" value={form.confirm} onChange={set('confirm')} />
          </Field>
        </div>
        <Button type="submit" loading={loading} className="btn-primary btn-block btn-lg">
          <UserPlus size={18} /> Create account
        </Button>
      </form>
      <p className="auth-switch">
        Already have an account? <Link to={`/login${params.get('next') ? `?next=${encodeURIComponent(params.get('next'))}` : ''}`}>Log in</Link>
      </p>
    </AuthLayout>
  )
}
