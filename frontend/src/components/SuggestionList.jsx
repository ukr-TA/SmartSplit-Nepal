import { Link } from 'react-router-dom'
import { ArrowRight, CheckCircle2, Sparkles } from 'lucide-react'
import { firstName } from '../utils/format'
import { Avatar, Money } from './ui'

/** Smart settlement plan: "Utsuk → Sita  Rs. 500  [Settle]" */
export default function SuggestionList({ groupId, suggestions, userId, stats, compact = false }) {
  if (!suggestions.length) {
    return (
      <div className="settled-banner">
        <CheckCircle2 size={22} />
        <div>
          <strong>Everyone is settled up</strong>
          <small>No payments needed in this group.</small>
        </div>
      </div>
    )
  }

  return (
    <div className="stack-sm">
      {stats && !compact && stats.direct_transactions > stats.smart_transactions && (
        <div className="smart-banner">
          <Sparkles size={18} />
          <span>
            Smart settlement needs <strong>{stats.smart_transactions}</strong> payment{stats.smart_transactions === 1 ? '' : 's'} instead of{' '}
            <strong>{stats.direct_transactions}</strong> — {stats.direct_transactions - stats.smart_transactions} fewer transfers.
          </span>
        </div>
      )}
      <ul className="suggestions">
        {suggestions.map((s) => {
          const mePaying = s.from_user.id === userId
          const meReceiving = s.to_user.id === userId
          return (
            <li key={`${s.from_user.id}-${s.to_user.id}`} className={mePaying ? 'mine-give' : meReceiving ? 'mine-receive' : ''}>
              <div className="sug-people">
                <span className="sug-person">
                  <Avatar user={s.from_user} size={34} />
                  <span>{mePaying ? 'You' : firstName(s.from_user.full_name)}</span>
                </span>
                <span className="sug-arrow">
                  <ArrowRight size={16} />
                </span>
                <span className="sug-person">
                  <Avatar user={s.to_user} size={34} />
                  <span>{meReceiving ? 'You' : firstName(s.to_user.full_name)}</span>
                </span>
              </div>
              <Money value={s.amount} className="sug-amount" />
              {mePaying ? (
                <Link className="btn btn-sm btn-primary" to={`/groups/${groupId}/settle/${s.to_user.id}?amount=${s.amount}`}>
                  Settle
                </Link>
              ) : meReceiving ? (
                <Link className="btn btn-sm btn-ghost" to={`/groups/${groupId}/settle/${s.from_user.id}?amount=${s.amount}&receive=1`}>
                  Record cash
                </Link>
              ) : (
                <span className="sug-spacer" />
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
