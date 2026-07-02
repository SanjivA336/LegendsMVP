interface HPBarProps {
  hp: number
  maxHp: number
  className?: string
}

export default function HPBar({ hp, maxHp, className = '' }: HPBarProps) {
  const pct = Math.max(0, Math.min(100, (hp / maxHp) * 100))
  const color = pct >= 50 ? 'bg-green-500' : pct >= 25 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <div className={`h-1.5 bg-zinc-700 rounded-full overflow-hidden ${className}`}>
      <div
        className={`h-full ${color} rounded-full transition-[width] duration-500`}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}
