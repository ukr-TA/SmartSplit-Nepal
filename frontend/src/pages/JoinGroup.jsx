import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { CheckCircle2, Users } from 'lucide-react'
import { getErrorMessage } from '../api/client'
import { groupApi } from '../api/services'
import { Button, ErrorState, Spinner } from '../components/ui'
import { useUI } from '../context/UIContext'
import { useApi } from '../hooks/useApi'
import { groupTypeOf } from '../utils/constants'

export default function JoinGroup() {
  const { token } = useParams()
  const navigate = useNavigate()
  const { toast } = useUI()
  const { data, loading, error } = useApi(() => groupApi.previewInvite(token), [token])
  const [joining, setJoining] = useState(false)

  if (loading) return <Spinner label="Checking invitation…" />
  if (error) {
    return (
      <div className="page narrow">
        <ErrorState message={error} />
        <Link to="/" className="btn btn-ghost">Go to dashboard</Link>
      </div>
    )
  }

  const Icon = groupTypeOf(data.group.group_type).icon

  const join = async () => {
    setJoining(true)
    try {
      const res = await groupApi.join(token)
      toast(res.joined ? `You joined ${data.group.name}` : 'You are already a member')
      navigate(`/groups/${res.group_id}`)
    } catch (err) {
      toast(getErrorMessage(err), 'error')
      setJoining(false)
    }
  }

  return (
    <div className="page narrow">
      <div className="card join-card">
        <span className={`group-icon lg type-${data.group.group_type}`}><Icon size={30} /></span>
        <p className="eyebrow">You're invited</p>
        <h1>{data.group.name}</h1>
        {data.group.description && <p className="muted">{data.group.description}</p>}
        <p className="muted"><Users size={15} /> {data.group.member_count} members · invited by {data.invited_by}</p>
        {data.already_member ? (
          <>
            <p className="text-receive"><CheckCircle2 size={16} /> You're already a member.</p>
            <Link className="btn btn-primary btn-lg" to={`/groups/${data.group.id}`}>Open group</Link>
          </>
        ) : (
          <Button onClick={join} loading={joining} className="btn-primary btn-lg">Join group</Button>
        )}
      </div>
    </div>
  )
}
