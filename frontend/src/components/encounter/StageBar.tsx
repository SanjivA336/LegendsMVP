import { useState } from 'react'
import ColorAvatar from '../ui/ColorAvatar'
import CastModal from './CastModal'
import type { Character } from '../../types/character'
import type { RelationshipEdge } from '../../types/context'
import { NPC_NEUTRAL } from '../../constants/colors'
import { usePlayerColors } from '../../hooks/usePlayerColors'

interface StageBarProps {
  stageCharacters: Character[]
  relationships: RelationshipEdge[]
  playerCharacterId: string | null
}

export default function StageBar({ stageCharacters, relationships, playerCharacterId }: StageBarProps) {
  const [castOpen, setCastOpen] = useState(false)
  const playerColors = usePlayerColors()

  const players = stageCharacters.filter((c) => c.is_player)

  function colorFor(char: Character): string {
    if (char.is_player) {
      const idx = players.indexOf(char)
      return char.id === playerCharacterId
        ? playerColors[0]
        : playerColors[idx % playerColors.length]
    }
    return NPC_NEUTRAL
  }

  return (
    <div className="h-12 px-4 flex items-center gap-2 bg-zinc-950">
      <div className="flex items-center gap-1.5">
        {stageCharacters.map((char) => (
          <div key={char.id} title={char.name}>
            <ColorAvatar name={char.name} color={colorFor(char)} size="sm" />
          </div>
        ))}
      </div>

      {stageCharacters.length > 0 && (
        <button
          onClick={() => setCastOpen(true)}
          className="text-xs text-zinc-500 hover:text-zinc-300 ml-2 transition-colors duration-150"
        >
          Cast
        </button>
      )}

      <CastModal
        open={castOpen}
        onClose={() => setCastOpen(false)}
        characters={stageCharacters}
        relationships={relationships}
        playerCharacterId={playerCharacterId}
      />
    </div>
  )
}
