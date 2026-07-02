import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { useQuery } from '@tanstack/react-query'
import WorldMapGrid from './WorldMapGrid'
import type { MapStyle } from './WorldMapGrid'
import { useWorldMap } from '../../hooks/useWorldMap'
import { useGameStore } from '../../store/gameStore'
import { useAdventure } from '../../hooks/useAdventure'
import { listPOIs } from '../../api/pois'
import type { Tile } from '../../types/world'
import type { POI } from '../../types/poi'

// ── Journey algorithms ───────────────────────────────────────────────────────

function bresenhamLine(x0: number, y0: number, x1: number, y1: number): Array<{ x: number; y: number }> {
  const pts: Array<{ x: number; y: number }> = []
  const dx = Math.abs(x1 - x0)
  const dy = Math.abs(y1 - y0)
  const sx = x0 < x1 ? 1 : -1
  const sy = y0 < y1 ? 1 : -1
  let err = dx - dy
  let cx = x0
  let cy = y0
  for (;;) {
    pts.push({ x: cx, y: cy })
    if (cx === x1 && cy === y1) break
    const e2 = 2 * err
    if (e2 > -dy) { err -= dy; cx += sx }
    if (e2 < dx)  { err += dx; cy += sy }
  }
  return pts
}

function deterministicOffset(x0: number, y0: number, x1: number, y1: number): number {
  const h = ((x0 * 73856093) ^ (y0 * 19349663) ^ (x1 * 83492791) ^ (y1 * 31234567)) >>> 0
  return (h % 3) - 1  // -1, 0, or +1
}

function isBiomeBoundary(x: number, y: number, tileMap: Map<string, Tile>): boolean {
  const tile = tileMap.get(`${x},${y}`)
  if (!tile) return false
  const biomeId = tile.biome_id
  const dirs = [[0, -1], [1, 0], [0, 1], [-1, 0]]
  return dirs.some(([dx, dy]) => {
    const n = tileMap.get(`${x + dx},${y + dy}`)
    return n !== undefined && n.biome_id !== biomeId
  })
}

function snapToBiomeBoundary(x: number, y: number, tileMap: Map<string, Tile>, radius = 2): { x: number; y: number } {
  const visited = new Set<string>([`${x},${y}`])
  const queue: Array<{ x: number; y: number; dist: number }> = [{ x, y, dist: 0 }]
  while (queue.length > 0) {
    const curr = queue.shift()!
    if (isBiomeBoundary(curr.x, curr.y, tileMap)) return { x: curr.x, y: curr.y }
    if (curr.dist >= radius) continue
    for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
      const nx = curr.x + dx
      const ny = curr.y + dy
      const key = `${nx},${ny}`
      if (!visited.has(key) && tileMap.has(key)) {
        visited.add(key)
        queue.push({ x: nx, y: ny, dist: curr.dist + 1 })
      }
    }
  }
  return { x, y }
}

interface JourneyStop {
  x: number
  y: number
  type: 'encounter' | 'poi'
  poi?: POI
}

interface JourneyPlan {
  path: Array<{ x: number; y: number }>
  stops: JourneyStop[]
  distance: number
  encounterCount: number
}

function planJourney(
  from: { x: number; y: number },
  to: { x: number; y: number },
  tileMap: Map<string, Tile>,
  pois: POI[],
): JourneyPlan {
  const path = bresenhamLine(from.x, from.y, to.x, to.y)
  const distance = path.length - 1
  if (distance === 0) return { path, stops: [], distance: 0, encounterCount: 0 }

  const base = Math.max(0, Math.round(distance / 5))
  const offset = deterministicOffset(from.x, from.y, to.x, to.y)
  const encounterCount = Math.max(0, base + offset)

  const interior = path.slice(1, -1)
  const interiorSet = new Set(interior.map((p) => `${p.x},${p.y}`))

  const poiStops: JourneyStop[] = pois
    .filter((p) => interiorSet.has(`${p.tile_x},${p.tile_y}`))
    .map((p) => ({ x: p.tile_x, y: p.tile_y, type: 'poi' as const, poi: p }))

  const encounterStops: JourneyStop[] = []
  if (encounterCount > 0 && interior.length > 0) {
    const step = interior.length / encounterCount
    for (let i = 0; i < encounterCount; i++) {
      const idx = Math.min(Math.round((i + 0.5) * step), interior.length - 1)
      const raw = interior[idx]
      const snapped = snapToBiomeBoundary(raw.x, raw.y, tileMap)
      encounterStops.push({ x: snapped.x, y: snapped.y, type: 'encounter' as const })
    }
  }

  return { path, stops: [...encounterStops, ...poiStops], distance, encounterCount }
}

// Sea level constant matches WorldMapGrid (backend default percent_ocean=0.30)
const SEA_LEVEL = 0.30

function fmtElevation(elevation: number): string {
  const ft = Math.round((elevation - SEA_LEVEL) / (1.0 - SEA_LEVEL) * 3000)
  const m = Math.round(ft / 3.281)
  return `${ft.toLocaleString()} ft / ${m.toLocaleString()} m`
}

// ── Component ────────────────────────────────────────────────────────────────

interface WorldMapModalProps {
  open: boolean
  onClose: () => void
}

export default function WorldMapModal({ open, onClose }: WorldMapModalProps) {
  const currentMapId = useGameStore((s) => s.currentMapId)
  const currentTileX = useGameStore((s) => s.currentTileX)
  const currentTileY = useGameStore((s) => s.currentTileY)
  const adventure = useAdventure()

  const [selectedTile, setSelectedTile] = useState<Tile | null>(null)
  const [journeyMode, setJourneyMode] = useState<'idle' | 'planning'>('idle')
  const [journeyTarget, setJourneyTarget] = useState<{ x: number; y: number } | null>(null)
  const [cellSize, setCellSize] = useState(10)
  const [mapStyle, setMapStyle] = useState<MapStyle>('biome')

  const { data: map, isLoading } = useWorldMap(open ? currentMapId : null)

  const { data: pois = [] } = useQuery<POI[]>({
    queryKey: ['pois', adventure?.id, currentMapId],
    queryFn: () => listPOIs(adventure!.id, currentMapId ?? undefined),
    enabled: open && !!adventure?.id,
  })

  // Compute dynamic cell size based on viewport
  useEffect(() => {
    if (!open || !map) return
    const available = window.innerHeight - 80
    const size = Math.max(4, Math.min(14, Math.floor(available / map.height)))
    setCellSize(size)
  }, [open, map])

  // Escape key to close
  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  // Reset journey state when modal closes
  useEffect(() => {
    if (!open) {
      setJourneyMode('idle')
      setJourneyTarget(null)
      setSelectedTile(null)
    }
  }, [open])

  const biomeColorOverrides = adventure?.biomeColorOverrides ?? {}

  const poiMap = new Map<string, POI>()
  for (const poi of pois) poiMap.set(`${poi.tile_x},${poi.tile_y}`, poi)

  const tileMap = new Map<string, Tile>()
  if (map) for (const t of map.tiles) tileMap.set(`${t.x},${t.y}`, t)

  const from =
    currentTileX !== null && currentTileY !== null
      ? { x: currentTileX, y: currentTileY }
      : null

  const journey =
    from && journeyTarget && map
      ? planJourney(from, journeyTarget, tileMap, pois)
      : null

  const pathSet = journey
    ? new Set(journey.path.map((p) => `${p.x},${p.y}`))
    : new Set<string>()
  const encounterSet = journey
    ? new Set(journey.stops.filter((s) => s.type === 'encounter').map((s) => `${s.x},${s.y}`))
    : new Set<string>()
  const poiStopSet = journey
    ? new Set(journey.stops.filter((s) => s.type === 'poi').map((s) => `${s.x},${s.y}`))
    : new Set<string>()

  function handleTileClick(tile: Tile) {
    if (journeyMode === 'planning') {
      setJourneyTarget({ x: tile.x, y: tile.y })
    } else {
      setSelectedTile(tile)
    }
  }

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-50 flex" style={{ backgroundColor: 'rgba(9,9,11,0.97)' }}>
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute top-3 right-3 z-10 w-8 h-8 flex items-center justify-center text-zinc-400 hover:text-zinc-100 bg-zinc-900 hover:bg-zinc-800 rounded-lg border border-zinc-700 transition-colors duration-150 text-sm"
        title="Close (Esc)"
      >
        ✕
      </button>

      {/* Map area — centers the grid */}
      <div className="flex-1 flex items-center justify-center overflow-auto p-4">
        {isLoading && <p className="text-zinc-400 text-sm">Loading map...</p>}
        {!isLoading && !map && <p className="text-zinc-400 text-sm">No world map generated yet.</p>}
        {map && (
          <WorldMapGrid
            map={map}
            currentX={currentTileX}
            currentY={currentTileY}
            poiMap={poiMap}
            biomeColorOverrides={biomeColorOverrides}
            mapStyle={mapStyle}
            cellSize={cellSize}
            onTileClick={handleTileClick}
            pathTiles={pathSet}
            encounterTiles={encounterSet}
            poiStopTiles={poiStopSet}
            journeyTarget={journeyTarget}
          />
        )}
      </div>

      {/* Sidebar */}
      <div className="w-72 shrink-0 border-l border-zinc-800 flex flex-col bg-zinc-900">
        {/* Header */}
        <div className="px-4 py-3 border-b border-zinc-800 shrink-0">
          <h2 className="text-sm font-semibold text-zinc-100">
            {journeyMode === 'planning' ? 'Plan Journey' : 'World Map'}
          </h2>
          {journeyMode === 'planning' && (
            <p className="text-xs text-zinc-500 mt-0.5">
              {journeyTarget ? 'Destination set.' : 'Click a destination on the map.'}
            </p>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-5">
          {/* Map style selector */}
          <section className="flex flex-col gap-2">
            <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">View Mode</div>
            <div className="flex gap-1">
              {(['biome', 'elevation'] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => setMapStyle(s)}
                  className={`flex-1 py-1.5 rounded-lg text-xs font-semibold capitalize transition-colors duration-150 ${
                    mapStyle === s
                      ? 'bg-zinc-700 text-zinc-100'
                      : 'bg-zinc-800 text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  {s}
                </button>
              ))}
              <button
                disabled
                title="Coming soon"
                className="flex-1 py-1.5 rounded-lg text-xs font-semibold bg-zinc-800 text-zinc-600 cursor-not-allowed"
              >
                Faction
              </button>
            </div>
          </section>

          {/* Journey planner */}
          <section className="flex flex-col gap-2">
            <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">Journey</div>

            {journeyMode === 'idle' ? (
              <button
                onClick={() => { setJourneyMode('planning'); setJourneyTarget(null); setSelectedTile(null) }}
                disabled={!from}
                className="w-full py-2 px-3 rounded-xl text-sm font-semibold transition-colors duration-150 disabled:opacity-40"
                style={{ backgroundColor: 'var(--accent)', color: '#18181b' }}
              >
                Plan Journey
              </button>
            ) : (
              <div className="flex flex-col gap-2">
                {journey && (
                  <div className="rounded-xl bg-zinc-800 p-3 flex flex-col gap-1.5 text-xs">
                    <div className="flex justify-between">
                      <span className="text-zinc-500">From</span>
                      <span className="text-zinc-200 font-mono">{from?.x}, {from?.y}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">To</span>
                      <span className="text-zinc-200 font-mono">{journeyTarget?.x}, {journeyTarget?.y}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Distance</span>
                      <span className="text-zinc-200 font-mono">{journey.distance} tiles</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Encounters</span>
                      <span className="text-zinc-200 font-mono">{journey.encounterCount}</span>
                    </div>
                    {journey.stops.filter((s) => s.type === 'poi').length > 0 && (
                      <div className="flex justify-between">
                        <span className="text-zinc-500">POI Stops</span>
                        <span className="text-zinc-200 font-mono">
                          {journey.stops.filter((s) => s.type === 'poi').length}
                        </span>
                      </div>
                    )}
                  </div>
                )}

                <div className="flex gap-2">
                  <button
                    disabled={!journey}
                    className="flex-1 py-1.5 rounded-lg text-xs font-semibold transition-colors duration-150 disabled:opacity-40"
                    style={{ backgroundColor: '#3f3f46', color: '#f4f4f5' }}
                  >
                    Start Journey
                  </button>
                  <button
                    onClick={() => { setJourneyMode('idle'); setJourneyTarget(null) }}
                    className="flex-1 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-100 rounded-lg text-xs font-semibold transition-colors duration-150"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </section>

          {/* Selected tile info */}
          {selectedTile && journeyMode === 'idle' && (
            <section className="flex flex-col gap-2">
              <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">Tile Info</div>
              <div className="rounded-xl bg-zinc-800 p-3 flex flex-col gap-2.5">
                <div className="flex items-center gap-2">
                  <div
                    className="w-4 h-4 rounded border border-zinc-600 shrink-0"
                    style={{
                      backgroundColor:
                        biomeColorOverrides[String(selectedTile.biome_id)] ??
                        (selectedTile.is_water ? '#1e3a5f' : '#27272a'),
                    }}
                  />
                  <span className="text-sm font-semibold text-zinc-100">
                    {selectedTile.biome_name ?? (selectedTile.is_water ? 'Water' : 'Unknown')}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-y-2 gap-x-3 text-xs">
                  <div>
                    <div className="text-[9px] uppercase tracking-wider text-zinc-500">Position</div>
                    <div className="font-mono text-zinc-200">{selectedTile.x}, {selectedTile.y}</div>
                  </div>
                  <div>
                    <div className="text-[9px] uppercase tracking-wider text-zinc-500">Elevation</div>
                    <div className="font-mono text-zinc-200 text-[10px]">{fmtElevation(selectedTile.elevation)}</div>
                  </div>
                  <div>
                    <div className="text-[9px] uppercase tracking-wider text-zinc-500">Terrain</div>
                    <div className="text-zinc-200">{selectedTile.is_water ? 'Water' : 'Land'}</div>
                  </div>
                  <div>
                    <div className="text-[9px] uppercase tracking-wider text-zinc-500">POI</div>
                    <div className="text-zinc-200 capitalize">
                      {(() => {
                        const p = poiMap.get(`${selectedTile.x},${selectedTile.y}`)
                        return p ? p.type : '—'
                      })()}
                    </div>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* Legend */}
          <section className="flex flex-col gap-2">
            <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">Legend</div>
            <div className="flex flex-col gap-1.5 text-xs text-zinc-400">
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full border-2 border-yellow-400 shrink-0" />
                Current location
              </span>
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 shrink-0" style={{ backgroundColor: '#F8961E' }} />
                Settlement
              </span>
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: '#9B5DE5' }} />
                Dungeon
              </span>
              <span className="flex items-center gap-2">
                <span
                  className="w-3 h-3 shrink-0"
                  style={{ backgroundColor: '#2EC4B6', clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)' }}
                />
                Encampment
              </span>
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 shrink-0 rotate-45" style={{ backgroundColor: '#9AA0A6' }} />
                Ruins
              </span>
              {journey && (
                <>
                  <span className="flex items-center gap-2">
                    <span className="w-3 h-3 shrink-0 opacity-50 rounded-sm" style={{ backgroundColor: '#fbbf24' }} />
                    Journey path
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: '#ef4444' }} />
                    Encounter
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="w-3 h-3 shrink-0 rotate-45" style={{ backgroundColor: '#fb923c' }} />
                    Destination
                  </span>
                </>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>,
    document.body,
  )
}
