import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import type { ReactNode } from 'react'

interface ModalProps {
  open: boolean
  onClose: () => void
  children: ReactNode
  title?: string
  maxWidth?: string
}

export default function Modal({ open, onClose, children, title, maxWidth = 'max-w-lg' }: ModalProps) {
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div
        className={`relative z-10 bg-zinc-900/95 backdrop-blur-md border border-zinc-700 rounded-2xl w-full ${maxWidth} shadow-2xl`}
      >
        {title && (
          <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-zinc-800">
            <h2 className="font-semibold tracking-tight text-zinc-100">{title}</h2>
            <button
              onClick={onClose}
              className="text-zinc-500 hover:text-zinc-100 text-xl leading-none transition-colors duration-150"
            >
              &#x2715;
            </button>
          </div>
        )}
        <div className="p-6">{children}</div>
      </div>
    </div>,
    document.body
  )
}
