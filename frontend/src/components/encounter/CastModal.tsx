import { useState } from 'react'
import Modal from '../ui/Modal'
import RelationshipGraph from './RelationshipGraph'
import type { Character } from '../../types/character'
import type { RelationshipEdge } from '../../types/context'
import { NPC_NEUTRAL } from '../../constants/colors'
import { usePlayerColors } from '../../hooks/usePlayerColors'

interface CastModalProps {
  open: boolean
  onClose: () => void
  characters: Character[]
  relationships: RelationshipEdge[]
  playerCharacterId: string | null
}

function buildColorMap(
  characters: Character[],
  playerCharacterId: string | null,
  playerColors: string[]
): Record<string, string> {
  const map: Record<string, string> = {}
  const players = characters.filter((c) => c.is_player)
  for (const char of characters) {
    if (char.is_player) {
      const idx = players.indexOf(char)
      map[char.id] = char.id === playerCharacterId
        ? playerColors[0]
        : playerColors[idx % playerColors.length]
    } else {
      map[char.id] = NPC_NEUTRAL
    }
  }
  return map
}

export default function CastModal({
  open,
  onClose,
  characters,
  relationships,
  playerCharacterId,
}: CastModalProps) {
  const [view, setView] = useState<'graph' | 'list'>('graph')
  const playerColors = usePlayerColors()
  const colorMap = buildColorMap(characters, playerCharacterId, playerColors)

  return (
    <Modal open={open} onClose={onClose} title="Cast" maxWidth="max-w-md">
      <div className="flex flex-col gap-4">
        <div className="flex gap-2">
          <button
            onClick={() => setView('graph')}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors duration-150 ${
              view === 'graph' ? 'bg-zinc-700 text-zinc-100' : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            Graph
          </button>
          <button
            onClick={() => setView('list')}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors duration-150 ${
              view === 'list' ? 'bg-zinc-700 text-zinc-100' : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            List
          </button>
        </div>

        {view === 'graph' && (
          <div className="flex justify-center">
            <RelationshipGraph
              relationships={relationships}
              characters={characters}
              colorMap={colorMap}
            />
          </div>
        )}

        {view === 'list' && (
          <div className="flex flex-col gap-2">
            {relationships.length === 0 && (
              <p className="text-sm text-zinc-500">No relationships mapped yet.</p>
            )}
            {relationships.map((rel) => {
              const from = characters.find((c) => c.id === rel.from_id)
              const to = characters.find((c) => c.id === rel.to_id)
              if (!from || !to) return null
              return (
                <div key={rel.id} className="flex items-center gap-2 text-xs text-zinc-400">
                  <span className="font-semibold" style={{ color: colorMap[rel.from_id] }}>
                    {from.name}
                  </span>
                  <span className="text-zinc-600">
                    {rel.affinity > 0.2 ? '→' : rel.affinity < -0.2 ? '⤳' : '—'}
                  </span>
                  <span className="font-semibold" style={{ color: colorMap[rel.to_id] }}>
                    {to.name}
                  </span>
                  <span className="ml-auto font-mono text-zinc-600">
                    {rel.affinity > 0 ? '+' : ''}{rel.affinity.toFixed(2)}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </Modal>
  )
}
