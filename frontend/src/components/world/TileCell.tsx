import type { Tile } from '../../types/world'
import type { POI } from '../../types/poi'

interface TileCellProps {
  tile: Tile
  isCurrent: boolean
  poi?: POI | null
  biomeColor?: string
  isOnPath?: boolean
  isJourneyTarget?: boolean
  isEncounterStop?: boolean
  isPoiStop?: boolean
  onClick?: (tile: Tile) => void
}

function fallbackTileColor(tile: Tile): string {
  if (tile.is_water) return '#1e3a5f'
  const e = tile.elevation
  if (e >= 0.85) return '#78716c'
  if (e >= 0.65) return '#57534e'
  if (e >= 0.45) return '#15803d'
  if (e >= 0.25) return '#166534'
  return '#14532d'
}

const POI_COLORS: Record<string, string> = {
  dungeon: '#9B5DE5',
  settlement: '#F8961E',
  encampment: '#2EC4B6',
  ruins: '#9AA0A6',
}

function markerSize(poi: POI): number {
  const base = 3
  if (poi.type === 'settlement' || poi.type === 'encampment') {
    return base + (poi.tier - 1)
  }
  return base
}

function PoiMarker({ poi, highlighted }: { poi: POI; highlighted?: boolean }) {
  const color = highlighted ? '#facc15' : (POI_COLORS[poi.type] ?? '#fff')
  const size = markerSize(poi)

  if (poi.type === 'ruins') {
    return (
      <div className="absolute inset-0 flex items-center justify-center" style={{ pointerEvents: 'none' }}>
        <div style={{ width: size + 1, height: size + 1, backgroundColor: color, transform: 'rotate(45deg)' }} />
      </div>
    )
  }
  if (poi.type === 'settlement') {
    return (
      <div className="absolute inset-0 flex items-center justify-center" style={{ pointerEvents: 'none' }}>
        <div style={{ width: size, height: size, backgroundColor: color }} />
      </div>
    )
  }
  if (poi.type === 'encampment') {
    return (
      <div className="absolute inset-0 flex items-center justify-center" style={{ pointerEvents: 'none' }}>
        <div style={{ width: size + 2, height: size + 2, backgroundColor: color, clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)' }} />
      </div>
    )
  }
  // dungeon
  return (
    <div className="absolute inset-0 flex items-center justify-center" style={{ pointerEvents: 'none' }}>
      <div style={{ width: size, height: size, borderRadius: '50%', backgroundColor: color }} />
    </div>
  )
}

export default function TileCell({
  tile, isCurrent, poi, biomeColor,
  isOnPath, isJourneyTarget, isEncounterStop, isPoiStop,
  onClick,
}: TileCellProps) {
  const bg = biomeColor ?? fallbackTileColor(tile)

  return (
    <div
      title={`(${tile.x}, ${tile.y}) — ${tile.biome_name ?? 'unknown'}`}
      onClick={() => onClick?.(tile)}
      className={`relative ${onClick ? 'cursor-pointer hover:brightness-125' : ''} ${
        isCurrent ? 'ring-2 ring-yellow-400 animate-pulse z-10' : ''
      }`}
      style={{ backgroundColor: bg }}
    >
      {/* Journey path overlay */}
      {isOnPath && (
        <div className="absolute inset-0 bg-amber-400/20" style={{ pointerEvents: 'none' }} />
      )}

      {/* Journey target (destination) */}
      {isJourneyTarget && (
        <div className="absolute inset-0 flex items-center justify-center z-20" style={{ pointerEvents: 'none' }}>
          <div className="w-2 h-2 bg-orange-400 rotate-45" />
        </div>
      )}

      {/* Encounter stop */}
      {isEncounterStop && (
        <div className="absolute inset-0 flex items-center justify-center z-20" style={{ pointerEvents: 'none' }}>
          <div className="w-2.5 h-2.5 rounded-full bg-red-500 border border-red-300" />
        </div>
      )}

      {/* Discovered POI */}
      {poi && <PoiMarker poi={poi} highlighted={isPoiStop} />}

      {/* poi_candidate tiles show no marker until discovered */}
    </div>
  )
}
