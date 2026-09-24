import { useEffect } from 'react'
import { AlertTriangle, Loader2, RefreshCw, X } from 'lucide-react'
import { categoryOf } from '../utils/constants'
import { formatNPR, initials } from '../utils/format'

const AVATAR_TINTS = ['#0f766e', '#2a78d6', '#b45309', '#7c3aed', '#be185d', '#047857', '#1e40af', '#9a3412']

export function Avatar({ user, size = 36 }) {
  const name = user?.full_name || '?'
  const tint = AVATAR_TINTS[(user?.id || name.length) % AVATAR_TINTS.length]
  if (user?.profile_picture) {
    return <img className="avatar" src={user.profile_picture} alt={name} style={{ width: size, height: size }} />
  }
  return (
    <span
      className="avatar"
      aria-hidden="true"
      style={{ width: size, height: size, background: tint, fontSize: size * 0.38 }}
    >
      {initials(name)}
    </span>
  )
}

export function AvatarStack({ users = [], max = 4, size = 28 }) {
  const shown = users.slice(0, max)
  const extra = users.length - shown.length
  return (
    <span className="avatar-stack">
      {shown.map((u) => (
        <Avatar key={u.id} user={u} size={size} />
      ))}
      {extra > 0 && (
        <span className="avatar avatar-more" style={{ width: size, height: size, fontSize: size * 0.36 }}>
          +{extra}
        </span>
      )}
    </span>
  )
}

/** Coloured amount. tone: "auto" uses sign (green receive / red give). */
export function Money({ value, tone = 'none', sign = false, className = '' }) {
  const n = Number(value) || 0
  const cls = tone === 'auto' ? (n > 0 ? 'text-receive' : n < 0 ? 'text-give' : 'muted') : tone === 'none' ? '' : `text-${tone}`
  return <span className={`money ${cls} ${className}`}>{formatNPR(n, { sign })}</span>
}

export function CategoryIcon({ category, size = 40 }) {
  const c = categoryOf(category)
  const Icon = c.icon
  return (
    <span className="cat-icon" style={{ width: size, height: size, '--cat-tint': c.tint, '--cat-ink': c.ink }} title={c.label}>
      <Icon size={size * 0.48} />
    </span>
  )
}

export function Spinner({ label = 'Loading…', inline = false }) {
  return (
    <div className={inline ? 'spinner-inline' : 'spinner-block'} role="status">
      <Loader2 className="spin" size={inline ? 16 : 26} />
      {label && <span>{label}</span>}
    </div>
  )
}

export function Skeleton({ height = 16, width = '100%', radius = 8 }) {
  return <span className="skeleton" style={{ height, width, borderRadius: radius }} />
}

export function CardSkeleton({ rows = 3 }) {
  return (
    <div className="card stack-sm">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} width={`${90 - i * 15}%`} />
      ))}
    </div>
  )
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="empty-state error">
      <AlertTriangle size={28} />
      <p>{message}</p>
      {onRetry && (
        <button className="btn btn-ghost" onClick={() => onRetry()}>
          <RefreshCw size={16} /> Try again
        </button>
      )}
    </div>
  )
}

export function EmptyState({ icon: Icon, title, message, action }) {
  return (
    <div className="empty-state">
      {Icon && (
        <span className="empty-icon">
          <Icon size={26} />
        </span>
      )}
      <h3>{title}</h3>
      {message && <p className="muted">{message}</p>}
      {action}
    </div>
  )
}

export function Modal({ title, onClose, children, footer, size = 'md' }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className={`modal modal-${size}`} role="dialog" aria-modal="true" aria-label={title} onMouseDown={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>{title}</h3>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-actions">{footer}</div>}
      </div>
    </div>
  )
}

export function Field({ label, error, hint, children, htmlFor }) {
  return (
    <label className={`field ${error ? 'has-error' : ''}`} htmlFor={htmlFor}>
      {label && <span className="field-label">{label}</span>}
      {children}
      {error ? <span className="field-error">{error}</span> : hint ? <span className="field-hint">{hint}</span> : null}
    </label>
  )
}

export function Button({ loading, children, className = 'btn-primary', ...props }) {
  return (
    <button className={`btn ${className}`} disabled={loading || props.disabled} {...props}>
      {loading && <Loader2 className="spin" size={16} />}
      {children}
    </button>
  )
}

export function PageHeader({ title, subtitle, actions, back }) {
  return (
    <div className="page-header">
      <div>
        {back}
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </div>
  )
}

export function StatusBadge({ status }) {
  const map = { successful: 'Successful', pending: 'Pending', failed: 'Failed' }
  return <span className={`badge badge-${status}`}>{map[status] || status}</span>
}

export function MethodBadge({ method }) {
  const labels = { esewa: 'eSewa', khalti: 'Khalti', cash: 'Cash' }
  return <span className={`method-badge method-${method}`}>{labels[method] || method}</span>
}
