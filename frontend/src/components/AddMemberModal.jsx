import { useEffect, useState } from 'react'
import { Check, Phone, QrCode, Search, UserPlus } from 'lucide-react'
import { getErrorMessage } from '../api/client'
import { authApi, groupApi } from '../api/services'
import { useUI } from '../context/UIContext'
import { Avatar, Modal, Spinner } from './ui'

/** Find registered users by phone, name or email and add them to the group. */
export default function AddMemberModal({ group, onClose, onAdded, onInvite }) {
  const { toast } = useUI()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [matchType, setMatchType] = useState(null)
  const [searching, setSearching] = useState(false)
  const [adding, setAdding] = useState(null)
  const [added, setAdded] = useState([])

  const memberIds = new Set([...(group.members || []).map((m) => m.user.id), ...added])
  const q = query.trim()

  // Search as the user types (debounced)
  useEffect(() => {
    if (q.length < 2) return undefined
    const t = setTimeout(() => {
      setSearching(true)
      authApi
        .searchUsers(q)
        .then((res) => {
          setResults(res.results)
          setMatchType(res.match_type)
        })
        .catch((err) => toast(getErrorMessage(err), 'error'))
        .finally(() => setSearching(false))
    }, 350)
    return () => clearTimeout(t)
  }, [q, toast])

  const add = async (user) => {
    setAdding(user.id)
    try {
      const updated = await groupApi.addMember(group.id, user.id)
      setAdded((a) => [...a, user.id])
      toast(`${user.full_name} added to ${group.name}`)
      onAdded(updated)
    } catch (err) {
      toast(getErrorMessage(err), 'error')
    } finally {
      setAdding(null)
    }
  }

  const digitsOnly = /^[\d\s+-]+$/.test(q)
  const shown = q.length >= 2 ? results : null

  return (
    <Modal title="Add members" onClose={onClose} footer={<button className="btn btn-primary" onClick={onClose}>Done</button>}>
      <div className="stack">
        <div className="search-box big">
          {digitsOnly && q ? <Phone size={18} /> : <Search size={18} />}
          <input
            autoFocus
            placeholder="Phone number (98XXXXXXXX), name or email"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setResults(null)
            }}
            inputMode={digitsOnly && q ? 'tel' : 'text'}
          />
          {searching && <Spinner inline label="" />}
        </div>
        <p className="muted small">
          For privacy, phone numbers must be typed in full (10 digits). Names match partially.
        </p>

        {shown && shown.length === 0 && !searching && (
          <div className="notice">
            {matchType === 'phone' && q.replace(/\D/g, '').length < 10
              ? 'Keep typing - enter all 10 digits of the phone number.'
              : 'No registered SmartSplit user found. Share an invite link instead.'}
          </div>
        )}

        {shown && shown.length > 0 && (
          <ul className="people-list">
            {shown.map((u) => {
              const isMember = memberIds.has(u.id)
              return (
                <li key={u.id}>
                  <Avatar user={u} size={40} />
                  <div className="grow">
                    <strong>{u.full_name}</strong>
                    <small className="muted">{u.phone_number}</small>
                  </div>
                  {isMember ? (
                    <span className="pill pill-receive"><Check size={14} /> Member</span>
                  ) : (
                    <button className="btn btn-sm btn-primary" disabled={adding === u.id} onClick={() => add(u)}>
                      <UserPlus size={15} /> Add
                    </button>
                  )}
                </li>
              )
            })}
          </ul>
        )}

        {onInvite && (
          <button className="invite-cta" onClick={onInvite}>
            <QrCode size={20} />
            <span>
              <strong>Friend not on SmartSplit yet?</strong>
              <small>Share an invite link or QR code</small>
            </span>
          </button>
        )}
      </div>
    </Modal>
  )
}
