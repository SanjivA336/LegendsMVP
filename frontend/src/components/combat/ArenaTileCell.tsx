import type { CSSProperties } from 'react'
import type { ArenaTile } from '../../types/combat'

interface ArenaTileCellProps {
  tile: ArenaTile
  indoor: boolean
  children?: React.ReactNode
}

function edgeBorderStyle(level: number): { style: string; color: string; width: string } {
  if (level === 1) return { style: 'dashed', color: '#a1a1aa', width: '1px' }
  if (level === 2) return { style: 'solid',  color: '#f4f4f5', width: '2px' }
  if (level === 3) return { style: 'solid',  color: '#ef4444', width: '3px' }
  return { style: 'solid', color: '#3f3f46', width: '1px' }
}

export default function ArenaTileCell({ tile, indoor, children }: ArenaTileCellProps) {
  const [n, e, s, w] = tile.edges

  const tileStyle: CSSProperties = {
    position: 'relative',
    backgroundColor: tile.passable
      ? indoor
        ? '#3f3f46'
        : '#166534'
      : '#1c1917',
    borderTopStyle:    edgeBorderStyle(n).style as CSSProperties['borderTopStyle'],
    borderTopColor:    edgeBorderStyle(n).color,
    borderTopWidth:    edgeBorderStyle(n).width,
    borderRightStyle:  edgeBorderStyle(e).style as CSSProperties['borderRightStyle'],
    borderRightColor:  edgeBorderStyle(e).color,
    borderRightWidth:  edgeBorderStyle(e).width,
    borderBottomStyle: edgeBorderStyle(s).style as CSSProperties['borderBottomStyle'],
    borderBottomColor: edgeBorderStyle(s).color,
    borderBottomWidth: edgeBorderStyle(s).width,
    borderLeftStyle:   edgeBorderStyle(w).style as CSSProperties['borderLeftStyle'],
    borderLeftColor:   edgeBorderStyle(w).color,
    borderLeftWidth:   edgeBorderStyle(w).width,
    boxSizing:         'border-box',
  }

  return (
    <div style={tileStyle}>
      {/* Hazard indicator */}
      {tile.hazard > 0 && (
        <div
          className="absolute inset-0 flex items-end justify-end p-px pointer-events-none"
        >
          <span className="text-[7px] font-bold text-red-400 leading-none">!</span>
        </div>
      )}
      {/* Aura overlay */}
      {tile.aura && (
        <div className="absolute inset-0 bg-violet-500/20 pointer-events-none" />
      )}
      {children}
    </div>
  )
}
