import type { ReactNode } from 'react'

interface CollapsibleProps {
  open: boolean
  children: ReactNode
}

export default function Collapsible({ open, children }: CollapsibleProps) {
  return (
    <div
      className="overflow-hidden transition-all duration-300"
      style={{
        maxHeight: open ? '4000px' : '0px',
        opacity: open ? 1 : 0,
      }}
    >
      {children}
    </div>
  )
}
