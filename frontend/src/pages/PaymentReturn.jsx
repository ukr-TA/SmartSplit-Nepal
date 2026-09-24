import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { XCircle } from 'lucide-react'
import { getErrorMessage } from '../api/client'
import { settlementApi } from '../api/services'
import { Spinner } from '../components/ui'
import { useUI } from '../context/UIContext'

/**
 * Landing page after a real eSewa / Khalti test-gateway payment.
 *   /payments/esewa/success/:id?data=...
 *   /payments/esewa/failure/:id
 *   /payments/khalti/return/:id?pidx=...&status=...
 * The backend verifies the payment before anything is recorded.
 */
export default function PaymentReturn() {
  const { gateway, result, id } = useParams()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { toast } = useUI()
  const [error, setError] = useState('')
  const [settlement, setSettlement] = useState(null)
  const started = useRef(false)

  useEffect(() => {
    if (started.current) return
    started.current = true
    const verify = async () => {
      try {
        let res
        if (gateway === 'esewa') {
          res = result === 'failure'
            ? await settlementApi.verifyEsewa(id, { failed: true })
            : await settlementApi.verifyEsewa(id, { data: params.get('data') || '' })
        } else {
          res = await settlementApi.verifyKhalti(id, params.get('pidx') || '')
        }
        const s = res.settlement
        if (s.status === 'successful') {
          toast(`Payment verified · ${s.transaction_id}`)
          navigate(`/settlements/${s.id}/receipt`, { replace: true })
        } else {
          setSettlement(s)
          setError(
            s.status === 'failed'
              ? 'The payment was cancelled or failed. Your balance has not changed.'
              : `The payment is still ${res.next?.gateway_status || 'pending'}. Try again in a moment.`,
          )
        }
      } catch (err) {
        setError(getErrorMessage(err))
      }
    }
    verify()
  }, [gateway, result, id, params, navigate, toast])

  if (!error) return <Spinner label={`Verifying your ${gateway === 'esewa' ? 'eSewa' : 'Khalti'} payment…`} />

  return (
    <div className="wallet-page">
      <div className="wallet-card">
        <div className="wallet-body center">
          <XCircle size={56} className="text-give" />
          <h2>Payment not completed</h2>
          <p className="muted">{error}</p>
          <Link className="btn btn-primary btn-block" to={settlement ? `/groups/${settlement.group}/balances` : '/'}>
            Back to SmartSplit
          </Link>
        </div>
      </div>
    </div>
  )
}
