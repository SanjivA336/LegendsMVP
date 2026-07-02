import type { Stats } from '../../types/character'

const STAT_LABELS: Record<keyof Stats, string> = {
  strength:     'STR',
  dexterity:    'DEX',
  intelligence: 'INT',
  fortitude:    'FOR',
  charisma:     'CHA',
  reflex:       'REF',
}

interface StatBlockProps {
  stats: Stats
}

export default function StatBlock({ stats }: StatBlockProps) {
  return (
    <div className="grid grid-cols-3 gap-2">
      {(Object.entries(STAT_LABELS) as [keyof Stats, string][]).map(([key, label]) => (
        <div
          key={key}
          className="bg-zinc-800 rounded-xl p-3 flex flex-col items-center gap-0.5"
        >
          <span className="text-xs uppercase tracking-wider text-zinc-400">{label}</span>
          <span className="font-mono text-lg font-semibold text-zinc-100">{stats[key]}</span>
          <span className="text-xs text-zinc-500 font-mono">
            {stats[key] >= 10 ? `+${Math.floor((stats[key] - 10) / 2)}` : Math.floor((stats[key] - 10) / 2)}
          </span>
        </div>
      ))}
    </div>
  )
}
