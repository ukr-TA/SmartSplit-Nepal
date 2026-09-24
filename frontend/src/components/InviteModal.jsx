import { useEffect, useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { Check, Copy, RefreshCw, Share2 } from 'lucide-react'
import { getErrorMessage } from '../api/client'
import { groupApi } from '../api/services'
import { useUI } from '../context/UIContext'
import { formatDate } from '../utils/format'
import { Modal, Spinner } from './ui'

export default function InviteModal({ group, onClose }) {
  const { toast, confirm } = useUI()
  const [invite, setInvite] = useState(null)
  const [copied, setCopied] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    groupApi
      .invite(group.id)
      .then(setInvite)
      .catch((err) => toast(getErrorMessage(err), 'error'))
  }, [group.id, toast])

  const link = invite ? `${window.location.origin}/join/${invite.token}` : ''

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(link)
    } catch {
      // Fallback for browsers that block the clipboard API
      const el = document.createElement('textarea')
      el.value = link
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      el.remove()
    }
    setCopied(true)
    toast('Invite link copied')
    setTimeout(() => setCopied(false), 2000)
  }

  const share = () => navigator.share?.({ title: `Join ${group.name} on SmartSplit`, url: link }).catch(() => {})

  const regenerate = async () => {
    const ok = await confirm({
      title: 'Create a new link?',
      message: 'The current link and QR code will stop working.',
      confirmText: 'Create new link',
    })
    if (!ok) return
    setBusy(true)
    try {
      setInvite(await groupApi.invite(group.id, true))
      toast('New invite link created')
    } catch (err) {
      toast(getErrorMessage(err), 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title="Invite members" onClose={onClose} size="sm">
      {!invite ? (
        <Spinner />
      ) : (
        <div className="invite-box">
          <p className="eyebrow">{group.name}</p>
          <div className="qr-frame">
            <QRCodeSVG value={link} size={196} level="M" marginSize={1} fgColor="#0f1f1c" />
          </div>
          <p className="muted small center">Scan with a phone camera to join</p>
          <div className="invite-code">
            <span className="muted small">Invite code</span>
            <strong>{invite.token}</strong>
          </div>
          <div className="copy-row">
            <input className="input" readOnly value={link} onFocus={(e) => e.target.select()} />
            <button className="btn btn-primary" onClick={copy}>
              {copied ? <Check size={16} /> : <Copy size={16} />} {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
          <div className="row-between">
            <small className="muted">Valid until {formatDate(invite.expires_at)} · used {invite.use_count}×</small>
            <div className="row">
              {typeof navigator.share === 'function' && (
                <button className="icon-btn" onClick={share} aria-label="Share"><Share2 size={17} /></button>
              )}
              <button className="link-btn" onClick={regenerate} disabled={busy}>
                <RefreshCw size={14} /> New link
              </button>
            </div>
          </div>
        </div>
      )}
    </Modal>
  )
}
