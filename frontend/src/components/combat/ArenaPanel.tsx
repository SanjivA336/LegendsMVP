import { useArena, useEncounter } from '../../hooks/useCombat'
import { useWorldMap } from '../../hooks/useWorldMap'
import { useParty } from '../../hooks/useCharacter'
import { useGameStore } from '../../store/gameStore'
import { useAdventure } from '../../hooks/useAdventure'
import ArenaGrid from './ArenaGrid'

interface ArenaPanelProps {
  encounterId: string | null
}

export default function ArenaPanel({ encounterId }: ArenaPanelProps) {
  const adventure = useAdventure()
  const activeCharacterId = useGameStore((s) => s.activeCharacterId)
  const currentTileX = useGameStore((s) => s.currentTileX)
  const currentTileY = useGameStore((s) => s.currentTileY)
  const currentMapId = useGameStore((s) => s.currentMapId)
  const { data: arena, isLoading } = useArena(encounterId)
  const { data: encounter } = useEncounter(encounterId)
  const { data: worldMap } = useWorldMap(currentMapId)
  const { data: allCharacters = [] } = useParty(adventure?.id ?? null)

  if (!encounterId) return null

  // Scope the roster to who's actually staged in this encounter, not the whole adventure --
  // falls back to everyone if stage_ids hasn't been populated yet (e.g. no round has run yet).
  const characters = encounter?.stage_ids?.length
    ? allCharacters.filter((c) => encounter.stage_ids.includes(c.id))
    : allCharacters

  // Tint the floor with the biome color of the adventure's current world-map tile --
  // Arena tiles themselves carry no biome data, so this is a general "where you are" tint
  // rather than per-tile precision. Indoor arenas keep their neutral gray regardless.
  const currentTile = worldMap?.tiles.find((t) => t.x === currentTileX && t.y === currentTileY)
  const floorColor = currentTile?.biome_id != null
    ? adventure?.biomeColorOverrides?.[String(currentTile.biome_id)]
    : undefined

  return (
    <div className="h-1/2 border-b border-zinc-800 bg-zinc-950 flex flex-col overflow-hidden">
      {/* Arena header */}
      <div className="h-8 flex items-center px-4 gap-3 shrink-0 border-b border-zinc-800">
        <span className="text-xs uppercase tracking-wider text-zinc-400">Arena</span>
        {arena && (
          <>
            <span className="text-xs text-zinc-600 font-mono">
              {arena.width}×{arena.height}
            </span>
            <span className="text-xs text-zinc-600">Round {arena.round}</span>
            <span className="text-xs text-zinc-600">
              Turn: {arena.combatants.find(c => c.id === arena.turn_order[arena.current_turn_idx])
                ? characters.find(c => c.id === arena.turn_order[arena.current_turn_idx])?.name ?? 'Unknown'
                : '—'
              }
            </span>
          </>
        )}
      </div>

      {/* Arena grid */}
      <div className="flex-1 overflow-auto p-2 flex items-start justify-start">
        {isLoading && (
          <div className="flex items-center justify-center w-full h-full text-sm text-zinc-500">
            Loading arena...
          </div>
        )}
        {!isLoading && !arena && (
          <div className="flex items-center justify-center w-full h-full text-sm text-zinc-500">
            Arena not available.
          </div>
        )}
        {arena && (
          <ArenaGrid
            arena={arena}
            characters={characters}
            playerCharacterId={activeCharacterId}
            floorColor={!arena.indoor ? floorColor : undefined}
          />
        )}
      </div>
    </div>
  )
}
