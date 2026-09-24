import { Link } from 'react-router-dom'
import {
  ArrowDownLeft, ArrowRight, ArrowUpRight, CheckCircle2, HandCoins, Plus, Scale, Users, Wallet,
} from 'lucide-react'
import { miscApi } from '../api/services'
import {
  Avatar, CardSkeleton, CategoryIcon, EmptyState, ErrorState, MethodBadge, Money,
} from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useApi } from '../hooks/useApi'
import { groupTypeOf } from '../utils/constants'
import { firstName, formatDate, formatNPR, timeAgo, toNumber } from '../utils/format'

function StatCard({ label, value, count, icon: Icon, tone, hint, sign }) {
  return (
    <div className={`stat-card tone-${tone}`}>
      <span className="stat-icon">
        <Icon size={20} />
      </span>
      <span className="stat-label">{label}</span>
      {count != null ? <strong className="stat-value">{count}</strong> : <Money value={value} sign={sign} className="stat-value" />}
      {hint && <span className="stat-hint">{hint}</span>}
    </div>
  )
}

function ActionList({ title, rows, kind }) {
  const give = kind === 'give'
  return (
    <div className="card">
      <div className="card-head">
        <h3>{title}</h3>
        <span className={`pill ${give ? 'pill-give' : 'pill-receive'}`}>{rows.length}</span>
      </div>
      {rows.length === 0 ? (
        <p className="muted small">{give ? "Nothing to pay. You're all clear." : 'Nobody owes you right now.'}</p>
      ) : (
        <ul className="action-list">
          {rows.slice(0, 5).map((r) => (
            <li key={`${r.group.id}-${r.user.id}`}>
              <Avatar user={r.user} size={38} />
              <div className="grow">
                <strong>{r.user.full_name}</strong>
                <small className="muted">{r.group.name}</small>
              </div>
              <Money value={r.amount} tone={give ? 'give' : 'receive'} className="strong" />
              {give ? (
                <Link className="btn btn-sm btn-primary" to={`/groups/${r.group.id}/settle/${r.user.id}?amount=${r.amount}`}>
                  Settle
                </Link>
              ) : (
                <Link className="btn btn-sm btn-ghost" to={`/groups/${r.group.id}/balances`}>
                  View
                </Link>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  const { data, loading, error, reload } = useApi(() => miscApi.dashboard(), [])

  if (error) return <ErrorState message={error} onRetry={reload} />

  const s = data?.summary
  const net = toNumber(s?.net_balance)
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'

  return (
    <div className="page">
      <div className="hero-row">
        <div>
          <p className="eyebrow">{greeting}</p>
          <h1>Namaste, {firstName(user?.full_name)} 👋</h1>
          <p className="muted">
            {loading
              ? 'Loading your balances…'
              : net > 0
                ? `Overall, you should receive ${formatNPR(Math.abs(net))}.`
                : net < 0
                  ? `Overall, you need to give ${formatNPR(Math.abs(net))}.`
                  : 'You are all settled up.'}
          </p>
        </div>
        <div className="hero-actions">
          <Link to="/groups/new" className="btn btn-ghost">
            <Users size={17} /> New group
          </Link>
          <Link to="/split" className="btn btn-primary btn-lg">
            <Plus size={18} /> Split Expense
          </Link>
        </div>
      </div>

      {loading ? (
        <div className="stat-grid">
          {[1, 2, 3, 4].map((i) => <CardSkeleton key={i} rows={2} />)}
        </div>
      ) : (
        <div className="stat-grid">
          <StatCard label="You need to give" value={s.you_owe} icon={ArrowUpRight} tone="give" hint={`${data.should_pay.length} payment${data.should_pay.length === 1 ? '' : 's'} to make`} />
          <StatCard label="You will receive" value={s.you_are_owed} icon={ArrowDownLeft} tone="receive" hint={`from ${data.should_receive.length} ${data.should_receive.length === 1 ? 'person' : 'people'}`} />
          <StatCard label="Net balance" value={s.net_balance} sign icon={Scale} tone={net > 0 ? 'receive' : net < 0 ? 'give' : 'neutral'} hint={net === 0 ? 'All settled' : net > 0 ? 'In your favour' : 'You owe overall'} />
          <StatCard label="Active groups" count={s.active_groups} icon={Users} tone="brand" hint={`My share this month: ${formatNPR(s.my_spending_this_month)}`} />
        </div>
      )}

      {!loading && data.groups.length === 0 && (
        <div className="card">
          <EmptyState
            icon={Users}
            title="Start your first group"
            message="Create a group for a trip, your flat or a college project, add friends by phone number, then split your first expense."
            action={<Link to="/groups/new" className="btn btn-primary"><Plus size={16} /> Create group</Link>}
          />
        </div>
      )}

      {!loading && data.groups.length > 0 && (
        <>
          <div className="grid-2 align-start">
            <ActionList title="You should pay" rows={data.should_pay} kind="give" />
            <ActionList title="You should receive" rows={data.should_receive} kind="receive" />
          </div>

          <div className="grid-3-1 align-start">
            <div className="card">
              <div className="card-head">
                <h3>Recent expenses</h3>
                <Link to="/groups" className="link-btn">All groups <ArrowRight size={14} /></Link>
              </div>
              {data.recent_expenses.length === 0 ? (
                <p className="muted small">No expenses yet. Tap “Split Expense” to add one.</p>
              ) : (
                <ul className="expense-mini-list">
                  {data.recent_expenses.map((e) => (
                    <li key={e.id}>
                      <Link to={`/groups/${e.group.id}/expenses`} className="expense-mini">
                        <CategoryIcon category={e.category} size={40} />
                        <div className="grow">
                          <strong>{e.description}</strong>
                          <small className="muted">
                            {e.paid_by.id === user.id ? 'You' : firstName(e.paid_by.full_name)} paid · {e.group.name} · {formatDate(e.date)}
                          </small>
                        </div>
                        <div className="right">
                          <Money value={e.amount} className="strong" />
                          <small className="muted">your share <Money value={e.my_share} /></small>
                        </div>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="stack">
              <div className="card">
                <div className="card-head">
                  <h3>Your groups</h3>
                  <Link to="/groups" className="link-btn">See all</Link>
                </div>
                <ul className="group-mini-list">
                  {data.groups.slice(0, 5).map((g) => {
                    const Icon = groupTypeOf(g.group_type).icon
                    return (
                      <li key={g.id}>
                        <Link to={`/groups/${g.id}`} className="group-mini">
                          <span className="group-icon sm"><Icon size={17} /></span>
                          <span className="grow">
                            <strong>{g.name}</strong>
                            <small className="muted">{g.member_count} members</small>
                          </span>
                          {toNumber(g.my_net) === 0 ? (
                            <span className="muted small"><CheckCircle2 size={14} /> settled</span>
                          ) : (
                            <Money value={g.my_net} tone="auto" sign className="small strong" />
                          )}
                        </Link>
                      </li>
                    )
                  })}
                </ul>
              </div>

              <div className="card">
                <div className="card-head">
                  <h3>Recent settlements</h3>
                  <Link to="/settlements" className="link-btn">History</Link>
                </div>
                {data.recent_settlements.length === 0 ? (
                  <p className="muted small"><HandCoins size={14} /> No settlements yet.</p>
                ) : (
                  <ul className="settle-mini-list">
                    {data.recent_settlements.map((st) => (
                      <li key={st.id}>
                        <Link to={`/settlements/${st.id}/receipt`}>
                          <span className="grow">
                            <strong>
                              {st.payer.id === user.id ? 'You' : firstName(st.payer.full_name)} → {st.recipient.id === user.id ? 'You' : firstName(st.recipient.full_name)}
                            </strong>
                            <small className="muted">{st.group_name} · {formatDate(st.created_at)}</small>
                          </span>
                          <span className="right">
                            <Money value={st.amount} className="strong" />
                            <MethodBadge method={st.method} />
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-head">
              <h3>Recent activity</h3>
              <Link to="/activity" className="link-btn">View all</Link>
            </div>
            <ul className="timeline compact">
              {data.recent_activity.map((a) => (
                <li key={a.id} className={`tl-${a.action}`}>
                  <span className="tl-dot" />
                  <div>
                    <p>
                      {a.description}
                      {a.amount && <> · <Money value={a.amount} className="strong" /></>}
                    </p>
                    <small className="muted">{a.group_name} · {timeAgo(a.created_at)}</small>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
      <p className="muted small center">
        <Wallet size={13} /> Amounts in Nepali Rupees (NPR)
      </p>
    </div>
  )
}
