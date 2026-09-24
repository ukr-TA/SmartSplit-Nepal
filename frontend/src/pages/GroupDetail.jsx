import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, CalendarDays, Pencil, Plus, QrCode, Trash2, UserPlus } from 'lucide-react'
import { getErrorMessage } from '../api/client'
import { groupApi } from '../api/services'
import AddMemberModal from '../components/AddMemberModal'
import GroupFormModal from '../components/GroupFormModal'
import InviteModal from '../components/InviteModal'
import { AvatarStack, ErrorState, Spinner } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useUI } from '../context/UIContext'
import { useApi } from '../hooks/useApi'
import { groupTypeOf } from '../utils/constants'
import { formatDate } from '../utils/format'
import OverviewTab from './group/OverviewTab'
import ExpensesTab from './group/ExpensesTab'
import BalancesTab from './group/BalancesTab'
import SettlementsTab from './group/SettlementsTab'
import ActivityTab from './group/ActivityTab'
import MembersTab from './group/MembersTab'
import AnalyticsTab from './group/AnalyticsTab'

const TABS = [
  { key: 'overview', label: 'Overview' },
  { key: 'expenses', label: 'Expenses' },
  { key: 'balances', label: 'Balances' },
  { key: 'settlements', label: 'Settlements' },
  { key: 'analytics', label: 'Trip Analytics', tripOnly: true },
  { key: 'activity', label: 'Activity' },
  { key: 'members', label: 'Members' },
]

export default function GroupDetail() {
  const { id, tab = 'overview' } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { toast, confirm } = useUI()
  const { data: group, loading, error, reload, setData } = useApi(() => groupApi.get(id), [id])
  const [modal, setModal] = useState(() => (new URLSearchParams(window.location.search).get('add') ? 'add' : null))
  const [version, setVersion] = useState(0) // bump to refresh tab data

  if (loading) return <Spinner />
  if (error) {
    return (
      <div className="page">
        <ErrorState message={error} onRetry={reload} />
        <Link to="/groups" className="btn btn-ghost">Back to groups</Link>
      </div>
    )
  }

  const isOwner = group.my_role === 'owner'
  const tabs = TABS.filter((t) => !t.tripOnly || group.is_trip)
  const current = tabs.some((t) => t.key === tab) ? tab : 'overview'
  const type = groupTypeOf(group.group_type)
  const TypeIcon = type.icon
  const refresh = () => {
    reload(true)
    setVersion((v) => v + 1)
  }

  const deleteGroup = async () => {
    const ok = await confirm({
      title: `Delete ${group.name}?`,
      message: 'All expenses, settlements and activity in this group will be permanently deleted. Groups can only be deleted once everyone is settled.',
      confirmText: 'Delete group',
      danger: true,
    })
    if (!ok) return
    try {
      await groupApi.remove(group.id)
      toast('Group deleted')
      navigate('/groups')
    } catch (err) {
      toast(getErrorMessage(err), 'error')
    }
  }

  const tabProps = { group, user, isOwner, refresh, version, openModal: setModal }

  return (
    <div className="page">
      <Link to="/groups" className="back-link"><ArrowLeft size={16} /> Groups</Link>

      <div className={`group-hero ${group.is_trip ? 'is-trip' : ''}`}>
        <div className="group-hero-main">
          <span className={`group-icon lg type-${group.group_type}`}><TypeIcon size={28} /></span>
          <div className="grow">
            <p className="eyebrow">{group.is_trip ? 'Trip' : type.label}</p>
            <h1>{group.name}</h1>
            <p className="muted">
              {group.description}
              {group.is_trip && group.start_date && (
                <span className="nowrap">
                  {group.description ? ' · ' : ''}
                  <CalendarDays size={14} /> {formatDate(group.start_date)}
                  {group.end_date && ` – ${formatDate(group.end_date)}`}
                </span>
              )}
            </p>
            <button className="members-inline" onClick={() => navigate(`/groups/${group.id}/members`)}>
              <AvatarStack users={group.members.map((m) => m.user)} max={6} size={30} />
              <span>{group.member_count} members</span>
            </button>
          </div>
        </div>
        <div className="group-hero-actions">
          <Link to={`/split?group=${group.id}`} className="btn btn-primary">
            <Plus size={17} /> Split Expense
          </Link>
          <button className="btn btn-ghost" onClick={() => setModal('add')}>
            <UserPlus size={17} /> Add member
          </button>
          <button className="btn btn-ghost" onClick={() => setModal('invite')}>
            <QrCode size={17} /> Invite
          </button>
          {isOwner && (
            <>
              <button className="icon-btn bordered" onClick={() => setModal('edit')} aria-label="Edit group" title="Edit group">
                <Pencil size={17} />
              </button>
              <button className="icon-btn bordered danger" onClick={deleteGroup} aria-label="Delete group" title="Delete group">
                <Trash2 size={17} />
              </button>
            </>
          )}
        </div>
      </div>

      <nav className="tabs" role="tablist">
        {tabs.map((t) => (
          <Link
            key={t.key}
            role="tab"
            aria-selected={current === t.key}
            className={`tab ${current === t.key ? 'active' : ''}`}
            to={`/groups/${group.id}${t.key === 'overview' ? '' : `/${t.key}`}`}
            replace
          >
            {t.label}
          </Link>
        ))}
      </nav>

      <div className="tab-panel">
        {current === 'overview' && <OverviewTab {...tabProps} />}
        {current === 'expenses' && <ExpensesTab {...tabProps} />}
        {current === 'balances' && <BalancesTab {...tabProps} />}
        {current === 'settlements' && <SettlementsTab {...tabProps} />}
        {current === 'analytics' && <AnalyticsTab {...tabProps} />}
        {current === 'activity' && <ActivityTab {...tabProps} />}
        {current === 'members' && <MembersTab {...tabProps} />}
      </div>

      {modal === 'add' && (
        <AddMemberModal
          group={group}
          onClose={() => {
            setModal(null)
            if (window.location.search) navigate(window.location.pathname, { replace: true })
          }}
          onAdded={(updated) => {
            setData(updated)
            setVersion((v) => v + 1)
          }}
          onInvite={() => setModal('invite')}
        />
      )}
      {modal === 'invite' && <InviteModal group={group} onClose={() => setModal(null)} />}
      {modal === 'edit' && (
        <GroupFormModal
          group={group}
          onClose={() => setModal(null)}
          onSaved={(updated) => {
            setModal(null)
            setData(updated)
          }}
        />
      )}
    </div>
  )
}
