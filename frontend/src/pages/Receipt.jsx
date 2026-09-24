import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, Clock, Printer, XCircle } from 'lucide-react'
import { settlementApi } from '../api/services'
import { Logo } from '../components/Layout'
import { ErrorState, Spinner } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { formatDateTime, formatNPR } from '../utils/format'
import { WalletLogo } from './SettleUp'

export default function Receipt() {
  const { id } = useParams()
  const { data: s, loading, error } = useApi(() => settlementApi.get(id), [id])

  if (loading) return <Spinner />
  if (error) return <div className="page narrow"><ErrorState message={error} /></div>

  const StatusIcon = s.status === 'successful' ? CheckCircle2 : s.status === 'pending' ? Clock : XCircle

  return (
    <div className="receipt-page">
      <div className="receipt-toolbar no-print">
        <Link to={`/groups/${s.group}/settlements`} className="btn btn-ghost"><ArrowLeft size={16} /> Back to group</Link>
        <button className="btn btn-primary" onClick={() => window.print()}><Printer size={16} /> Print / Save PDF</button>
      </div>

      <article className="receipt">
        <header className="receipt-head">
          <Logo />
          <span className="muted small">Settlement receipt</span>
        </header>

        <div className={`receipt-status status-${s.status}`}>
          <StatusIcon size={36} />
          <div>
            <strong>{s.status === 'successful' ? 'Payment Successful' : s.status_label}</strong>
            <small>{formatDateTime(s.completed_at || s.created_at)}</small>
          </div>
        </div>

        <div className="receipt-amount">{formatNPR(s.amount)}</div>

        <dl className="receipt-rows">
          <div><dt>Paid by</dt><dd>{s.payer.full_name}</dd></div>
          <div><dt>Paid to</dt><dd>{s.recipient.full_name}</dd></div>
          <div><dt>Group</dt><dd>{s.group_name}</dd></div>
          <div>
            <dt>Method</dt>
            <dd className="row"><WalletLogo method={s.method} size={22} /> {s.method_label}</dd>
          </div>
          <div><dt>Mode</dt><dd>{s.channel_label}</dd></div>
          <div><dt>Transaction ID</dt><dd className="mono">{s.transaction_id}</dd></div>
          {s.gateway_reference && <div><dt>Gateway reference</dt><dd className="mono">{s.gateway_reference}</dd></div>}
          {s.note && <div><dt>Note</dt><dd>{s.note}</dd></div>}
          <div><dt>Recorded by</dt><dd>{s.created_by.full_name}</dd></div>
        </dl>

        <footer className="receipt-foot">
          <p>Split less. Settle smarter.</p>
          <small className="muted">
            {s.channel === 'simulation'
              ? 'Demo simulation - no real money was transferred.'
              : s.channel === 'sandbox'
                ? 'Paid through the wallet’s test environment - no real money was transferred.'
                : 'Cash settlement recorded in SmartSplit.'}
          </small>
        </footer>
      </article>
    </div>
  )
}
