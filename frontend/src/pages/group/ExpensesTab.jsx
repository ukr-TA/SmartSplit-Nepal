import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Receipt, Search } from 'lucide-react'
import { expenseApi } from '../../api/services'
import ExpenseList from '../../components/ExpenseList'
import { CardSkeleton, EmptyState, ErrorState, Money } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { CATEGORIES } from '../../utils/constants'

export default function ExpensesTab({ group, user, refresh, version }) {
  const { data, loading, error, reload } = useApi(() => expenseApi.list({ group: group.id }), [group.id, version])
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('all')

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return (data || []).filter(
      (e) => (category === 'all' || e.category === category) && (!q || e.description.toLowerCase().includes(q)),
    )
  }, [data, query, category])

  if (error) return <ErrorState message={error} onRetry={reload} />
  if (loading) return <CardSkeleton rows={5} />

  if (!data.length) {
    return (
      <div className="card">
        <EmptyState
          icon={Receipt}
          title="No expenses yet"
          message="Hotel, food, transport - add what the group spent and SmartSplit will work out the shares."
          action={<Link to={`/split?group=${group.id}`} className="btn btn-primary"><Plus size={16} /> Split Expense</Link>}
        />
      </div>
    )
  }

  const total = filtered.reduce((sum, e) => sum + Number(e.amount), 0)
  const used = CATEGORIES.filter((c) => data.some((e) => e.category === c.value))

  return (
    <div className="stack">
      <div className="filter-bar">
        <div className="search-box">
          <Search size={16} />
          <input placeholder="Search expenses" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <div className="chips">
          <button className={`chip ${category === 'all' ? 'active' : ''}`} onClick={() => setCategory('all')}>All</button>
          {used.map((c) => (
            <button key={c.value} className={`chip ${category === c.value ? 'active' : ''}`} onClick={() => setCategory(c.value)}>
              {c.label}
            </button>
          ))}
        </div>
      </div>
      <p className="muted small">
        {filtered.length} expense{filtered.length === 1 ? '' : 's'} · <Money value={total} className="strong" />
      </p>
      {filtered.length ? (
        <ExpenseList expenses={filtered} userId={user.id} onChanged={refresh} />
      ) : (
        <p className="muted center">No expenses match your filters.</p>
      )}
    </div>
  )
}
