import type { ArenaCombatant } from '../../types/combat'
import type { Character } from '../../types/character'
import { NPC_HOSTILE } from '../../constants/colors'
import { usePlayerColors } from '../../hooks/usePlayerColors'

interface CombatantTokenProps {
  combatant: ArenaCombatant
  character: Character | undefined
  playerCharacterId: string | null
  cellSize: number
  players: ArenaCombatant[]
}

export default function CombatantToken({
  combatant,
  character,
  playerCharacterId,
  cellSize,
  players,
}: CombatantTokenProps) {
  const isDead = combatant.status.includes('dead')
  const hpRatio = combatant.hp / combatant.max_hp
  const playerColors = usePlayerColors()

  let color: string
  if (character?.is_player) {
    const idx = players.indexOf(combatant)
    color = combatant.id === playerCharacterId
      ? playerColors[0]
      : playerColors[idx % playerColors.length]
  } else {
    color = NPC_HOSTILE
  }

  const tokenSize = Math.max(10, cellSize * 0.65)
  const initials = character
    ? character.name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
    : '?'

  return (
    <div
      className="absolute inset-0 flex items-center justify-center"
      style={{ opacity: isDead ? 0.3 : 1 }}
    >
      <div
        className="rounded-full flex items-center justify-center font-bold text-zinc-950 relative"
        style={{
          width: tokenSize,
          height: tokenSize,
          backgroundColor: color,
          fontSize: Math.max(8, tokenSize * 0.35),
          boxShadow: `0 0 0 ${Math.max(1, tokenSize * 0.08)}px rgba(0,0,0,0.5)`,
        }}
      >
        {initials}
        {/* HP pip ring */}
        <svg
          className="absolute inset-0"
          width={tokenSize}
          height={tokenSize}
          viewBox={`0 0 ${tokenSize} ${tokenSize}`}
          style={{ transform: 'rotate(-90deg)' }}
        >
          <circle
            cx={tokenSize / 2}
            cy={tokenSize / 2}
            r={tokenSize / 2 - 1}
            fill="none"
            stroke="rgba(0,0,0,0.3)"
            strokeWidth={2}
          />
          <circle
            cx={tokenSize / 2}
            cy={tokenSize / 2}
            r={tokenSize / 2 - 1}
            fill="none"
            stroke={hpRatio >= 0.5 ? '#22c55e' : hpRatio >= 0.25 ? '#eab308' : '#ef4444'}
            strokeWidth={2}
            strokeDasharray={`${2 * Math.PI * (tokenSize / 2 - 1) * hpRatio} 9999`}
          />
        </svg>
      </div>
    </div>
  )
}
