import { Minus, Sparkles, TrendingDown, TrendingUp } from 'lucide-react'
import { groupApi } from '../api/services'
import { useApi } from '../hooks/useApi'
import { CardSkeleton, EmptyState } from './ui'
import { formatNPR } from '../utils/format'

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function monthLabel(key) {
  const [year, month] = key.split('-')
  return `${MONTH_NAMES[Number(month) - 1]} ${year.slice(2)}`
}


/**
 * What a group might spend next month, from the regression model trained in
 * ml/notebooks/smartsplit_ml.ipynb, with a one- or two-sentence reason underneath (for example,
 * Dashain falling next month).
 * The prediction is shown as a range because the notebook measures a mean absolute percentage
 * error of roughly 40% on held-out months.
 */
export default function ForecastCard({ group, version }) {
  const { data, loading, error } = useApi(() => groupApi.forecast(group.id), [group.id, version])

  if (loading) return <CardSkeleton rows={3} />
  if (error || !data) return null

  if (!data.ready) {
    return (
      <div className="card">
        <div className="card-head">
          <h3><Sparkles size={16} /> Spending forecast</h3>
        </div>
        <EmptyState
          icon={TrendingUp}
          title="Not enough history yet"
          message={data.reason || 'A few months of expenses are needed before a forecast is useful.'}
        />
      </div>
    )
  }

  const why = data.explanation || {}
  const history = data.history.slice(-9)
  const bars = [
    ...history.map((row) => ({ key: row.month, value: row.total, predicted: false })),
    { key: data.month, value: data.predicted_total, predicted: true },
  ]
  const max = Math.max(...bars.map((bar) => bar.value), data.upper, 1)
  const change = why.change_vs_average ?? 0
  const DirectionIcon = why.direction === 'up' ? TrendingUp : why.direction === 'down' ? TrendingDown : Minus

  return (
    <div className="card forecast-card">
      <div className="card-head">
        <h3><Sparkles size={16} /> Spending forecast</h3>
        <span className="pill">{data.model}</span>
      </div>

      <div className="forecast-headline">
        <div>
          <span className="muted small">{monthLabel(data.month)} might cost around</span>
          <strong className="forecast-value">{formatNPR(Math.round(data.predicted_total))}</strong>
          <span className="muted small">
            could be anywhere from {formatNPR(Math.round(data.lower))} to {formatNPR(Math.round(data.upper))}
          </span>
        </div>
        <div className={`forecast-delta ${why.direction || 'same'}`}>
          <span><DirectionIcon size={15} /> {change >= 0 ? '+' : ''}{Math.round(change * 100)}%</span>
          <small>possible change vs your average</small>
        </div>
      </div>

      <div className="forecast-chart" role="img" aria-label="Monthly spending history and prediction">
        {bars.map((bar) => (
          <div key={bar.key} className={`forecast-col ${bar.predicted ? 'is-predicted' : ''}`}>
            <span className="forecast-amount">{Math.round(bar.value / 1000)}k</span>
            <span className="forecast-bar" style={{ height: `${Math.max((bar.value / max) * 100, 2)}%` }} />
            <span className="forecast-x">{monthLabel(bar.key)}</span>
          </div>
        ))}
      </div>

      {why.summary && (
        <p className="forecast-summary">
          <Sparkles size={15} />
          <span>{why.summary}</span>
        </p>
      )}

      <p className="muted small">
        A machine-learning estimate from this group&apos;s own history, the same month last year and
        the Nepali festival calendar. It shows what might happen, not what will.
      </p>
    </div>
  )
}
