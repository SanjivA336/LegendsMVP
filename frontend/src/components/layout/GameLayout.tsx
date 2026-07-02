import type { ReactNode } from 'react'
import { useGameStore } from '../../store/gameStore'
import LeftSidebar from './LeftSidebar'
import RightSidebar from './RightSidebar'

interface GameLayoutProps {
  center: ReactNode
  stageBar?: ReactNode
}

export default function GameLayout({ center, stageBar }: GameLayoutProps) {
  const leftOpen = useGameStore((s) => s.leftSidebarOpen)
  const rightOpen = useGameStore((s) => s.rightSidebarOpen)

  return (
    <div className="flex h-full overflow-hidden bg-zinc-950">
      {/* Left sidebar */}
      <div
        className="shrink-0 border-r border-zinc-800 bg-zinc-900 flex flex-col overflow-hidden transition-[width] duration-300"
        style={{ width: leftOpen ? '280px' : '48px' }}
      >
        <LeftSidebar open={leftOpen} />
      </div>

      {/* Center */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {stageBar && <div className="shrink-0 border-b border-zinc-800">{stageBar}</div>}
        <div className="flex-1 flex flex-col overflow-hidden">{center}</div>
      </div>

      {/* Right sidebar */}
      <div
        className="shrink-0 border-l border-zinc-800 bg-zinc-900 flex flex-col overflow-hidden transition-[width] duration-300"
        style={{ width: rightOpen ? '280px' : '48px' }}
      >
        <RightSidebar open={rightOpen} />
      </div>
    </div>
  )
}
