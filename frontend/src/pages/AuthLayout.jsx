import { useEffect, useState } from 'react'
import { ArrowRightLeft, HandCoins, Sparkles } from 'lucide-react'
import { authApi } from '../api/services'
import { Logo } from '../components/Layout'
import ThemeToggle from '../components/ThemeToggle'

function ServerStatus() {
  const [status, setStatus] = useState('checking')
  useEffect(() => {
    authApi
      .health()
      .then(() => setStatus('ok'))
      .catch(() => setStatus('down'))
  }, [])
  const text = { checking: 'Checking server…', ok: 'Server connected', down: 'Server offline — start the backend' }[status]
  return (
    <span className={`server-status ${status}`}>
      <span className="dot" /> {text}
    </span>
  )
}

export default function AuthLayout({ title, subtitle, children }) {
  return (
    <div className="auth-page">
      <section className="auth-hero">
        <Logo />
        <div className="auth-hero-copy">
          <h2>
            Split less.
            <br />
            Settle smarter.
          </h2>
          <p>Shared expenses for Nepali students, roommates, families and travellers — in rupees, with eSewa and Khalti.</p>
        </div>
        <div className="auth-demo-card">
          <div className="auth-demo-title">
            <span>POKHARA TRIP</span>
            <span className="pill">5 friends</span>
          </div>
          <div className="auth-demo-row">
            <span>10 direct payments</span>
            <ArrowRightLeft size={16} />
            <strong>3 smart payments</strong>
          </div>
          <div className="auth-demo-list">
            <span><HandCoins size={15} /> Mina → Utsuk</span><strong>Rs. 5,500</strong>
            <span><HandCoins size={15} /> Hari → Sita</span><strong>Rs. 2,000</strong>
            <span><HandCoins size={15} /> Mina → Ram</span><strong>Rs. 500</strong>
          </div>
          <div className="auth-demo-foot">
            <Sparkles size={14} /> Pay with eSewa · Khalti · Cash
          </div>
        </div>
      </section>
      <section className="auth-panel">
        <div className="auth-theme">
          <ThemeToggle />
        </div>
        <div className="auth-form-wrap">
          <div className="auth-mobile-logo">
            <Logo />
          </div>
          <h1>{title}</h1>
          <p className="muted">{subtitle}</p>
          {children}
          <ServerStatus />
        </div>
      </section>
    </div>
  )
}
