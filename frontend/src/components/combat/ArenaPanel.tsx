import { useArena } from '../../hooks/useCombat'
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
  const { data: arena, isLoading } = useArena(encounterId)
  const { data: characters = [] } = useParty(adventure?.id ?? null)

  if (!encounterId) return null

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
          />
        )}
      </div>
    </div>
  )
}
