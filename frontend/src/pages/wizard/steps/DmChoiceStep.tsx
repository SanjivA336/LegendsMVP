import { useState } from 'react'
import type { WizardData } from '../wizardData'

interface Props {
  data: WizardData
  onNext: (patch: Partial<WizardData>) => void
  onBack: () => void
}

export default function DmChoiceStep({ data, onNext, onBack }: Props) {
  const [mode, setMode] = useState<'ai' | 'human'>(data.dmMode)

  return (
    <div className="flex flex-col gap-5">
      <p className="text-sm text-zinc-400">Who narrates this adventure?</p>

      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={() => setMode('ai')}
          className={`text-left rounded-2xl border px-4 py-4 transition-colors duration-150 ${
            mode === 'ai' ? 'border-accent bg-zinc-800/80' : 'border-zinc-700 bg-zinc-800/40 hover:border-zinc-600'
          }`}
        >
          <div className="text-sm font-semibold text-zinc-100 mb-1">AI Dungeon Master</div>
          <p className="text-xs text-zinc-400 leading-relaxed">
            The DM narrates, runs NPCs, and adjudicates checks. You'll create a character next.
          </p>
        </button>
        <button
          onClick={() => setMode('human')}
          className={`text-left rounded-2xl border px-4 py-4 transition-colors duration-150 ${
            mode === 'human' ? 'border-accent bg-zinc-800/80' : 'border-zinc-700 bg-zinc-800/40 hover:border-zinc-600'
          }`}
        >
          <div className="text-sm font-semibold text-zinc-100 mb-1">I'll Be the DM</div>
          <p className="text-xs text-zinc-400 leading-relaxed">
            You narrate and run the game yourself. No character needed here -- players create their own when they join.
          </p>
        </button>
      </div>

      <div className="flex justify-between pt-2">
        <button onClick={onBack} className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150">
          Back
        </button>
        <button
          onClick={() => onNext({ dmMode: mode })}
          className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150"
        >
          Next
        </button>
      </div>
    </div>
  )
}
