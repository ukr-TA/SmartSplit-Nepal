import { useNavigate } from 'react-router-dom'
import { Crown, LogOut, QrCode, UserMinus, UserPlus } from 'lucide-react'
import { getErrorMessage } from '../../api/client'
import { groupApi } from '../../api/services'
import { Avatar } from '../../components/ui'
import { useUI } from '../../context/UIContext'
import { formatDate } from '../../utils/format'

export default function MembersTab({ group, user, isOwner, refresh, openModal }) {
  const { toast, confirm } = useUI()
  const navigate = useNavigate()

  const remove = async (member) => {
    const self = member.user.id === user.id
    const ok = await confirm({
      title: self ? `Leave ${group.name}?` : `Remove ${member.user.full_name}?`,
      message: self
        ? 'You can only leave once your balance in this group is settled.'
        : 'Members can only be removed when their balance is settled. Their past expenses stay in the history.',
      confirmText: self ? 'Leave group' : 'Remove',
      danger: true,
    })
    if (!ok) return
    try {
      await groupApi.removeMember(group.id, member.user.id)
      toast(self ? `You left ${group.name}` : `${member.user.full_name} removed`)
      if (self) navigate('/groups')
      else refresh()
    } catch (err) {
      toast(getErrorMessage(err), 'error')
    }
  }

  return (
    <div className="card">
      <div className="card-head">
        <h3>{group.member_count} members</h3>
        <div className="row">
          <button className="btn btn-sm btn-ghost" onClick={() => openModal('invite')}><QrCode size={15} /> Invite link</button>
          <button className="btn btn-sm btn-primary" onClick={() => openModal('add')}><UserPlus size={15} /> Add member</button>
        </div>
      </div>
      <ul className="people-list">
        {group.members.map((m) => {
          const self = m.user.id === user.id
          return (
            <li key={m.id}>
              <Avatar user={m.user} size={42} />
              <div className="grow">
                <strong>
                  {m.user.full_name} {self && <span className="muted">(you)</span>}
                </strong>
                <small className="muted">{m.user.phone_number} · joined {formatDate(m.joined_at)}</small>
              </div>
              {m.role === 'owner' ? (
                <span className="pill pill-owner"><Crown size={13} /> Owner</span>
              ) : self ? (
                <button className="btn btn-sm btn-ghost" onClick={() => remove(m)}><LogOut size={15} /> Leave</button>
              ) : isOwner ? (
                <button className="icon-btn bordered danger" onClick={() => remove(m)} aria-label={`Remove ${m.user.full_name}`} title="Remove member">
                  <UserMinus size={16} />
                </button>
              ) : null}
            </li>
          )
        })}
      </ul>
      {group.member_count < 2 && (
        <div className="notice">Add at least one more member to start splitting expenses.</div>
      )}
    </div>
  )
}
