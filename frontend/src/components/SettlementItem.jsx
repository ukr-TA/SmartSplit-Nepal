import { Link } from 'react-router-dom'
import { ArrowRight, FileText } from 'lucide-react'
import { formatDateTime, firstName } from '../utils/format'
import { Avatar, MethodBadge, Money, StatusBadge } from './ui'

export default function SettlementItem({ s, userId, showGroup = false }) {
  const name = (u) => (u.id === userId ? 'You' : firstName(u.full_name))
  return (
    <li className={`settlement-item status-${s.status}`}>
      <div className="si-people">
        <Avatar user={s.payer} size={34} />
        <ArrowRight size={15} className="muted" />
        <Avatar user={s.recipient} size={34} />
      </div>
      <div className="grow si-main">
        <strong>{name(s.payer)} → {name(s.recipient)}</strong>
        <small className="muted">
          {showGroup && <>{s.group_name} · </>}
          {formatDateTime(s.completed_at || s.created_at)}
        </small>
        <small className="mono muted">{s.transaction_id}</small>
      </div>
      <div className="si-right">
        <Money value={s.amount} className="strong" />
        <span className="row">
          <MethodBadge method={s.method} />
          <StatusBadge status={s.status} />
        </span>
        {s.status === 'successful' && (
          <Link to={`/settlements/${s.id}/receipt`} className="link-btn small">
            <FileText size={13} /> Receipt
          </Link>
        )}
        {s.status === 'pending' && s.payer.id === userId && s.channel === 'simulation' && (
          <Link to={`/pay/${s.id}`} className="link-btn small">Continue payment</Link>
        )}
      </div>
    </li>
  )
}
