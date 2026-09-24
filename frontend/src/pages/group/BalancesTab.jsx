import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown, HelpCircle } from 'lucide-react'
import { groupApi } from '../../api/services'
import SuggestionList from '../../components/SuggestionList'
import { Avatar, CardSkeleton, CategoryIcon, ErrorState, Money } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { formatDate, toNumber } from '../../utils/format'

function NetBar({ value, max }) {
  const n = toNumber(value)
  const pct = max ? Math.min(Math.abs(n) / max, 1) * 50 : 0
  return (
    <div className="net-bar" aria-hidden="true">
      <span className="net-mid" />
      {n !== 0 && (
        <span
          className={`net-fill ${n > 0 ? 'pos' : 'neg'}`}
          style={n > 0 ? { left: '50%', width: `${pct}%` } : { right: '50%', width: `${pct}%` }}
        />
      )}
    </div>
  )
}

function PersonCard({ row, groupId }) {
  const [open, setOpen] = useState(false)
  const give = toNumber(row.you_give)
  const receive = toNumber(row.you_receive)
  const direct = toNumber(row.direct_net)
  return (
    <div className="person-card">
      <div className="person-row">
        <Avatar user={row.user} size={42} />
        <div className="grow">
          <strong>{row.user.full_name}</strong>
          {give > 0 ? (
            <small className="text-give">You give <Money value={give} className="strong" /></small>
          ) : receive > 0 ? (
            <small className="text-receive">Gives you <Money value={receive} className="strong" /></small>
          ) : (
            <small className="muted">Nothing to settle with them</small>
          )}
        </div>
        {give > 0 && (
          <Link className="btn btn-sm btn-primary" to={`/groups/${groupId}/settle/${row.user.id}?amount=${give}`}>
            Settle with {row.user.full_name.split(' ')[0]}
          </Link>
        )}
        {row.shared_expenses.length > 0 && (
          <button className={`icon-btn ${open ? 'rotated' : ''}`} onClick={() => setOpen((o) => !o)} aria-label="Show shared expenses">
            <ChevronDown size={18} />
          </button>
        )}
      </div>
      {open && (
        <div className="person-detail">
          {direct !== 0 && (
            <p className="muted small">
              From shared expenses alone, {direct > 0 ? `${row.user.full_name.split(' ')[0]} owes you` : 'you owe them'}{' '}
              <Money value={Math.abs(direct)} className="strong" />. Smart settlement may route this through other members.
            </p>
          )}
          <ul className="mini-expenses">
            {row.shared_expenses.map((e) => (
              <li key={e.id}>
                <CategoryIcon category={e.category} size={28} />
                <span className="grow">
                  {e.description}
                  <small className="muted"> · {formatDate(e.date)}</small>
                </span>
                <small className={e.direction === 'you_owe' ? 'text-give' : 'text-receive'}>
                  {e.direction === 'you_owe' ? 'you owe ' : 'they owe '}
                  <Money value={e.amount} />
                </small>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default function BalancesTab({ group, user, version }) {
  const { data, loading, error, reload } = useApi(() => groupApi.balances(group.id), [group.id, version])
  const [explain, setExplain] = useState(false)

  if (error) return <ErrorState message={error} onRetry={reload} />
  if (loading) return <CardSkeleton rows={5} />

  const max = Math.max(...data.members.map((m) => Math.abs(toNumber(m.net))), 1)

  return (
    <div className="stack">
      <div className="grid-2 align-start">
        <div className="card">
          <div className="card-head">
            <h3>Suggested settlements</h3>
            <button className="link-btn" onClick={() => setExplain((e) => !e)}>
              <HelpCircle size={15} /> How it works
            </button>
          </div>
          {explain && (
            <div className="explain-box">
              <ol>
                <li><strong>Net balance</strong> = what a person paid − their share of expenses + settlements they paid − settlements they received.</li>
                <li>Positive balances <span className="text-receive">receive</span>; negative balances <span className="text-give">give</span>. They always add up to zero.</li>
                <li>Exact matches are paired first, then the biggest giver pays the biggest receiver, again and again.</li>
                <li>Every payment clears at least one person, so a group of <em>n</em> people needs at most <em>n − 1</em> payments.</li>
              </ol>
            </div>
          )}
          <SuggestionList groupId={group.id} suggestions={data.suggestions} userId={user.id} stats={data.stats} />
        </div>

        <div className="card">
          <div className="card-head">
            <h3>Group balances</h3>
            <small className="muted">Total <Money value={data.total_spent} /></small>
          </div>
          <ul className="balance-table">
            {data.members.map((m) => {
              const n = toNumber(m.net)
              return (
                <li key={m.user.id} title={`Paid ${m.paid} · Share ${m.share} · Settled +${m.settlements_paid} / −${m.settlements_received}`}>
                  <Avatar user={m.user} size={34} />
                  <div className="grow">
                    <strong>
                      {m.user.id === user.id ? 'You' : m.user.full_name}
                      {!m.is_member && <span className="pill tiny">left</span>}
                    </strong>
                    <small className="muted">
                      paid <Money value={m.paid} /> · share <Money value={m.share} />
                    </small>
                    <NetBar value={m.net} max={max} />
                  </div>
                  <div className="right">
                    <small className={n > 0 ? 'text-receive' : n < 0 ? 'text-give' : 'muted'}>
                      {n > 0 ? 'receives' : n < 0 ? 'gives' : 'settled'}
                    </small>
                    {n !== 0 && <Money value={Math.abs(n)} tone={n > 0 ? 'receive' : 'give'} className="strong" />}
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <h3>Your balance with each member</h3>
        </div>
        {data.individual.length === 0 ? (
          <p className="muted small">You don't share any expenses with other members yet.</p>
        ) : (
          <div className="stack-sm">
            {data.individual.map((row) => (
              <PersonCard key={row.user.id} row={row} groupId={group.id} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
