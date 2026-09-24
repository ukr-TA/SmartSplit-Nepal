import { useState } from 'react'
import { Paperclip } from 'lucide-react'
import { formatDate, firstName } from '../utils/format'
import ExpenseDetailModal from './ExpenseDetailModal'
import { CategoryIcon, Money } from './ui'

/** Expenses as a date-grouped card timeline. */
export default function ExpenseList({ expenses, userId, onChanged }) {
  const [open, setOpen] = useState(null)

  const byDate = expenses.reduce((acc, e) => {
    ;(acc[e.date] ||= []).push(e)
    return acc
  }, {})

  return (
    <>
      <div className="expense-timeline">
        {Object.entries(byDate).map(([date, items]) => (
          <section key={date}>
            <h4 className="date-label">{formatDate(date)}</h4>
            <div className="stack-sm">
              {items.map((e) => {
                const mine = e.paid_by.id === userId
                const share = Number(e.my_share)
                const lent = mine ? Number(e.amount) - share : 0
                return (
                  <button key={e.id} className="expense-card" onClick={() => setOpen(e)}>
                    <CategoryIcon category={e.category} size={46} />
                    <div className="grow">
                      <strong className="expense-title">
                        {e.description}
                        {e.receipt && <Paperclip size={14} className="muted" aria-label="Has receipt" />}
                      </strong>
                      <small className="muted">
                        Paid by {mine ? 'you' : e.paid_by.full_name} · {e.splits.length} {e.splits.length === 1 ? 'person' : 'people'}
                      </small>
                      <small className="participants">
                        {e.splits.map((s) => (s.user.id === userId ? 'You' : firstName(s.user.full_name))).join(' · ')}
                      </small>
                    </div>
                    <div className="right">
                      <Money value={e.amount} className="expense-amount" />
                      {mine && lent > 0 ? (
                        <small className="text-receive">you lent <Money value={lent} /></small>
                      ) : mine ? (
                        <small className="muted">your own expense</small>
                      ) : share > 0 ? (
                        <small className="text-give">your share <Money value={share} /></small>
                      ) : (
                        <small className="muted">not involved</small>
                      )}
                    </div>
                  </button>
                )
              })}
            </div>
          </section>
        ))}
      </div>
      {open && (
        <ExpenseDetailModal expense={open} userId={userId} onClose={() => setOpen(null)} onChanged={onChanged} />
      )}
    </>
  )
}
