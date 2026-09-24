import { HandCoins, Pencil, Plus, Receipt, Trash2, UserMinus, UserPlus, Users } from 'lucide-react'
import { timeAgo } from '../utils/format'
import { Money } from './ui'

const ICONS = {
  group_created: Users,
  group_updated: Pencil,
  member_added: UserPlus,
  member_joined: UserPlus,
  member_removed: UserMinus,
  member_left: UserMinus,
  expense_added: Receipt,
  expense_updated: Pencil,
  expense_deleted: Trash2,
  settlement: HandCoins,
}

export default function Timeline({ items, showGroup = false }) {
  return (
    <ul className="timeline">
      {items.map((a) => {
        const Icon = ICONS[a.action] || Plus
        return (
          <li key={a.id} className={`tl-${a.action}`}>
            <span className="tl-icon"><Icon size={16} /></span>
            <div className="tl-body">
              <p>{a.description}</p>
              {a.amount && <Money value={a.amount} className="strong" />}
              <small className="muted">
                {showGroup && <>{a.group_name} · </>}
                {timeAgo(a.created_at)}
              </small>
            </div>
          </li>
        )
      })}
    </ul>
  )
}
