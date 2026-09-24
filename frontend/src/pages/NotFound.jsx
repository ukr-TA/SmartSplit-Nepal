import { Link } from 'react-router-dom'
import { Compass } from 'lucide-react'
import { EmptyState } from '../components/ui'

export default function NotFound() {
  return (
    <div className="page narrow">
      <div className="card">
        <EmptyState
          icon={Compass}
          title="Page not found"
          message="The page you're looking for doesn't exist."
          action={<Link to="/" className="btn btn-primary">Go to dashboard</Link>}
        />
      </div>
    </div>
  )
}
