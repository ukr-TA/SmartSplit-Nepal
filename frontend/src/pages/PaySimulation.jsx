import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { CheckCircle2, FlaskConical, Lock, XCircle } from 'lucide-react'
import { getErrorMessage } from '../api/client'
import { settlementApi } from '../api/services'
import { Button, ErrorState, Spinner } from '../components/ui'
import { useUI } from '../context/UIContext'
import { formatDateTime, formatNPR } from '../utils/format'
import { WalletLogo } from './SettleUp'

/**
 * In-app eSewa / Khalti payment simulation.
 * Looks like a wallet checkout, generates a mock transaction and records the settlement.
 */
export default function PaySimulation() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { toast, confirm } = useUI()
  const [s, setS] = useState(null)
  const [error, setError] = useState('')
  const [pin, setPin] = useState('')
  const [phase, setPhase] = useState('confirm') // confirm | processing | done | failed
  const [formError, setFormError] = useState('')

  useEffect(() => {
    settlementApi
      .get(id)
      .then((data) => {
        setS(data)
        if (data.status === 'successful') setPhase('done')
        if (data.status === 'failed') setPhase('failed')
      })
      .catch((err) => setError(getErrorMessage(err)))
  }, [id])

  if (error) return <div className="page narrow"><ErrorState message={error} /></div>
  if (!s) return <Spinner />
  if (s.method === 'cash' || s.channel !== 'simulation') {
    return <div className="page narrow"><ErrorState message="This settlement is not a simulated wallet payment." /></div>
  }

  const isKhalti = s.method === 'khalti'
  const brand = isKhalti ? 'Khalti' : 'eSewa'

  const pay = async () => {
    setFormError('')
    if (isKhalti && !/^\d{4}$/.test(pin)) return setFormError('Enter your 4-digit Khalti MPIN (any 4 digits in the demo).')
    setPhase('processing')
    try {
      // short pause so the demo feels like a real wallet
      const [res] = await Promise.all([settlementApi.confirm(s.id, pin), new Promise((r) => setTimeout(r, 1400))])
      setS(res.settlement)
      setPhase('done')
      toast(`Payment successful · ${res.settlement.transaction_id}`)
    } catch (err) {
      setFormError(getErrorMessage(err))
      setPhase('confirm')
    }
  }

  const cancel = async () => {
    if (!(await confirm({ title: 'Cancel this payment?', message: 'No money will be moved and balances stay the same.', confirmText: 'Cancel payment', cancelText: 'Keep paying', danger: true }))) return
    try {
      const res = await settlementApi.cancel(s.id)
      setS(res.settlement)
      setPhase('failed')
    } catch (err) {
      setFormError(getErrorMessage(err))
    }
  }

  return (
    <div className={`wallet-page ${s.method}`}>
      <div className="sim-ribbon"><FlaskConical size={14} /> Demo simulation — no real money is moved</div>
      <div className="wallet-card">
        <div className="wallet-top">
          <WalletLogo method={s.method} size={46} />
          <div>
            <strong>{brand} {phase === 'done' ? '' : 'Payment'}</strong>
            <small>SmartSplit Nepal · Merchant checkout</small>
          </div>
        </div>

        {phase === 'confirm' || phase === 'processing' ? (
          <div className="wallet-body">
            <dl className="wallet-rows">
              <div><dt>{isKhalti ? 'Recipient' : 'Pay to'}</dt><dd>{s.recipient.full_name}</dd></div>
              <div><dt>Amount</dt><dd className="wallet-amount">{formatNPR(s.amount)}</dd></div>
              <div><dt>Group</dt><dd>{s.group_name}</dd></div>
              <div><dt>Transaction ID</dt><dd className="mono">{s.transaction_id}</dd></div>
            </dl>
            {isKhalti && (
              <label className="field">
                <span className="field-label">Khalti MPIN</span>
                <input className="input pin-input" type="password" inputMode="numeric" maxLength={4} placeholder="••••" value={pin} onChange={(e) => {
                    setPin(e.target.value.replace(/\D/g, ''))
                    setFormError('')
                  }} autoFocus />
                <span className="field-hint">Demo: any 4 digits, e.g. 1111</span>
              </label>
            )}
            {formError && <div className="alert alert-error">{formError}</div>}
            <Button onClick={pay} loading={phase === 'processing'} className={`btn-lg btn-block wallet-btn ${s.method}`}>
              {phase === 'processing' ? 'Processing payment…' : `Confirm Payment · ${formatNPR(s.amount)}`}
            </Button>
            <button className="link-btn center-block" onClick={cancel} disabled={phase === 'processing'}>Cancel</button>
            <p className="wallet-secure"><Lock size={12} /> Secured checkout (simulated)</p>
          </div>
        ) : phase === 'done' ? (
          <div className="wallet-body center">
            <CheckCircle2 size={64} className="success-pop" />
            <h2>Payment Successful</h2>
            <dl className="wallet-rows">
              <div><dt>Paid to</dt><dd>{s.recipient.full_name}</dd></div>
              <div><dt>Amount</dt><dd className="wallet-amount">{formatNPR(s.amount)}</dd></div>
              <div><dt>Transaction ID</dt><dd className="mono">{s.transaction_id}</dd></div>
              <div><dt>{brand} reference</dt><dd className="mono">{s.gateway_reference}</dd></div>
              <div><dt>Date</dt><dd>{formatDateTime(s.completed_at)}</dd></div>
            </dl>
            <div className="stack-sm">
              <Link className={`btn btn-lg btn-block wallet-btn ${s.method}`} to={`/settlements/${s.id}/receipt`}>View receipt</Link>
              <button className="btn btn-ghost btn-block" onClick={() => navigate(`/groups/${s.group}/balances`)}>Back to balances</button>
            </div>
          </div>
        ) : (
          <div className="wallet-body center">
            <XCircle size={60} className="text-give" />
            <h2>Payment cancelled</h2>
            <p className="muted">No money was moved. Your balance is unchanged.</p>
            <button className="btn btn-primary btn-block" onClick={() => navigate(`/groups/${s.group}/balances`)}>Back to balances</button>
          </div>
        )}
      </div>
    </div>
  )
}
