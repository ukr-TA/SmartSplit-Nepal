import { Activity } from 'lucide-react'
import { groupApi } from '../../api/services'
import Timeline from '../../components/Timeline'
import { CardSkeleton, EmptyState, ErrorState } from '../../components/ui'
import { useApi } from '../../hooks/useApi'

export default function ActivityTab({ group, version }) {
  const { data, loading, error, reload } = useApi(() => groupApi.activity(group.id), [group.id, version])
  if (error) return <ErrorState message={error} onRetry={reload} />
  if (loading) return <CardSkeleton rows={6} />
  return (
    <div className="card">
      {data.length ? <Timeline items={data} /> : <EmptyState icon={Activity} title="No activity yet" />}
    </div>
  )
}
