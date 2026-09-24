import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  Activity, Bell, ChevronRight, HandCoins, LayoutDashboard, LogOut, Plus, User, Users,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useUI } from '../context/UIContext'
import { miscApi } from '../api/services'
import { timeAgo } from '../utils/format'
import BrandMark from './BrandMark'
import ThemeToggle from './ThemeToggle'
import { Avatar } from './ui'

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/groups', label: 'Groups', icon: Users },
  { to: '/activity', label: 'Activity', icon: Activity },
  { to: '/settlements', label: 'Settlements', icon: HandCoins },
  { to: '/profile', label: 'Profile', icon: User },
]

export function Logo({ compact = false }) {
  return (
    <Link to="/" className="logo">
      <BrandMark size={36} />
      {!compact && (
        <span className="logo-text">
          SmartSplit <em>Nepal</em>
        </span>
      )}
    </Link>
  )
}

function NotificationBell() {
  const [open, setOpen] = useState(false)
  const [state, setState] = useState({ unread_count: 0, results: [] })
  const ref = useRef(null)
  const navigate = useNavigate()
  const location = useLocation()

  const load = useCallback(() => {
    miscApi.notifications().then(setState).catch(() => {})
  }, [])

  // refresh on navigation and every 30 seconds
  useEffect(() => {
    load()
  }, [load, location.pathname])
  useEffect(() => {
    const t = setInterval(load, 30000)
    return () => clearInterval(t)
  }, [load])

  useEffect(() => {
    const onClick = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false)
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  const openItem = async (n) => {
    setOpen(false)
    if (!n.is_read) {
      miscApi.markRead(n.id).then(load).catch(() => {})
    }
    if (n.group) navigate(`/groups/${n.group}`)
  }

  const markAll = async () => {
    await miscApi.markAllRead().catch(() => {})
    load()
  }

  return (
    <div className="bell" ref={ref}>
      <button className="icon-btn bell-btn" onClick={() => setOpen((o) => !o)} aria-label="Notifications">
        <Bell size={20} />
        {state.unread_count > 0 && <span className="bell-count">{state.unread_count > 9 ? '9+' : state.unread_count}</span>}
      </button>
      {open && (
        <div className="bell-panel">
          <div className="bell-head">
            <strong>Notifications</strong>
            {state.unread_count > 0 && (
              <button className="link-btn" onClick={markAll}>
                Mark all read
              </button>
            )}
          </div>
          {state.results.length === 0 ? (
            <p className="muted bell-empty">You're all caught up.</p>
          ) : (
            <ul>
              {state.results.slice(0, 12).map((n) => (
                <li key={n.id}>
                  <button className={`bell-item ${n.is_read ? '' : 'unread'}`} onClick={() => openItem(n)}>
                    <span className={`bell-dot kind-${n.kind}`} />
                    <span className="bell-text">
                      <strong>{n.title}</strong>
                      <span>{n.message}</span>
                      <small>
                        {n.group_name ? `${n.group_name} · ` : ''}
                        {timeAgo(n.created_at)}
                      </small>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}

export default function Layout() {
  const { user, logout } = useAuth()
  const { confirm, toast } = useUI()
  const navigate = useNavigate()
  const location = useLocation()
  // Inside a group, "Split Expense" pre-selects that group
  const groupMatch = location.pathname.match(/^\/groups\/(\d+)/)
  const splitLink = groupMatch ? `/split?group=${groupMatch[1]}` : '/split'

  const handleLogout = async () => {
    const ok = await confirm({ title: 'Log out?', message: 'You will need to log in again to see your groups.', confirmText: 'Log out' })
    if (!ok) return
    await logout()
    toast('Logged out. See you soon!', 'info')
    navigate('/login')
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Logo />
        <Link to={splitLink} className="btn btn-primary btn-block sidebar-cta">
          <Plus size={18} /> Split Expense
        </Link>
        <nav className="side-nav">
          {NAV.filter((item) => item.to !== '/profile').map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className="side-link">
              <Icon size={19} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <Link to="/profile" className="me-card">
            <Avatar user={user} size={36} />
            <span className="me-text">
              <strong>{user?.full_name}</strong>
              <small>{user?.phone_number}</small>
            </span>
            <ChevronRight size={16} className="muted" />
          </Link>
          <button className="side-link logout" onClick={handleLogout}>
            <LogOut size={19} />
            <span>Log out</span>
          </button>
        </div>
      </aside>

      <div className="main-col">
        <header className="topbar">
          <div className="topbar-mobile-logo">
            <Logo compact />
          </div>
          <div className="topbar-right">
            <Link to={splitLink} className="btn btn-primary btn-sm topbar-cta">
              <Plus size={16} /> Split Expense
            </Link>
            <ThemeToggle />
            <NotificationBell />
            <Link to="/profile" className="topbar-avatar" aria-label="Profile">
              <Avatar user={user} size={34} />
            </Link>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>

      <nav className="bottom-nav">
        {NAV.slice(0, 2).map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className="bottom-link">
            <Icon size={20} />
            <span>{label}</span>
          </NavLink>
        ))}
        <Link to={splitLink} className="bottom-fab" aria-label="Split expense">
          <Plus size={24} />
        </Link>
        {NAV.slice(3, 5).map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} className="bottom-link">
            <Icon size={20} />
            <span>{label === 'Settlements' ? 'Settle' : label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
