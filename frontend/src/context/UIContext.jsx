import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react'
import { AlertTriangle, CheckCircle2, Info, X, XCircle } from 'lucide-react'

const UIContext = createContext(null)

const TOAST_ICONS = { success: CheckCircle2, error: XCircle, info: Info }

/** Toast notifications + a promise-based confirm dialog. */
export function UIProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const [dialog, setDialog] = useState(null)
  const nextId = useRef(1)

  const dismiss = useCallback((id) => setToasts((t) => t.filter((x) => x.id !== id)), [])

  const toast = useCallback(
    (message, type = 'success') => {
      const id = nextId.current++
      setToasts((t) => [...t.slice(-3), { id, message, type }])
      setTimeout(() => dismiss(id), type === 'error' ? 6000 : 3500)
    },
    [dismiss],
  )

  const confirm = useCallback(
    (options) =>
      new Promise((resolve) => {
        setDialog({ ...options, resolve })
      }),
    [],
  )

  const close = (answer) => {
    dialog?.resolve(answer)
    setDialog(null)
  }

  const value = useMemo(() => ({ toast, confirm }), [toast, confirm])

  return (
    <UIContext.Provider value={value}>
      {children}

      <div className="toast-stack" role="status" aria-live="polite">
        {toasts.map(({ id, message, type }) => {
          const Icon = TOAST_ICONS[type] || Info
          return (
            <div key={id} className={`toast toast-${type}`}>
              <Icon size={18} />
              <span>{message}</span>
              <button className="icon-btn" onClick={() => dismiss(id)} aria-label="Dismiss">
                <X size={16} />
              </button>
            </div>
          )
        })}
      </div>

      {dialog && (
        <div className="modal-backdrop" onMouseDown={() => close(false)}>
          <div className="modal modal-sm" role="alertdialog" aria-modal="true" onMouseDown={(e) => e.stopPropagation()}>
            <div className={`confirm-icon ${dialog.danger ? 'danger' : ''}`}>
              <AlertTriangle size={22} />
            </div>
            <h3>{dialog.title}</h3>
            {dialog.message && <p className="muted">{dialog.message}</p>}
            <div className="modal-actions">
              <button className="btn btn-ghost" onClick={() => close(false)}>
                {dialog.cancelText || 'Cancel'}
              </button>
              <button
                className={`btn ${dialog.danger ? 'btn-danger' : 'btn-primary'}`}
                onClick={() => close(true)}
                autoFocus
              >
                {dialog.confirmText || 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}
    </UIContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useUI() {
  return useContext(UIContext)
}
