import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'

/** Sliding light/dark switch. */
export default function ThemeToggle() {
  const { theme, toggle } = useTheme()
  const dark = theme === 'dark'
  return (
    <button
      type="button"
      role="switch"
      aria-checked={dark}
      aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
      title={dark ? 'Light mode' : 'Dark mode'}
      className={`theme-toggle ${dark ? 'is-dark' : ''}`}
      onClick={toggle}
    >
      <Sun size={14} className="tt-sun" />
      <Moon size={14} className="tt-moon" />
      <span className="tt-knob">{dark ? <Moon size={13} /> : <Sun size={13} />}</span>
    </button>
  )
}
