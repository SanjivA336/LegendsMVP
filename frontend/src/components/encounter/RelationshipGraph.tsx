import type { RelationshipEdge } from '../../types/context'
import type { Character } from '../../types/character'

interface RelationshipGraphProps {
  relationships: RelationshipEdge[]
  characters: Character[]
  colorMap: Record<string, string>
}

function edgeColor(affinity: number): string {
  if (affinity > 0.2) return '#22c55e'  // green
  if (affinity < -0.2) return '#ef4444' // red
  return '#71717a'                       // gray
}

export default function RelationshipGraph({ relationships, characters, colorMap }: RelationshipGraphProps) {
  const W = 320
  const H = 320
  const cx = W / 2
  const cy = H / 2
  const r = 110
  const nodeR = 20

  const charMap = new Map(characters.map((c) => [c.id, c]))
  const ids = characters.map((c) => c.id)
  const n = ids.length

  function pos(i: number) {
    const angle = (i * 2 * Math.PI) / n - Math.PI / 2
    return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) }
  }

  if (n === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-sm text-zinc-500">
        No characters in scene.
      </div>
    )
  }

  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
      {/* Edges */}
      {relationships.map((rel) => {
        const fromIdx = ids.indexOf(rel.from_id)
        const toIdx = ids.indexOf(rel.to_id)
        if (fromIdx === -1 || toIdx === -1) return null
        const from = pos(fromIdx)
        const to = pos(toIdx)
        return (
          <line
            key={rel.id}
            x1={from.x}
            y1={from.y}
            x2={to.x}
            y2={to.y}
            stroke={edgeColor(rel.affinity)}
            strokeWidth={1.5}
            strokeOpacity={0.6}
          />
        )
      })}

      {/* Nodes */}
      {ids.map((id, i) => {
        const { x, y } = pos(i)
        const char = charMap.get(id)
        const color = colorMap[id] ?? '#71717a'
        const initials = char ? char.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase() : '?'
        return (
          <g key={id}>
            <circle cx={x} cy={y} r={nodeR} fill={color} />
            <text
              x={x}
              y={y + 1}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize={10}
              fontWeight="bold"
              fill="#09090b"
            >
              {initials}
            </text>
            <text
              x={x}
              y={y + nodeR + 10}
              textAnchor="middle"
              fontSize={9}
              fill="#a1a1aa"
            >
              {char?.name.split(' ')[0] ?? id.slice(0, 6)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
