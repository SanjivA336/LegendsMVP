import { useGameStore } from '../store/gameStore'
import type { AdventureMeta } from '../store/gameStore'

export function useAdventure(): AdventureMeta | null {
  const activeAdventureId = useGameStore((s) => s.activeAdventureId)
  const adventures = useGameStore((s) => s.adventures)
  return adventures.find((a) => a.id === activeAdventureId) ?? null
}
