import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft, ArrowRight, Check, CheckCircle2, Equal, ImagePlus, Percent, Plus, Users, X,
} from 'lucide-react'
import { getErrorMessage } from '../api/client'
import CategorySuggestion from '../components/CategorySuggestion'
import { expenseApi, groupApi } from '../api/services'
import {
  Avatar, Button, CardSkeleton, CategoryIcon, EmptyState, ErrorState, Field, Money, PageHeader, Spinner,
} from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useUI } from '../context/UIContext'
import { CATEGORIES, groupTypeOf } from '../utils/constants'
import { firstName, formatNPR, todayISO } from '../utils/format'

const STEPS = ['Details', 'Paid by', 'Split with', 'How to split', 'Review']
const METHODS = [
  { value: 'equal', label: 'Equally', icon: Equal, hint: 'Everyone pays the same' },
  { value: 'custom', label: 'Custom amounts', icon: Plus, hint: 'Enter each person’s amount' },
  { value: 'percentage', label: 'Percentages', icon: Percent, hint: 'Must add up to 100%' },
]

const round2 = (n) => Math.round(n * 100) / 100

function GroupPicker({ onPick }) {
  const [groups, setGroups] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => {
    groupApi.list().then(setGroups).catch((e) => setError(getErrorMessage(e)))
  }, [])
  if (error) return <ErrorState message={error} />
  if (!groups) return <CardSkeleton />
  if (!groups.length) {
    return (
      <div className="card">
        <EmptyState
          icon={Users}
          title="Create a group first"
          message="Expenses belong to a group — like a trip, your flat or a project."
          action={<Link to="/groups/new" className="btn btn-primary"><Plus size={16} /> Create group</Link>}
        />
      </div>
    )
  }
  return (
    <div className="card">
      <h3>Which group is this expense for?</h3>
      <div className="pick-grid">
        {groups.map((g) => {
          const Icon = groupTypeOf(g.group_type).icon
          return (
            <button key={g.id} className="pick-card" onClick={() => onPick(g.id)}>
              <span className={`group-icon type-${g.group_type}`}><Icon size={20} /></span>
              <span className="grow">
                <strong>{g.name}</strong>
                <small className="muted">{g.member_count} members</small>
              </span>
              <ArrowRight size={16} className="muted" />
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default function SplitExpense() {
  const { expenseId } = useParams()
  const editing = Boolean(expenseId)
  const [params, setParams] = useSearchParams()
  const groupId = params.get('group')
  const { user } = useAuth()
  const { toast } = useUI()
  const navigate = useNavigate()
  const fileRef = useRef(null)

  const [group, setGroup] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [step, setStep] = useState(0)
  const [form, setForm] = useState({
    description: '',
    amount: '',
    category: 'food',
    date: todayISO(),
    paid_by: user.id,
    participants: [],
    split_method: 'equal',
    custom: {},
    percent: {},
    notes: '',
  })
  const [receipt, setReceipt] = useState(null)
  const [error, setError] = useState('')
  const [preview, setPreview] = useState(null)
  const [busy, setBusy] = useState(false)
  const [loadedExpense, setLoadedExpense] = useState(null)

  const set = (patch) => setForm((f) => ({ ...f, ...patch }))

  // Load expense (edit mode) and then its group
  useEffect(() => {
    let active = true
    const load = async () => {
      try {
        let gid = groupId
        if (editing) {
          const e = await expenseApi.get(expenseId)
          if (!e.can_edit) throw new Error('You are not allowed to edit this expense.')
          gid = e.group
          const custom = {}
          const percent = {}
          e.splits.forEach((s) => {
            custom[s.user.id] = String(Number(s.amount))
            if (s.percentage != null) percent[s.user.id] = String(Number(s.percentage))
          })
          if (!active) return
          setLoadedExpense(e)
          setForm({
            description: e.description,
            amount: String(Number(e.amount)),
            category: e.category,
            date: e.date,
            paid_by: e.paid_by.id,
            participants: e.splits.map((s) => s.user.id),
            split_method: e.split_method,
            custom,
            percent,
            notes: e.notes || '',
          })
        }
        if (!gid) return
        const g = await groupApi.get(gid)
        if (!active) return
        setGroup(g)
        if (!editing) {
          // For trips, default the date into the trip period when today is outside it
          const today = todayISO()
          const outside = g.is_trip && g.start_date && (today < g.start_date || (g.end_date && today > g.end_date))
          const date = outside && g.start_date <= today ? g.start_date : today
          setForm((f) => ({ ...f, date, participants: g.members.map((m) => m.user.id) }))
        }
      } catch (err) {
        if (active) setLoadError(err.response ? getErrorMessage(err) : err.message)
      }
    }
    load()
    return () => {
      active = false
    }
  }, [groupId, editing, expenseId])

  const members = useMemo(() => group?.members.map((m) => m.user) || [], [group])
  const amount = Number(form.amount) || 0
  const selected = members.filter((m) => form.participants.includes(m.id))

  const customTotal = round2(selected.reduce((s, m) => s + (Number(form.custom[m.id]) || 0), 0))
  const percentTotal = round2(selected.reduce((s, m) => s + (Number(form.percent[m.id]) || 0), 0))

  const validateStep = (i) => {
    if (i === 0) {
      if (!form.description.trim()) return 'Describe the expense (e.g. Hotel, Dinner).'
      if (!(amount > 0)) return 'Enter an amount greater than zero.'
      if (amount > 10000000) return 'Amount is too large.'
      if (!/^\d+(\.\d{1,2})?$/.test(String(form.amount).trim())) return 'Use at most 2 decimal places (paisa).'
      if (!form.date) return 'Pick a date.'
    }
    if (i === 1 && !form.paid_by) return 'Choose who paid.'
    if (i === 2 && form.participants.length === 0) return 'Select at least one person to split with.'
    if (i === 3) {
      if (form.split_method === 'custom' && Math.abs(customTotal - amount) > 0.001) {
        const diff = round2(amount - customTotal)
        return `Custom amounts must add up to ${formatNPR(amount)} (${diff > 0 ? `${formatNPR(diff)} left` : `${formatNPR(-diff)} too much`}).`
      }
      if (form.split_method === 'percentage' && Math.abs(percentTotal - 100) > 0.001) {
        return `Percentages must add up to 100% (currently ${percentTotal}%).`
      }
    }
    return ''
  }

  const payload = () => {
    const body = {
      group: group.id,
      description: form.description.trim(),
      amount: amount.toFixed(2),
      category: form.category,
      date: form.date,
      paid_by: form.paid_by,
      split_method: form.split_method,
      notes: form.notes,
    }
    if (form.split_method === 'equal') body.participants = form.participants
    if (form.split_method === 'custom') body.splits = selected.map((m) => ({ user: m.id, amount: (Number(form.custom[m.id]) || 0).toFixed(2) }))
    if (form.split_method === 'percentage') body.splits = selected.map((m) => ({ user: m.id, percentage: (Number(form.percent[m.id]) || 0).toFixed(2) }))
    return body
  }

  const next = async () => {
    const msg = validateStep(step)
    setError(msg)
    if (msg) return
    if (step === 3) {
      setBusy(true)
      try {
        setPreview(await expenseApi.preview(payload()))
        setStep(4)
      } catch (err) {
        setError(getErrorMessage(err))
      } finally {
        setBusy(false)
      }
      return
    }
    setStep((s) => s + 1)
  }

  const back = () => {
    setError('')
    setStep((s) => Math.max(0, s - 1))
  }

  const confirm = async () => {
    setBusy(true)
    setError('')
    try {
      const saved = editing ? await expenseApi.update(expenseId, payload()) : await expenseApi.create(payload())
      if (receipt) {
        try {
          await expenseApi.uploadReceipt(saved.id, receipt)
        } catch (err) {
          toast(`Expense saved, but the receipt failed: ${getErrorMessage(err)}`, 'error')
        }
      }
      toast(editing ? 'Expense updated' : `${saved.description} added · ${formatNPR(saved.amount)}`)
      navigate(`/groups/${group.id}/expenses`)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  // Split equally helpers for custom/percentage modes
  const fillEqual = () => {
    if (!selected.length) return
    if (form.split_method === 'custom') {
      const each = Math.floor((amount * 100) / selected.length)
      let rest = Math.round(amount * 100) - each * selected.length
      const custom = {}
      selected.forEach((m) => {
        const extra = rest > 0 ? 1 : 0
        rest -= extra
        custom[m.id] = ((each + extra) / 100).toFixed(2)
      })
      set({ custom })
    } else {
      const each = Math.floor(10000 / selected.length) / 100
      const percent = {}
      selected.forEach((m, i) => {
        percent[m.id] = i === 0 ? round2(100 - each * (selected.length - 1)).toString() : each.toString()
      })
      set({ percent })
    }
  }

  if (loadError) {
    return (
      <div className="page narrow">
        <ErrorState message={loadError} />
        <Link to="/" className="btn btn-ghost">Back to dashboard</Link>
      </div>
    )
  }

  if (!editing && !groupId) {
    return (
      <div className="page narrow">
        <PageHeader title="Split Expense" subtitle="Record what was spent and who shares it." />
        <GroupPicker onPick={(id) => setParams({ group: id })} />
      </div>
    )
  }

  if (!group) return <Spinner />

  if (members.length < 2) {
    return (
      <div className="page narrow">
        <PageHeader title="Split Expense" subtitle={group.name} />
        <div className="card">
          <EmptyState
            icon={Users}
            title="Add members first"
            message={`${group.name} only has you. Add friends to split expenses with them.`}
            action={<Link to={`/groups/${group.id}/members?add=1`} className="btn btn-primary">Add members</Link>}
          />
        </div>
      </div>
    )
  }

  const payer = members.find((m) => m.id === form.paid_by)

  return (
    <div className="page narrow">
      <PageHeader
        title={editing ? 'Edit expense' : 'Split Expense'}
        subtitle={
          <>
            in <Link to={`/groups/${group.id}`}>{group.name}</Link>
            {!editing && (
              <> · <button className="link-btn small" onClick={() => setParams({})}>change group</button></>
            )}
          </>
        }
      />

      <ol className="stepper">
        {STEPS.map((label, i) => (
          <li key={label} className={i === step ? 'current' : i < step ? 'done' : ''}>
            <span className="step-dot">{i < step ? <Check size={13} /> : i + 1}</span>
            <span className="step-label">{label}</span>
          </li>
        ))}
      </ol>

      <div className="card wizard-card">
        {step === 0 && (
          <div className="stack">
            <Field label="What was it for?">
              <input className="input input-lg" placeholder="e.g. Hotel in Lakeside" value={form.description} maxLength={120} onChange={(e) => set({ description: e.target.value })} autoFocus />
            </Field>
            <Field label="Amount">
              <div className="amount-input">
                <span>Rs.</span>
                <input inputMode="decimal" placeholder="0" value={form.amount} onChange={(e) => set({ amount: e.target.value.replace(/[^\d.]/g, '') })} />
              </div>
            </Field>
            <div className="field">
              <span className="field-label">Category</span>
              <CategorySuggestion
                description={form.description}
                amount={form.amount}
                category={form.category}
                onApply={(category) => set({ category })}
              />
              <div className="cat-grid">
                {CATEGORIES.map((c) => (
                  <button type="button" key={c.value} className={`cat-option ${form.category === c.value ? 'selected' : ''}`} onClick={() => set({ category: c.value })}>
                    <CategoryIcon category={c.value} size={34} />
                    <span>{c.label}</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="grid-2">
              <Field label="Date">
                <input className="input" type="date" value={form.date} max={todayISO()} onChange={(e) => set({ date: e.target.value })} />
              </Field>
              <Field label="Notes (optional)">
                <input className="input" placeholder="Room 204, 2 nights" value={form.notes} maxLength={1000} onChange={(e) => set({ notes: e.target.value })} />
              </Field>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="stack">
            <h3>Who paid <Money value={amount} />?</h3>
            <div className="choice-list">
              {members.map((m) => (
                <button key={m.id} className={`choice ${form.paid_by === m.id ? 'selected' : ''}`} onClick={() => set({ paid_by: m.id })}>
                  <Avatar user={m} size={38} />
                  <span className="grow">{m.id === user.id ? 'You' : m.full_name}</span>
                  <span className="radio" />
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="stack">
            <div className="row-between">
              <h3>Split with</h3>
              <div className="row">
                <button className="link-btn" onClick={() => set({ participants: members.map((m) => m.id) })}>Everyone</button>
                <button className="link-btn" onClick={() => set({ participants: [] })}>None</button>
              </div>
            </div>
            <div className="choice-list">
              {members.map((m) => {
                const on = form.participants.includes(m.id)
                return (
                  <button
                    key={m.id}
                    className={`choice ${on ? 'selected' : ''}`}
                    onClick={() => set({ participants: on ? form.participants.filter((id) => id !== m.id) : [...form.participants, m.id] })}
                  >
                    <Avatar user={m} size={38} />
                    <span className="grow">{m.id === user.id ? 'You' : m.full_name}</span>
                    <span className="checkbox">{on && <Check size={14} />}</span>
                  </button>
                )
              })}
            </div>
            <p className="muted small">
              {form.participants.length} selected
              {form.participants.length > 0 && <> · about <Money value={amount / form.participants.length} /> each if split equally</>}
            </p>
          </div>
        )}

        {step === 3 && (
          <div className="stack">
            <h3>How should <Money value={amount} /> be split?</h3>
            <div className="method-grid">
              {METHODS.map(({ value, label, icon: Icon, hint }) => (
                <button key={value} className={`method-option ${form.split_method === value ? 'selected' : ''}`} onClick={() => set({ split_method: value })}>
                  <Icon size={20} />
                  <strong>{label}</strong>
                  <small>{hint}</small>
                </button>
              ))}
            </div>

            {form.split_method === 'equal' && (
              <ul className="share-list">
                {selected.map((m) => (
                  <li key={m.id}>
                    <Avatar user={m} size={32} />
                    <span className="grow">{m.id === user.id ? 'You' : m.full_name}</span>
                    <Money value={amount / selected.length} className="strong" />
                  </li>
                ))}
              </ul>
            )}

            {form.split_method !== 'equal' && (
              <>
                <ul className="share-list inputs">
                  {selected.map((m) => (
                    <li key={m.id}>
                      <Avatar user={m} size={32} />
                      <span className="grow">{m.id === user.id ? 'You' : m.full_name}</span>
                      {form.split_method === 'custom' ? (
                        <div className="mini-input">
                          <span>Rs.</span>
                          <input
                            inputMode="decimal"
                            aria-label={`Amount for ${m.full_name}`}
                            value={form.custom[m.id] ?? ''}
                            placeholder="0"
                            onChange={(e) => set({ custom: { ...form.custom, [m.id]: e.target.value.replace(/[^\d.]/g, '') } })}
                          />
                        </div>
                      ) : (
                        <div className="mini-input">
                          <input
                            inputMode="decimal"
                            aria-label={`Percentage for ${m.full_name}`}
                            value={form.percent[m.id] ?? ''}
                            placeholder="0"
                            onChange={(e) => set({ percent: { ...form.percent, [m.id]: e.target.value.replace(/[^\d.]/g, '') } })}
                          />
                          <span>%</span>
                          <small className="muted">{formatNPR((amount * (Number(form.percent[m.id]) || 0)) / 100)}</small>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
                <div className={`total-check ${form.split_method === 'custom' ? (Math.abs(customTotal - amount) < 0.001 ? 'ok' : 'bad') : Math.abs(percentTotal - 100) < 0.001 ? 'ok' : 'bad'}`}>
                  {form.split_method === 'custom' ? (
                    <span>
                      {formatNPR(customTotal)} of {formatNPR(amount)}
                      {Math.abs(customTotal - amount) >= 0.001 && ` · ${formatNPR(Math.abs(round2(amount - customTotal)))} ${customTotal < amount ? 'left' : 'over'}`}
                    </span>
                  ) : (
                    <span>
                      {percentTotal}% of 100%
                      {Math.abs(percentTotal - 100) >= 0.001 && ` · ${round2(Math.abs(100 - percentTotal))}% ${percentTotal < 100 ? 'left' : 'over'}`}
                    </span>
                  )}
                  <button className="link-btn" onClick={fillEqual}>Fill equally</button>
                </div>
              </>
            )}
          </div>
        )}

        {step === 4 && preview && (
          <div className="stack">
            <div className="review-head">
              <CategoryIcon category={preview.category} size={48} />
              <div className="grow">
                <h3>{preview.description}</h3>
                <small className="muted">
                  Paid by {preview.paid_by.id === user.id ? 'you' : preview.paid_by.full_name} · {METHODS.find((m) => m.value === preview.split_method)?.label}
                </small>
              </div>
              <Money value={preview.amount} className="detail-amount" />
            </div>

            <div className="review-me">
              <div>
                <small className="muted">Your share</small>
                <Money value={preview.my_share} className="strong big" />
              </div>
              <div className="right">
                <small className="muted">Effect on your balance</small>
                <Money value={preview.my_balance_effect} tone="auto" sign className="strong big" />
              </div>
            </div>

            <table className="data-table">
              <thead>
                <tr>
                  <th>Person</th>
                  <th className="num">Share</th>
                  <th className="num">Balance change</th>
                </tr>
              </thead>
              <tbody>
                {preview.shares.map((r) => (
                  <tr key={r.user.id}>
                    <td>
                      <span className="row">
                        <Avatar user={r.user} size={26} />
                        {r.user.id === user.id ? 'You' : r.user.full_name}
                        {r.user.id === preview.paid_by.id && <span className="pill tiny">paid</span>}
                      </span>
                    </td>
                    <td className="num">
                      {r.not_participating ? <span className="muted">—</span> : <Money value={r.amount} />}
                      {r.percentage != null && <small className="muted"> ({Number(r.percentage)}%)</small>}
                    </td>
                    <td className="num">
                      <Money value={r.balance_effect} tone="auto" sign />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="muted small">
              {payer?.id === user.id ? 'You' : firstName(payer?.full_name)} will receive the others’ shares; everyone else will give their share.
            </p>

            {!editing && (
              <div className="stack-sm">
                <span className="field-label">Receipt photo (optional)</span>
                {receipt ? (
                  <div className="file-chip" style={{ alignSelf: 'flex-start' }}>
                    <ImagePlus size={16} /> {receipt.name}
                    <button className="icon-btn" onClick={() => setReceipt(null)} aria-label="Remove receipt"><X size={14} /></button>
                  </div>
                ) : (
                  <button className="btn btn-ghost dashed btn-block" onClick={() => fileRef.current?.click()}>
                    <ImagePlus size={17} /> Attach receipt
                  </button>
                )}
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/*"
                  hidden
                  onChange={(e) => {
                    const f = e.target.files[0]
                    if (f && f.size > 5 * 1024 * 1024) return toast('Receipt image must be smaller than 5 MB.', 'error')
                    if (f) setReceipt(f)
                  }}
                />
              </div>
            )}
            {editing && loadedExpense?.receipt && <p className="muted small">The existing receipt stays attached.</p>}
          </div>
        )}

        {error && <div className="alert alert-error">{error}</div>}

        <div className="wizard-actions">
          {step > 0 ? (
            <button className="btn btn-ghost" onClick={back} disabled={busy}><ArrowLeft size={16} /> Back</button>
          ) : (
            <Link className="btn btn-ghost" to={`/groups/${group.id}`}>Cancel</Link>
          )}
          {step < 4 ? (
            <Button onClick={next} loading={busy}>
              {step === 3 ? 'Review' : 'Next'} <ArrowRight size={16} />
            </Button>
          ) : (
            <Button onClick={confirm} loading={busy} className="btn-primary btn-lg">
              <CheckCircle2 size={18} /> {editing ? 'Save changes' : 'Confirm & add expense'}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
