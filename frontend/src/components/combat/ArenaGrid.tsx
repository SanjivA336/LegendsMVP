import type { Arena } from '../../types/combat'
import type { Character } from '../../types/character'
import ArenaTileCell from './ArenaTileCell'
import CombatantToken from './CombatantToken'

const CELL_SIZE = 40

interface ArenaGridProps {
  arena: Arena
  characters: Character[]
  playerCharacterId: string | null
}

export default function ArenaGrid({ arena, characters, playerCharacterId }: ArenaGridProps) {
  const charMap = new Map(characters.map((c) => [c.id, c]))
  const playerCombatants = arena.combatants.filter(
    (c) => charMap.get(c.id)?.is_player
  )

  const combatantAt = new Map<string, typeof arena.combatants[number]>()
  for (const c of arena.combatants) {
    combatantAt.set(`${c.x},${c.y}`, c)
  }

  return (
    <div
      className="overflow-auto"
      style={{ maxWidth: '100%', maxHeight: '100%' }}
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${arena.width}, ${CELL_SIZE}px)`,
          gridTemplateRows: `repeat(${arena.height}, ${CELL_SIZE}px)`,
          gap: 0,
        }}
      >
        {Array.from({ length: arena.height }, (_, y) =>
          Array.from({ length: arena.width }, (_, x) => {
            const tile = arena.tiles[y]?.[x]
            const combatant = combatantAt.get(`${x},${y}`)
            if (!tile) return <div key={`${x},${y}`} style={{ backgroundColor: '#09090b' }} />
            return (
              <ArenaTileCell key={`${x},${y}`} tile={tile} indoor={arena.indoor}>
                {combatant && (
                  <CombatantToken
                    combatant={combatant}
                    character={charMap.get(combatant.id)}
                    playerCharacterId={playerCharacterId}
                    cellSize={CELL_SIZE}
                    players={playerCombatants}
                  />
                )}
              </ArenaTileCell>
            )
          })
        )}
      </div>
    </div>
  )
}
