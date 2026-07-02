import type { WorldMap, Tile } from '../../types/world'
import type { POI } from '../../types/poi'
import TileCell from './TileCell'

export type MapStyle = 'biome' | 'elevation'

// Sea level ≈ 30th percentile of elevation values (matches backend default percent_ocean=0.30)
const SEA_LEVEL = 0.30

function lerp(a: number, b: number, t: number): number {
  return Math.round(a + (b - a) * t)
}

function elevationColor(tile: Tile): string {
  if (tile.is_water) {
    const d = Math.max(0, Math.min(1, (SEA_LEVEL - tile.elevation) / SEA_LEVEL))
    return `rgb(${lerp(30, 10, d)},${lerp(80, 32, d)},${lerp(128, 64, d)})`
  }
  const n = Math.max(0, (tile.elevation - SEA_LEVEL) / (1.0 - SEA_LEVEL))
  if (n < 0.15) return '#c8b560'
  if (n < 0.35) return '#4a9944'
  if (n < 0.55) return '#2d7a2d'
  if (n < 0.70) return '#8b6914'
  if (n < 0.85) return '#7a6a5a'
  return '#c8c0b8'
}

interface WorldMapGridProps {
  map: WorldMap
  currentX?: number | null
  currentY?: number | null
  poiMap?: Map<string, POI>
  biomeColorOverrides?: Record<string, string>
  mapStyle?: MapStyle
  cellSize?: number
  onTileClick?: (tile: Tile) => void
  // Journey overlays
  pathTiles?: Set<string>
  encounterTiles?: Set<string>
  poiStopTiles?: Set<string>
  journeyTarget?: { x: number; y: number } | null
}

export default function WorldMapGrid({
  map,
  currentX,
  currentY,
  poiMap,
  biomeColorOverrides,
  mapStyle = 'biome',
  cellSize = 14,
  onTileClick,
  pathTiles,
  encounterTiles,
  poiStopTiles,
  journeyTarget,
}: WorldMapGridProps) {
  const tileMap = new Map<string, Tile>()
  for (const tile of map.tiles) {
    tileMap.set(`${tile.x},${tile.y}`, tile)
  }

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${map.width}, ${cellSize}px)`,
        gridTemplateRows: `repeat(${map.height}, ${cellSize}px)`,
        gap: 0,
      }}
      className="rounded-xl overflow-hidden"
    >
      {Array.from({ length: map.height }, (_, y) =>
        Array.from({ length: map.width }, (_, x) => {
          const tile = tileMap.get(`${x},${y}`)
          if (!tile) return <div key={`${x},${y}`} style={{ backgroundColor: '#09090b' }} />
          const key = `${x},${y}`
          const poi = tile.poi_id ? poiMap?.get(key) ?? null : null
          const tileColor =
            mapStyle === 'elevation'
              ? elevationColor(tile)
              : biomeColorOverrides?.[String(tile.biome_id)]
          return (
            <TileCell
              key={key}
              tile={tile}
              isCurrent={currentX === x && currentY === y}
              poi={poi}
              biomeColor={tileColor}
              isOnPath={pathTiles?.has(key)}
              isEncounterStop={encounterTiles?.has(key)}
              isPoiStop={poiStopTiles?.has(key)}
              isJourneyTarget={journeyTarget?.x === x && journeyTarget?.y === y}
              onClick={onTileClick}
            />
          )
        })
      )}
    </div>
  )
}
