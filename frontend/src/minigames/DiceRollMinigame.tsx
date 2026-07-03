import { useState } from 'react'
import { tierLabelForRoll, TIER_COLORS } from '../utils/diceScoring'
import type { MinigameProps } from './types'

interface RollState {
  rolls: number[]
  effective: number
}

export default function DiceRollMinigame({ skillName, dieSize, target, advDisadv, onComplete }: MinigameProps) {
  const [rolling, setRolling] = useState(false)
  const [result, setResult] = useState<RollState | null>(null)

  function handleRoll() {
    if (rolling || result) return
    setRolling(true)
    setTimeout(() => {
      const numRolls = advDisadv !== 0 ? 2 : 1
      const rolls = Array.from({ length: numRolls }, () => Math.floor(Math.random() * dieSize) + 1)
      const effective = advDisadv > 0
        ? Math.max(...rolls)
        : advDisadv < 0
          ? Math.min(...rolls)
          : rolls[0]
      setResult({ rolls, effective })
      setRolling(false)
      setTimeout(() => {
        onComplete({ rolls, die: dieSize, effective })
      }, 1200)
    }, 900)
  }

  const tier = result && target !== null ? tierLabelForRoll(result.effective, target, dieSize) : null
  const color = tier ? TIER_COLORS[tier] : undefined

  return (
    <div className="flex flex-col items-center gap-2 py-1">
      <div className="text-xs text-zinc-400">
        {skillName}{target !== null && ` — DC ${target}`}
      </div>
      {!result ? (
        <button
          onClick={handleRoll}
          disabled={rolling}
          className="px-4 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold text-sm rounded-lg transition-colors duration-150 disabled:opacity-60"
        >
          {rolling ? 'Rolling…' : `Roll d${dieSize}`}
        </button>
      ) : (
        <div className="flex flex-col items-center gap-1">
          <div className="text-2xl font-bold font-mono" style={{ color }}>{result.effective}</div>
          {tier && <div className="text-xs font-semibold" style={{ color }}>{tier}</div>}
          {advDisadv !== 0 && (
            <div className="text-[10px] text-zinc-500">rolls: {result.rolls.join(', ')}</div>
          )}
        </div>
      )}
    </div>
  )
}
