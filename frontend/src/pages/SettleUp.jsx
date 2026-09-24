import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Banknote, CheckCircle2, ExternalLink, FlaskConical, ShieldCheck } from 'lucide-react'
import { getErrorMessage } from '../api/client'
import { groupApi, settlementApi } from '../api/services'
import { Avatar, Button, ErrorState, Money, Spinner } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useUI } from '../context/UIContext'
import { PAYMENT_METHODS } from '../utils/constants'
import { firstName, formatNPR, toNumber } from '../utils/format'

export function WalletLogo({ method, size = 40 }) {
  if (method === 'esewa') {
    return (
      <span className="wallet-logo esewa" style={{ width: size, height: size }}>
        <svg viewBox="0 0 40 40" width={size * 0.62} height={size * 0.62} aria-hidden="true">
          <path d="M28 21.5H13.2c.6 4 3.3 6.3 7 6.3 2.6 0 4.6-1.1 5.9-3l2.9 2c-2 2.9-5.1 4.5-8.9 4.5-6.2 0-10.7-4.5-10.7-11s4.4-11 10.4-11c6.1 0 10.3 4.4 10.3 10.8 0 .5 0 1-.1 1.4zM13.3 18.3h11c-.6-3.4-2.8-5.5-5.6-5.5-2.9 0-4.9 2.1-5.4 5.5z" fill="#fff" />
        </svg>
      </span>
    )
  }
  if (method === 'khalti') {
    return (
      <span className="wallet-logo khalti" style={{ width: size, height: size }}>
        <svg viewBox="0 0 40 40" width={size * 0.6} height={size * 0.6} aria-hidden="true">
          <path d="M12 9v22M12 21l11-12M15.5 17.5 26 31" stroke="#fff" strokeWidth="4.2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
          <circle cx="29.5" cy="12" r="3" fill="#f7a81b" />
        </svg>
      </span>
    )
  }
  return (
    <span className="wallet-logo cash" style={{ width: size, height: size }}>
      <Banknote size={size * 0.55} />
    </span>
  )
}

/** Build and auto-submit the signed eSewa form (eSewa requires a POST redirect). */
function submitForm(url, fields) {
  const form = document.createElement('form')
  form.method = 'POST'
  form.action = url
  Object.entries(fields).forEach(([name, value]) => {
    const input = document.createElement('input')
    input.type = 'hidden'
    input.name = name
    input.value = value
    form.appendChild(input)
  })
  document.body.appendChild(form)
  form.submit()
}

export default function SettleUp() {
  const { id, userId } = useParams()
  const [params] = useSearchParams()
  const receiving = params.get('receive') === '1'
  const navigate = useNavigate()
  const { user } = useAuth()
  const { toast } = useUI()

  const [state, setState] = useState({ loading: true })
  const [method, setMethod] = useState(receiving ? 'cash' : null)
  const [channel, setChannel] = useState('simulation')
  const [amount, setAmount] = useState(params.get('amount') ? String(toNumber(params.get('amount'))) : '')
  const [note, setNote] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    Promise.all([groupApi.get(id), groupApi.balances(id), settlementApi.paymentConfig()])
      .then(([group, balances, config]) => setState({ loading: false, group, balances, config }))
      .catch((err) => setState({ loading: false, error: getErrorMessage(err) }))
  }, [id])

  const other = useMemo(
    () => state.group?.members.find((m) => String(m.user.id) === String(userId))?.user,
    [state.group, userId],
  )

  if (state.loading) return <Spinner />
  if (state.error) return <ErrorState message={state.error} />
  if (!other) return <ErrorState message="That person is not a member of this group." />

  const { group, balances, config } = state
  const myNet = toNumber(balances.my_net)
  const theirNet = toNumber(balances.members.find((m) => m.user.id === other.id)?.net)
  // Maximum that can be settled between the two people (mirrors the backend rule)
  const limit = receiving ? Math.min(Math.max(-theirNet, 0), Math.max(myNet, 0)) : Math.min(Math.max(-myNet, 0), Math.max(theirNet, 0))
  const suggested = receiving
    ? toNumber(balances.you_receive.find((r) => r.user.id === other.id)?.amount)
    : toNumber(balances.you_give.find((r) => r.user.id === other.id)?.amount)

  const value = Number(amount) || 0
  const gatewayReady = method && method !== 'cash' ? config[method]?.sandbox : false

  const submit = async () => {
    setError('')
    if (!method) return setError('Choose a payment method.')
    if (!(value > 0)) return setError('Enter an amount greater than zero.')
    if (value > limit + 0.001) return setError(`The most that can be settled with ${firstName(other.full_name)} is ${formatNPR(limit)}.`)
    if (method === 'khalti' && channel === 'sandbox' && value < 10) return setError("Khalti's minimum payment is Rs. 10.")
    setBusy(true)
    try {
      const body = {
        group: group.id,
        recipient: receiving ? user.id : other.id,
        amount: value.toFixed(2),
        method,
        channel: method === 'cash' ? undefined : channel,
        note,
      }
      if (receiving) body.payer = other.id
      const res = await settlementApi.create(body)
      const next = res.next
      if (next.type === 'done') {
        toast(receiving ? 'Cash received recorded' : `Cash payment to ${firstName(other.full_name)} recorded`)
        navigate(`/settlements/${res.settlement.id}/receipt`, { replace: true })
      } else if (next.type === 'simulation') {
        navigate(`/pay/${res.settlement.id}`)
      } else if (next.type === 'form_post') {
        toast('Redirecting to eSewa…', 'info')
        submitForm(next.url, next.fields)
      } else if (next.type === 'redirect') {
        toast('Redirecting to Khalti…', 'info')
        window.location.assign(next.url)
      }
    } catch (err) {
      setError(getErrorMessage(err))
      setBusy(false)
    }
  }

  if (limit <= 0) {
    return (
      <div className="page narrow">
        <Link to={`/groups/${group.id}/balances`} className="back-link"><ArrowLeft size={16} /> {group.name}</Link>
        <div className="card center stack">
          <CheckCircle2 size={40} className="text-receive" style={{ margin: '0 auto' }} />
          <h2>Nothing to settle</h2>
          <p className="muted">
            {receiving ? `${other.full_name} doesn't owe money in this group right now.` : `You don't need to pay ${other.full_name} in ${group.name}.`}
          </p>
          <Link className="btn btn-primary" to={`/groups/${group.id}/balances`}>View balances</Link>
        </div>
      </div>
    )
  }

  const methods = receiving ? ['cash'] : ['esewa', 'khalti', 'cash']

  return (
    <div className="page narrow">
      <Link to={`/groups/${group.id}/balances`} className="back-link"><ArrowLeft size={16} /> {group.name}</Link>

      <div className="pay-hub card">
        <p className="eyebrow center">{receiving ? 'Record money received' : 'Payment hub'}</p>
        <div className="pay-parties">
          <div>
            <Avatar user={receiving ? other : user} size={52} />
            <span>{receiving ? firstName(other.full_name) : 'You'}</span>
          </div>
          <ArrowRight size={22} className="muted" />
          <div>
            <Avatar user={receiving ? user : other} size={52} />
            <span>{receiving ? 'You' : firstName(other.full_name)}</span>
          </div>
        </div>
        <h2 className="center">{receiving ? `Cash from ${other.full_name}` : `Settle with ${other.full_name}`}</h2>

        <div className="pay-amount">
          <label htmlFor="pay-amount" className="muted small">Amount</label>
          <div className="amount-input xl">
            <span>Rs.</span>
            <input id="pay-amount" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value.replace(/[^\d.]/g, ''))} />
          </div>
          <div className="row center-row">
            {suggested > 0 && Math.abs(value - suggested) > 0.001 && (
              <button className="chip" onClick={() => setAmount(String(suggested))}>Suggested {formatNPR(suggested)}</button>
            )}
            <small className="muted">Up to <Money value={limit} /> in this group</small>
          </div>
        </div>

        <div className="stack-sm">
          <span className="field-label">Choose payment method</span>
          {methods.map((m) => (
            <button key={m} className={`method-card ${method === m ? 'selected' : ''}`} onClick={() => setMethod(m)}>
              <WalletLogo method={m} />
              <span className="grow">
                <strong>{PAYMENT_METHODS[m].label}</strong>
                <small className="muted">{receiving ? 'Mark cash you received in person' : PAYMENT_METHODS[m].tagline}</small>
              </span>
              <span className="radio" />
            </button>
          ))}
        </div>

        {method && method !== 'cash' && (
          <div className="channel-box">
            <span className="field-label">Payment mode</span>
            <div className="segmented">
              <button className={channel === 'simulation' ? 'active' : ''} onClick={() => setChannel('simulation')}>
                <FlaskConical size={15} /> Demo simulation
              </button>
              <button
                className={channel === 'sandbox' ? 'active' : ''}
                disabled={!gatewayReady}
                onClick={() => setChannel('sandbox')}
                title={gatewayReady ? '' : `${PAYMENT_METHODS[method].label} test gateway is not configured`}
              >
                <ExternalLink size={15} /> {PAYMENT_METHODS[method].label} test gateway
              </button>
            </div>
            <small className="muted">
              {channel === 'simulation'
                ? `Opens an in-app ${PAYMENT_METHODS[method].label} screen and generates a mock transaction ID. Works offline.`
                : method === 'esewa'
                  ? 'Redirects to eSewa’s official test site. Log in with test ID 9806800001, password Nepal@123, token 123456.'
                  : 'Redirects to Khalti’s sandbox. Use test ID 9800000001, MPIN 1111, OTP 987654.'}
              {!gatewayReady && channel === 'simulation' && method === 'khalti' && ' (Add KHALTI_SECRET_KEY in backend/.env to enable the Khalti test gateway.)'}
            </small>
          </div>
        )}

        <input className="input" placeholder="Add a note (optional)" value={note} maxLength={200} onChange={(e) => setNote(e.target.value)} />

        {error && <div className="alert alert-error">{error}</div>}

        <Button onClick={submit} loading={busy} disabled={!method} className="btn-primary btn-lg btn-block">
          {method === 'cash' ? (receiving ? 'Mark as received' : 'Mark as paid') : 'Continue'} {value > 0 && `· ${formatNPR(value)}`}
        </Button>
        <p className="muted small center">
          <ShieldCheck size={13} /> Balances update only after a payment succeeds.
        </p>
      </div>
    </div>
  )
}
