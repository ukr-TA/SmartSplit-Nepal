import { useState } from 'react'
import { BarChart3, CalendarDays, Crown, Table2, TrendingUp, Users, Wallet } from 'lucide-react'
import { groupApi } from '../../api/services'
import { ColumnChart, HBarList } from '../../components/charts'
import { Avatar, CardSkeleton, CategoryIcon, EmptyState, ErrorState, Money } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { categoryOf } from '../../utils/constants'
import { formatDate, formatNPR, formatShortDate, toNumber } from '../../utils/format'

export default function AnalyticsTab({ group, user, version }) {
  const { data, loading, error, reload } = useApi(() => groupApi.analytics(group.id), [group.id, version])
  const [showTable, setShowTable] = useState(false)

  if (error) return <ErrorState message={error} onRetry={reload} />
  if (loading) return <CardSkeleton rows={6} />
  if (!toNumber(data.total_spent)) {
    return (
      <div className="card">
        <EmptyState icon={BarChart3} title="No spending yet" message="Trip analytics appear once the first expense is added." />
      </div>
    )
  }

  const categories = data.by_category.map((c) => ({ ...c, key: c.category, value: toNumber(c.amount) }))
  const members = data.by_member.map((m) => ({ ...m, key: m.user.id, value: toNumber(m.paid), marker: toNumber(m.share) }))
  const daily = data.daily.map((d) => ({ date: d.date, value: toNumber(d.amount) }))
  const memberMax = Math.max(...members.map((m) => Math.max(m.value, m.marker)), 1)
  const top = categories[0]

  return (
    <div className="stack">
      <div className="trip-hero">
        <div>
          <p className="eyebrow light">{data.is_trip ? 'Trip dashboard' : 'Group insights'}</p>
          <h2>{data.name}</h2>
          {data.start_date && (
            <p className="light-muted">
              <CalendarDays size={14} /> {formatDate(data.start_date)}
              {data.end_date && ` – ${formatDate(data.end_date)}`} · {data.days} day{data.days === 1 ? '' : 's'}
            </p>
          )}
        </div>
        <div className="trip-total">
          <span className="light-muted">Total spending</span>
          <strong>{formatNPR(data.total_spent)}</strong>
        </div>
      </div>

      <div className="stat-grid">
        <div className="stat-card tone-neutral">
          <span className="stat-icon"><TrendingUp size={18} /></span>
          <span className="stat-label">Average per day</span>
          <Money value={data.average_per_day} className="stat-value" />
        </div>
        <div className="stat-card tone-neutral">
          <span className="stat-icon"><Users size={18} /></span>
          <span className="stat-label">Average per person</span>
          <Money value={data.average_per_person} className="stat-value" />
          <span className="stat-hint">{data.member_count} members</span>
        </div>
        <div className="stat-card tone-neutral">
          <span className="stat-icon"><Wallet size={18} /></span>
          <span className="stat-label">Expenses</span>
          <strong className="stat-value">{data.expense_count}</strong>
        </div>
        <div className="stat-card tone-neutral">
          <span className="stat-icon"><Crown size={18} /></span>
          <span className="stat-label">Biggest category</span>
          <strong className="stat-value small-value">{top ? categoryOf(top.category).label : '-'}</strong>
          {top && <span className="stat-hint">{Number(top.percentage)}% of spending</span>}
        </div>
      </div>

      <div className="grid-2 align-start">
        <div className="card">
          <div className="card-head">
            <h3>Spending by category</h3>
          </div>
          <HBarList
            rows={categories}
            renderLabel={(c) => (
              <>
                <CategoryIcon category={c.category} size={26} /> {c.label}
                <small className="muted"> · {c.count}</small>
              </>
            )}
            renderValue={(c) => (
              <>
                <strong>{formatNPR(c.amount)}</strong> <span className="muted pct">{Number(c.percentage)}%</span>
              </>
            )}
          />
        </div>

        <div className="card">
          <div className="card-head">
            <h3>Spending by member</h3>
            <span className="legend">
              <span className="legend-item"><span className="legend-bar" /> Paid</span>
              <span className="legend-item"><span className="legend-tick" /> Fair share</span>
            </span>
          </div>
          <HBarList
            rows={members}
            max={memberMax}
            marker
            renderLabel={(m) => (
              <>
                <Avatar user={m.user} size={24} /> {m.user.id === user.id ? 'You' : m.user.full_name}
              </>
            )}
            renderValue={(m) => (
              <>
                <strong>{formatNPR(m.paid)}</strong> <span className="muted pct">share {formatNPR(m.share)}</span>
              </>
            )}
          />
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <h3>Daily spending</h3>
          <button className="link-btn" onClick={() => setShowTable((s) => !s)}>
            <Table2 size={15} /> {showTable ? 'Show chart' : 'Show table'}
          </button>
        </div>
        {showTable ? (
          <table className="data-table">
            <thead>
              <tr><th>Date</th><th className="num">Amount</th></tr>
            </thead>
            <tbody>
              {daily.map((d) => (
                <tr key={d.date}><td>{formatShortDate(d.date)}</td><td className="num">{formatNPR(d.value)}</td></tr>
              ))}
            </tbody>
          </table>
        ) : (
          <ColumnChart points={daily} />
        )}
      </div>

      {data.top_expenses.length > 0 && (
        <div className="card">
          <div className="card-head"><h3>Biggest expenses</h3></div>
          <ul className="mini-expenses">
            {data.top_expenses.map((e) => (
              <li key={e.id}>
                <CategoryIcon category={e.category} size={32} />
                <span className="grow">
                  {e.description}
                  <small className="muted"> · {e.paid_by} · {formatDate(e.date)}</small>
                </span>
                <Money value={e.amount} className="strong" />
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
