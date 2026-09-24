import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ImagePlus, Pencil, Trash2, X } from 'lucide-react'
import { getErrorMessage } from '../api/client'
import { expenseApi } from '../api/services'
import { useUI } from '../context/UIContext'
import { categoryOf } from '../utils/constants'
import { formatDate, formatDateTime } from '../utils/format'
import { Avatar, Button, CategoryIcon, Modal, Money } from './ui'

const METHOD_LABEL = { equal: 'Split equally', custom: 'Custom amounts', percentage: 'By percentage' }

export default function ExpenseDetailModal({ expense: initial, userId, onClose, onChanged }) {
  const { toast, confirm } = useUI()
  const [expense, setExpense] = useState(initial)
  const [uploading, setUploading] = useState(false)
  const [zoom, setZoom] = useState(false)
  const fileRef = useRef(null)

  const upload = async (file) => {
    if (!file) return
    if (!file.type.startsWith('image/')) return toast('Please choose an image file (JPG or PNG).', 'error')
    if (file.size > 5 * 1024 * 1024) return toast('Receipt image must be smaller than 5 MB.', 'error')
    setUploading(true)
    try {
      const updated = await expenseApi.uploadReceipt(expense.id, file)
      setExpense(updated)
      onChanged?.()
      toast('Receipt uploaded')
    } catch (err) {
      toast(getErrorMessage(err), 'error')
    } finally {
      setUploading(false)
    }
  }

  const removeReceipt = async () => {
    if (!(await confirm({ title: 'Remove receipt?', confirmText: 'Remove', danger: true }))) return
    try {
      setExpense(await expenseApi.removeReceipt(expense.id))
      onChanged?.()
    } catch (err) {
      toast(getErrorMessage(err), 'error')
    }
  }

  const remove = async () => {
    const ok = await confirm({
      title: `Delete “${expense.description}”?`,
      message: 'Balances will be recalculated for everyone in the group.',
      confirmText: 'Delete expense',
      danger: true,
    })
    if (!ok) return
    try {
      await expenseApi.remove(expense.id)
      toast('Expense deleted')
      onChanged?.()
      onClose()
    } catch (err) {
      toast(getErrorMessage(err), 'error')
    }
  }

  const payerIsMe = expense.paid_by.id === userId

  return (
    <Modal
      title="Expense details"
      onClose={onClose}
      footer={
        expense.can_edit ? (
          <>
            <button className="btn btn-ghost danger-text" onClick={remove}><Trash2 size={16} /> Delete</button>
            <Link className="btn btn-primary" to={`/expenses/${expense.id}/edit`}><Pencil size={16} /> Edit</Link>
          </>
        ) : null
      }
    >
      <div className="stack">
        <div className="detail-head">
          <CategoryIcon category={expense.category} size={52} />
          <div className="grow">
            <h2>{expense.description}</h2>
            <small className="muted">{categoryOf(expense.category).label} · {formatDate(expense.date)}</small>
          </div>
          <Money value={expense.amount} className="detail-amount" />
        </div>

        <div className="detail-grid">
          <div>
            <small className="muted">Paid by</small>
            <strong>{payerIsMe ? 'You' : expense.paid_by.full_name}</strong>
          </div>
          <div>
            <small className="muted">Split</small>
            <strong>{METHOD_LABEL[expense.split_method]}</strong>
          </div>
          <div>
            <small className="muted">Your share</small>
            <Money value={expense.my_share} className="strong" />
          </div>
        </div>

        <div>
          <h4 className="section-label">Participants ({expense.splits.length})</h4>
          <ul className="share-list">
            {expense.splits.map((s) => (
              <li key={s.user.id}>
                <Avatar user={s.user} size={32} />
                <span className="grow">
                  {s.user.id === userId ? 'You' : s.user.full_name}
                  {s.user.id === expense.paid_by.id && <span className="pill tiny">paid</span>}
                </span>
                {s.percentage && <span className="muted small">{Number(s.percentage)}%</span>}
                <Money value={s.amount} className="strong" />
              </li>
            ))}
          </ul>
        </div>

        {expense.notes && (
          <div>
            <h4 className="section-label">Notes</h4>
            <p className="note-box">{expense.notes}</p>
          </div>
        )}

        <div>
          <h4 className="section-label">Receipt</h4>
          {expense.receipt ? (
            <div className="receipt-preview">
              <button className="receipt-thumb" onClick={() => setZoom(true)}>
                <img src={expense.receipt} alt="Receipt" />
              </button>
              <div className="stack-sm">
                <a className="link-btn" href={expense.receipt} target="_blank" rel="noreferrer">Open full size</a>
                {expense.can_edit && (
                  <>
                    <button className="link-btn" onClick={() => fileRef.current?.click()}>Replace</button>
                    <button className="link-btn danger-text" onClick={removeReceipt}>Remove</button>
                  </>
                )}
              </div>
            </div>
          ) : expense.can_edit ? (
            <Button className="btn-ghost dashed btn-block" loading={uploading} onClick={() => fileRef.current?.click()}>
              <ImagePlus size={18} /> Upload receipt photo
            </Button>
          ) : (
            <p className="muted small">No receipt attached.</p>
          )}
          <input ref={fileRef} type="file" accept="image/*" hidden onChange={(e) => upload(e.target.files[0])} />
        </div>

        <small className="muted">
          Added by {expense.created_by.id === userId ? 'you' : expense.created_by.full_name} · {formatDateTime(expense.created_at)}
        </small>
      </div>

      {zoom && (
        <div className="lightbox" onMouseDown={(e) => { e.stopPropagation(); setZoom(false) }}>
          <button className="icon-btn light" aria-label="Close"><X size={22} /></button>
          <img src={expense.receipt} alt="Receipt full size" />
        </div>
      )}
    </Modal>
  )
}
