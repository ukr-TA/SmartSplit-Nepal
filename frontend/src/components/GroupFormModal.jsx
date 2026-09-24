import { useState } from 'react'
import { CalendarDays } from 'lucide-react'
import { getErrorMessage, getFieldErrors } from '../api/client'
import { groupApi } from '../api/services'
import { useUI } from '../context/UIContext'
import { GROUP_TYPES } from '../utils/constants'
import { Button, Field, Modal } from './ui'

export default function GroupFormModal({ group, onClose, onSaved }) {
  const editing = Boolean(group)
  const { toast } = useUI()
  const [form, setForm] = useState({
    name: group?.name || '',
    description: group?.description || '',
    group_type: group?.group_type || 'trip',
    is_trip: group ? group.is_trip : true,
    start_date: group?.start_date || '',
    end_date: group?.end_date || '',
  })
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  const set = (patch) => setForm((f) => ({ ...f, ...patch }))

  const submit = async (e) => {
    e.preventDefault()
    const errs = {}
    if (form.name.trim().length < 2) errs.name = 'Give your group a name.'
    if (form.start_date && form.end_date && form.end_date < form.start_date) errs.end_date = 'End date cannot be before the start date.'
    setErrors(errs)
    if (Object.keys(errs).length) return

    const body = {
      ...form,
      name: form.name.trim(),
      start_date: form.is_trip && form.start_date ? form.start_date : null,
      end_date: form.is_trip && form.end_date ? form.end_date : null,
    }
    setSaving(true)
    try {
      const saved = editing ? await groupApi.update(group.id, body) : await groupApi.create(body)
      toast(editing ? 'Group updated' : `${saved.name} created`)
      onSaved(saved)
    } catch (err) {
      setErrors(getFieldErrors(err))
      toast(getErrorMessage(err), 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      title={editing ? 'Edit group' : 'Create a group'}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <Button type="submit" form="group-form" loading={saving}>{editing ? 'Save changes' : 'Create group'}</Button>
        </>
      }
    >
      <form id="group-form" className="stack" onSubmit={submit} noValidate>
        <Field label="Group name" error={errors.name}>
          <input className="input" placeholder="e.g. Pokhara Trip" value={form.name} maxLength={80} onChange={(e) => set({ name: e.target.value })} autoFocus />
        </Field>

        <div className="field">
          <span className="field-label">Type</span>
          <div className="type-grid">
            {GROUP_TYPES.map(({ value, label, icon: Icon }) => (
              <button
                type="button"
                key={value}
                className={`type-option ${form.group_type === value ? 'selected' : ''}`}
                onClick={() => set({ group_type: value, is_trip: value === 'trip' ? true : form.group_type === 'trip' ? false : form.is_trip })}
              >
                <Icon size={20} />
                <span>{label}</span>
              </button>
            ))}
          </div>
        </div>

        <Field label="Description (optional)">
          <input className="input" placeholder="Lakeside, Sarangkot & paragliding" value={form.description} maxLength={300} onChange={(e) => set({ description: e.target.value })} />
        </Field>

        <label className="toggle-row">
          <input type="checkbox" checked={form.is_trip} disabled={form.group_type === 'trip'} onChange={(e) => set({ is_trip: e.target.checked })} />
          <span>
            <strong>Trip Mode</strong>
            <small className="muted">Adds trip dates, a trip dashboard and spending analytics.</small>
          </span>
        </label>

        {form.is_trip && (
          <div className="grid-2">
            <Field label={<><CalendarDays size={14} /> Start date</>}>
              <input className="input" type="date" value={form.start_date || ''} onChange={(e) => set({ start_date: e.target.value })} />
            </Field>
            <Field label="End date" error={errors.end_date}>
              <input className="input" type="date" value={form.end_date || ''} min={form.start_date || undefined} onChange={(e) => set({ end_date: e.target.value })} />
            </Field>
          </div>
        )}
      </form>
    </Modal>
  )
}
