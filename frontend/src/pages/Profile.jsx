import { useRef, useState } from 'react'
import { Camera, KeyRound, LogOut, Save, Trash2 } from 'lucide-react'
import { getErrorMessage, getFieldErrors } from '../api/client'
import { authApi } from '../api/services'
import { Avatar, Button, Field, PageHeader } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useUI } from '../context/UIContext'
import { formatDate } from '../utils/format'
import { useNavigate } from 'react-router-dom'

export default function Profile() {
  const { user, setUser, logout, applySession } = useAuth()
  const { toast, confirm } = useUI()
  const navigate = useNavigate()
  const fileRef = useRef(null)
  const [form, setForm] = useState({ full_name: user.full_name, email: user.email, phone_number: user.phone_number })
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [pw, setPw] = useState({ current_password: '', new_password: '', confirm: '' })
  const [pwErrors, setPwErrors] = useState({})
  const [pwSaving, setPwSaving] = useState(false)

  const dirty = form.full_name !== user.full_name || form.email !== user.email || form.phone_number !== user.phone_number

  const save = async (e) => {
    e.preventDefault()
    setSaving(true)
    setErrors({})
    try {
      const updated = await authApi.updateProfile(form)
      setUser(updated)
      setForm({ full_name: updated.full_name, email: updated.email, phone_number: updated.phone_number })
      toast('Profile updated')
    } catch (err) {
      setErrors(getFieldErrors(err))
      toast(getErrorMessage(err), 'error')
    } finally {
      setSaving(false)
    }
  }

  const uploadPicture = async (file) => {
    if (!file) return
    if (!file.type.startsWith('image/')) return toast('Please choose an image file.', 'error')
    if (file.size > 3 * 1024 * 1024) return toast('Profile picture must be smaller than 3 MB.', 'error')
    const body = new FormData()
    body.append('profile_picture', file)
    setUploading(true)
    try {
      setUser(await authApi.updateProfile(body))
      toast('Profile picture updated')
    } catch (err) {
      toast(getErrorMessage(err), 'error')
    } finally {
      setUploading(false)
    }
  }

  const removePicture = async () => {
    if (!(await confirm({ title: 'Remove profile picture?', confirmText: 'Remove', danger: true }))) return
    try {
      setUser(await authApi.updateProfile({ remove_picture: true }))
    } catch (err) {
      toast(getErrorMessage(err), 'error')
    }
  }

  const changePassword = async (e) => {
    e.preventDefault()
    const errs = {}
    if (pw.new_password.length < 8) errs.new_password = 'Use at least 8 characters.'
    if (pw.new_password !== pw.confirm) errs.confirm = 'Passwords do not match.'
    setPwErrors(errs)
    if (Object.keys(errs).length) return
    setPwSaving(true)
    try {
      applySession(await authApi.changePassword({ current_password: pw.current_password, new_password: pw.new_password }))
      setPw({ current_password: '', new_password: '', confirm: '' })
      toast('Password changed')
    } catch (err) {
      setPwErrors(getFieldErrors(err))
    } finally {
      setPwSaving(false)
    }
  }

  const doLogout = async () => {
    if (!(await confirm({ title: 'Log out?', confirmText: 'Log out' }))) return
    await logout()
    navigate('/login')
  }

  return (
    <div className="page narrow">
      <PageHeader title="Profile" subtitle="Your account details. Friends see your name and a masked phone number." />

      <div className="card profile-card">
        <div className="profile-pic">
          <Avatar user={user} size={96} />
          <button className="pic-btn" onClick={() => fileRef.current?.click()} disabled={uploading} aria-label="Change profile picture">
            <Camera size={16} />
          </button>
          <input ref={fileRef} type="file" accept="image/*" hidden onChange={(e) => uploadPicture(e.target.files[0])} />
        </div>
        <div className="grow">
          <h2>{user.full_name}</h2>
          <p className="muted">{user.email} · +977 {user.phone_number}</p>
          <small className="muted">Member since {formatDate(user.date_joined)}</small>
          {user.profile_picture && (
            <div><button className="link-btn danger-text small" onClick={removePicture}><Trash2 size={13} /> Remove picture</button></div>
          )}
        </div>
      </div>

      <form className="card stack" onSubmit={save} noValidate>
        <h3>Account information</h3>
        <Field label="Full name" error={errors.full_name}>
          <input className="input" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
        </Field>
        <div className="grid-2">
          <Field label="Email" error={errors.email}>
            <input className="input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </Field>
          <Field label="Mobile number" error={errors.phone_number} hint="Used by friends to find you">
            <div className="input-prefix">
              <span>+977</span>
              <input className="input" inputMode="numeric" value={form.phone_number} onChange={(e) => setForm({ ...form, phone_number: e.target.value })} />
            </div>
          </Field>
        </div>
        <div className="row-end">
          <Button type="submit" loading={saving} disabled={!dirty}><Save size={16} /> Save changes</Button>
        </div>
      </form>

      <form className="card stack" onSubmit={changePassword} noValidate>
        <h3><KeyRound size={18} /> Change password</h3>
        <Field label="Current password" error={pwErrors.current_password}>
          <input className="input" type="password" autoComplete="current-password" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} />
        </Field>
        <div className="grid-2">
          <Field label="New password" error={pwErrors.new_password}>
            <input className="input" type="password" autoComplete="new-password" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} />
          </Field>
          <Field label="Confirm new password" error={pwErrors.confirm}>
            <input className="input" type="password" autoComplete="new-password" value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} />
          </Field>
        </div>
        <div className="row-end">
          <Button type="submit" loading={pwSaving} className="btn-ghost" disabled={!pw.current_password || !pw.new_password}>Update password</Button>
        </div>
      </form>

      <button className="btn btn-ghost danger-text btn-block" onClick={doLogout}><LogOut size={16} /> Log out</button>
    </div>
  )
}
