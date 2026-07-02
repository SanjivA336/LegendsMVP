import React, { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useGameStore } from '../../store/gameStore'
import { useAdventure } from '../../hooks/useAdventure'
import { useWorldMap } from '../../hooks/useWorldMap'
import { useContextCards } from '../../hooks/useContextCards'
import WorldMapModal from '../world/WorldMapModal'
import QuestTracker from '../quest/QuestTracker'
import { listPOIs } from '../../api/pois'
import { fetchDmNotes, updateDmNotes } from '../../api/dmNotes'
import type { Tile } from '../../types/world'
import type { POI } from '../../types/poi'

interface LeftSidebarProps {
  open: boolean
}

type ActiveSection = 'location' | 'context' | 'quests' | 'notes'

const FAMILY_NAMES = [
  'Arid', 'Grassland', 'Woodland', 'Tropical',
  'Wetland', 'Arctic', 'Ocean', 'Mountain', 'Volcanic',
]

const SEA_LEVEL = 0.30

function fmtElevation(elevation: number): string {
  const ft = Math.round((elevation - SEA_LEVEL) / (1.0 - SEA_LEVEL) * 3000)
  const m = Math.round(ft / 3.281)
  return `${ft.toLocaleString()} ft / ${m.toLocaleString()} m`
}

function tileColor(tile: Tile): string {
  if (tile.is_water) return '#1e3a5f'
  const e = tile.elevation
  if (e >= 0.85) return '#78716c'
  if (e >= 0.65) return '#57534e'
  if (e >= 0.45) return '#15803d'
  if (e >= 0.25) return '#166534'
  return '#14532d'
}

function toNSEW(x: number, y: number, mapWidth: number, mapHeight: number): string {
  const cx = Math.floor(mapWidth / 2)
  const cy = Math.floor(mapHeight / 2)
  const dx = x - cx
  const dy = y - cy
  const ns = dy === 0 ? '' : dy > 0 ? `${dy}S` : `${-dy}N`
  const ew = dx === 0 ? '' : dx > 0 ? `${dx}E` : `${-dx}W`
  return [ns, ew].filter(Boolean).join(' ') || 'Center'
}

interface MiniMapProps {
  tiles: Tile[]
  width: number
  height: number
  currentX: number | null
  currentY: number | null
  settlements: POI[]
  biomeColorOverrides: Record<string, string>
  onClick: () => void
}

function MiniMap({ tiles, width, height, currentX, currentY, settlements, biomeColorOverrides, onClick }: MiniMapProps) {
  const tileMap = new Map<string, Tile>()
  for (const t of tiles) tileMap.set(`${t.x},${t.y}`, t)

  const settlementSet = new Set(settlements.map((p) => `${p.tile_x},${p.tile_y}`))

  const CELL = 3

  return (
    <button
      onClick={onClick}
      className="rounded-xl overflow-hidden border border-zinc-700 hover:border-zinc-500 transition-colors duration-150 shrink-0"
      title="Click to open full map"
      style={{ cursor: 'pointer' }}
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${width}, ${CELL}px)`,
          gridTemplateRows: `repeat(${height}, ${CELL}px)`,
          width: width * CELL,
          height: height * CELL,
        }}
      >
        {Array.from({ length: height }, (_, y) =>
          Array.from({ length: width }, (_, x) => {
            const tile = tileMap.get(`${x},${y}`)
            const bg = tile
              ? (biomeColorOverrides[String(tile.biome_id)] ?? tileColor(tile))
              : '#09090b'
            const isCurrent = x === currentX && y === currentY
            const isSettlement = settlementSet.has(`${x},${y}`)

            return (
              <div
                key={`${x},${y}`}
                style={{
                  backgroundColor: bg,
                  outline: isCurrent ? '1px solid #facc15' : undefined,
                  outlineOffset: '-1px',
                  position: 'relative',
                }}
              >
                {isSettlement && (
                  <div
                    style={{
                      position: 'absolute',
                      inset: 0,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <div style={{ width: 2, height: 2, backgroundColor: '#F8961E' }} />
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </button>
  )
}

function MapPinIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  )
}

function BookIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  )
}

function ScrollIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="9" y1="13" x2="15" y2="13" />
      <line x1="9" y1="17" x2="13" y2="17" />
    </svg>
  )
}

function NotesIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  )
}

const SECTIONS: { key: ActiveSection; label: string; Icon: () => React.ReactElement }[] = [
  { key: 'location', label: 'Location', Icon: MapPinIcon },
  { key: 'quests',   label: 'Quests',   Icon: ScrollIcon },
  { key: 'context',  label: 'Context',  Icon: BookIcon },
  { key: 'notes',    label: 'DM Notes', Icon: NotesIcon },
]

export default function LeftSidebar({ open }: LeftSidebarProps) {
  const [mapModalOpen, setMapModalOpen] = useState(false)
  const [activeSection, setActiveSection] = useState<ActiveSection>('location')
  const [query, setQuery] = useState('')
  const [editingNotes, setEditingNotes] = useState(false)
  const [notesText, setNotesText] = useState('')
  const [savingNotes, setSavingNotes] = useState(false)

  const toggleLeft = useGameStore((s) => s.toggleLeftSidebar)
  const currentTileX = useGameStore((s) => s.currentTileX)
  const currentTileY = useGameStore((s) => s.currentTileY)
  const currentMapId = useGameStore((s) => s.currentMapId)
  const adventure = useAdventure()
  const queryClient = useQueryClient()

  const { data: worldMap } = useWorldMap(currentMapId)
  const { data: contextCards = [] } = useContextCards(adventure?.id ?? null)

  const { data: dmNotes } = useQuery({
    queryKey: ['dm-notes', adventure?.id],
    queryFn: () => fetchDmNotes(adventure!.id),
    enabled: !!adventure?.id,
  })

  const canEditNotes = adventure?.role === 'owner' || adventure?.role === 'admin'

  async function saveNotes() {
    if (!adventure?.id) return
    setSavingNotes(true)
    try {
      const updated = await updateDmNotes(adventure.id, notesText)
      queryClient.setQueryData(['dm-notes', adventure.id], updated)
      setEditingNotes(false)
    } catch {
      // Non-fatal
    } finally {
      setSavingNotes(false)
    }
  }

  const { data: pois = [] } = useQuery<POI[]>({
    queryKey: ['pois', adventure?.id, currentMapId],
    queryFn: () => listPOIs(adventure!.id, currentMapId ?? undefined),
    enabled: !!adventure?.id,
  })

  const settlements = pois.filter((p) => p.type === 'settlement')

  const currentTile = worldMap?.tiles.find(
    (t) => t.x === currentTileX && t.y === currentTileY
  )

  const familyId =
    currentTile?.biome_id !== null && currentTile?.biome_id !== undefined
      ? currentTile.biome_id % 10
      : null
  const familyName = familyId !== null ? FAMILY_NAMES[familyId] ?? null : null

  const coords =
    currentTile && worldMap
      ? toNSEW(currentTile.x, currentTile.y, worldMap.width, worldMap.height)
      : null

  const filteredCards = query
    ? contextCards.filter(
        (c) =>
          c.label.toLowerCase().includes(query.toLowerCase()) ||
          c.content.toLowerCase().includes(query.toLowerCase())
      )
    : contextCards

  if (!open) {
    return (
      <div className="flex flex-col items-center pt-2 gap-1">
        <button
          onClick={toggleLeft}
          className="w-10 h-10 flex items-center justify-center text-zinc-500 hover:text-zinc-100 hover:bg-zinc-800 rounded-lg transition-colors duration-150"
          title="Expand sidebar"
        >
          &#x276F;
        </button>
        {SECTIONS.map(({ key, label, Icon }) => (
          <button
            key={key}
            onClick={() => { toggleLeft(); setActiveSection(key) }}
            className="w-10 h-10 flex items-center justify-center text-zinc-500 hover:text-zinc-100 hover:bg-zinc-800 rounded-lg transition-colors duration-150"
            title={label}
          >
            <Icon />
          </button>
        ))}
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-800 shrink-0">
        <div className="flex gap-1">
          {SECTIONS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveSection(key)}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors duration-150 ${
                activeSection === key
                  ? 'bg-zinc-800 text-zinc-100'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <button
          onClick={toggleLeft}
          className="w-7 h-7 flex items-center justify-center text-zinc-500 hover:text-zinc-100 rounded-lg transition-colors duration-150"
          title="Collapse"
        >
          &#x276E;
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {activeSection === 'location' && (
          <div className="p-3 flex flex-col gap-3 items-center">
            {/* Mini map */}
            {worldMap ? (
              <MiniMap
                tiles={worldMap.tiles}
                width={worldMap.width}
                height={worldMap.height}
                currentX={currentTileX}
                currentY={currentTileY}
                settlements={settlements}
                biomeColorOverrides={adventure?.biomeColorOverrides ?? {}}
                onClick={() => setMapModalOpen(true)}
              />
            ) : (
              <button
                onClick={() => setMapModalOpen(true)}
                className="w-full py-2 rounded-xl border border-zinc-700 text-xs text-zinc-400 hover:text-zinc-100 hover:border-zinc-600 transition-colors duration-150"
              >
                View World Map
              </button>
            )}

            {/* 2×2 info grid */}
            {currentTile ? (
              <div className="w-full grid grid-cols-2 gap-1.5">
                <div className="rounded-xl bg-zinc-800 p-2.5 flex flex-col gap-0.5">
                  <div className="text-[9px] uppercase tracking-wider text-zinc-500">Coordinates</div>
                  <div className="text-xs font-mono font-semibold text-zinc-200">{coords}</div>
                </div>
                <div className="rounded-xl bg-zinc-800 p-2.5 flex flex-col gap-0.5">
                  <div className="text-[9px] uppercase tracking-wider text-zinc-500">Elevation</div>
                  <div className="text-[10px] font-mono font-semibold text-zinc-200 leading-tight">
                    {fmtElevation(currentTile.elevation)}
                  </div>
                </div>
                <div className="rounded-xl bg-zinc-800 p-2.5 flex flex-col gap-0.5">
                  <div className="text-[9px] uppercase tracking-wider text-zinc-500">Biome</div>
                  <div className="text-xs font-semibold text-zinc-200 truncate">
                    {currentTile.biome_name ?? (currentTile.is_water ? 'Water' : 'Unknown')}
                  </div>
                </div>
                <div className="rounded-xl bg-zinc-800 p-2.5 flex flex-col gap-0.5">
                  <div className="text-[9px] uppercase tracking-wider text-zinc-500">Family</div>
                  <div className="text-xs font-semibold text-zinc-200 truncate">
                    {familyName ?? (currentTile.is_water ? 'Ocean' : '—')}
                  </div>
                </div>
              </div>
            ) : (
              <div className="w-full rounded-xl bg-zinc-800 p-3">
                <div className="text-xs text-zinc-500">No location set. Click the map to set your position.</div>
              </div>
            )}
          </div>
        )}

        {activeSection === 'quests' && (
          <QuestTracker adventureId={adventure?.id ?? null} />
        )}

        {activeSection === 'notes' && (
          <div className="p-3 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <p className="text-xs text-zinc-500">A running summary of confirmed events in this adventure.</p>
              {canEditNotes && !editingNotes && (
                <button
                  onClick={() => { setNotesText(dmNotes?.public_notes ?? ''); setEditingNotes(true) }}
                  className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors shrink-0 ml-2"
                >
                  Edit
                </button>
              )}
            </div>

            {editingNotes ? (
              <div className="flex flex-col gap-2">
                <textarea
                  value={notesText}
                  onChange={(e) => setNotesText(e.target.value)}
                  rows={10}
                  className="w-full px-3 py-2.5 rounded-xl bg-zinc-800 border border-zinc-700 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-accent transition-colors resize-none"
                  placeholder="Write a summary of what has happened so far…"
                />
                <div className="flex gap-2 justify-end">
                  <button
                    onClick={() => setEditingNotes(false)}
                    className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={saveNotes}
                    disabled={savingNotes}
                    className="px-3 py-1.5 rounded-lg bg-accent text-xs font-semibold text-zinc-950 hover:bg-accent/90 disabled:opacity-60 transition-colors"
                  >
                    {savingNotes ? 'Saving…' : 'Save'}
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-xs text-zinc-300 leading-relaxed whitespace-pre-wrap">
                {dmNotes?.public_notes
                  ? dmNotes.public_notes
                  : <span className="text-zinc-600">No notes yet{canEditNotes ? ' — click Edit to add a summary.' : '.'}</span>
                }
              </div>
            )}
          </div>
        )}

        {activeSection === 'context' && (
          <div className="p-3 flex flex-col gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search context..."
              className="w-full bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-500 px-2.5 py-1.5 rounded-lg text-xs focus:outline-none focus:border-accent transition-colors duration-150"
            />
            {filteredCards.length === 0 && (
              <p className="text-xs text-zinc-600 text-center py-4">
                {query ? 'No matches.' : 'No context cards yet.'}
              </p>
            )}
            {filteredCards.map((card) => (
              <div
                key={card.id}
                className="rounded-xl bg-zinc-800 p-3 flex flex-col gap-1 hover:bg-zinc-700/60 transition-colors duration-150"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-zinc-200 truncate">{card.label}</span>
                  {card.always_inject && (
                    <span className="text-[10px] uppercase tracking-wider text-accent shrink-0">
                      always
                    </span>
                  )}
                </div>
                <p className="text-xs text-zinc-500 line-clamp-3 leading-snug">{card.content}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <WorldMapModal open={mapModalOpen} onClose={() => setMapModalOpen(false)} />
    </div>
  )
}
