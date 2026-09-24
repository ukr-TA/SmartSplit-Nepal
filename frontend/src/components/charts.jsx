import { useState } from 'react'
import { formatNPR, formatShortDate } from '../utils/format'

/**
 * Lightweight, dependency-free charts.
 * One measure per chart, one hue (magnitude), thin marks, recessive grid,
 * labels in text colours, hover tooltips on every mark.
 */

export function HBarList({ rows, max, renderLabel, renderValue, marker }) {
  const top = max ?? Math.max(...rows.map((r) => r.value), 1)
  return (
    <ul className="hbar-list">
      {rows.map((r) => (
        <li key={r.key} title={r.title}>
          <div className="hbar-labels">
            <span className="hbar-name">{renderLabel(r)}</span>
            <span className="hbar-value">{renderValue(r)}</span>
          </div>
          <div className="hbar-track">
            <span className="hbar-fill" style={{ width: `${Math.max((r.value / top) * 100, r.value > 0 ? 1.5 : 0)}%` }} />
            {marker && r.marker != null && (
              <span className="hbar-marker" style={{ left: `${Math.min((r.marker / top) * 100, 100)}%` }} />
            )}
          </div>
        </li>
      ))}
    </ul>
  )
}

export function ColumnChart({ points, height = 220 }) {
  const [hover, setHover] = useState(null)
  const max = Math.max(...points.map((p) => p.value), 1)
  // round the axis up to a friendly number
  const step = 10 ** Math.floor(Math.log10(max))
  const axisMax = Math.ceil(max / step) * step
  const ticks = [0, axisMax / 2, axisMax]
  const peak = points.reduce((best, p, i) => (p.value > (points[best]?.value ?? -1) ? i : best), 0)
  const labelEvery = Math.ceil(points.length / 10)

  return (
    <div className="colchart" style={{ height }}>
      <div className="colchart-axis">
        {ticks.slice().reverse().map((t) => (
          <span key={t}>{t >= 1000 ? `${(t / 1000).toLocaleString('en-IN')}k` : t}</span>
        ))}
      </div>
      <div className="colchart-plot" onMouseLeave={() => setHover(null)}>
        {ticks.map((t) => (
          <span key={t} className="colchart-grid" style={{ bottom: `${(t / axisMax) * 100}%` }} />
        ))}
        <div className="colchart-bars">
          {points.map((p, i) => (
            <div
              key={p.date}
              className={`colchart-col ${hover === i ? 'hover' : ''}`}
              onMouseEnter={() => setHover(i)}
              onFocus={() => setHover(i)}
              tabIndex={0}
              aria-label={`${formatShortDate(p.date)}: ${formatNPR(p.value)}`}
            >
              {i === peak && p.value > 0 && hover == null && (
                <span className="colchart-peak" style={{ bottom: `${(p.value / axisMax) * 100}%` }}>
                  {formatNPR(p.value)}
                </span>
              )}
              <span className="colchart-bar" style={{ height: `${(p.value / axisMax) * 100}%` }} />
              {hover === i && (
                <span className="chart-tip" style={{ bottom: `${Math.min((p.value / axisMax) * 100, 80)}%` }}>
                  <strong>{formatNPR(p.value)}</strong>
                  <small>{formatShortDate(p.date)}</small>
                </span>
              )}
              <span className="colchart-x">{i % labelEvery === 0 ? formatShortDate(p.date) : ''}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
