import { Navigate, Route, Routes, useLocation, useParams } from 'react-router-dom'
import Layout from './components/Layout'
import { Spinner } from './components/ui'
import { useAuth } from './context/AuthContext'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Groups from './pages/Groups'
import GroupDetail from './pages/GroupDetail'
import SplitExpense from './pages/SplitExpense'
import SettleUp from './pages/SettleUp'
import PaySimulation from './pages/PaySimulation'
import PaymentReturn from './pages/PaymentReturn'
import Receipt from './pages/Receipt'
import Settlements from './pages/Settlements'
import ActivityPage from './pages/ActivityPage'
import Profile from './pages/Profile'
import JoinGroup from './pages/JoinGroup'
import NotFound from './pages/NotFound'

function RequireAuth({ children }) {
  const { isAuthenticated, checking } = useAuth()
  const location = useLocation()
  if (checking) return <Spinner label="Loading SmartSplit…" />
  if (!isAuthenticated) {
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/login?next=${next}`} replace />
  }
  return children
}

function GuestOnly({ children }) {
  const { isAuthenticated, checking } = useAuth()
  const location = useLocation()
  if (checking) return <Spinner label="Loading SmartSplit…" />
  if (isAuthenticated) {
    const next = new URLSearchParams(location.search).get('next')
    return <Navigate to={next && next.startsWith('/') ? next : '/'} replace />
  }
  return children
}

// Re-mount the group page when the id changes so old data never flashes
function KeyedGroup() {
  const { id } = useParams()
  return <GroupDetail key={id} />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
      <Route path="/register" element={<GuestOnly><Register /></GuestOnly>} />

      {/* Full-screen pages (no sidebar) */}
      <Route path="/pay/:id" element={<RequireAuth><PaySimulation /></RequireAuth>} />
      <Route path="/payments/:gateway/:result/:id" element={<RequireAuth><PaymentReturn /></RequireAuth>} />
      <Route path="/settlements/:id/receipt" element={<RequireAuth><Receipt /></RequireAuth>} />

      <Route element={<RequireAuth><Layout /></RequireAuth>}>
        <Route index element={<Dashboard />} />
        <Route path="groups" element={<Groups />} />
        <Route path="groups/new" element={<Groups createOpen />} />
        <Route path="groups/:id" element={<KeyedGroup />} />
        <Route path="groups/:id/:tab" element={<KeyedGroup />} />
        <Route path="groups/:id/settle/:userId" element={<SettleUp />} />
        <Route path="split" element={<SplitExpense />} />
        <Route path="expenses/:expenseId/edit" element={<SplitExpense />} />
        <Route path="settlements" element={<Settlements />} />
        <Route path="activity" element={<ActivityPage />} />
        <Route path="profile" element={<Profile />} />
        <Route path="join/:token" element={<JoinGroup />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
