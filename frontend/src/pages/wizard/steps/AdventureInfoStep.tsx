import { useState } from 'react'
import type { WizardData } from '../AdventureWizard'

interface Props {
  data: WizardData
  onNext: (patch: Pick<WizardData, 'adventureName' | 'worldName'>) => void
  onBack: () => void
}

export default function AdventureInfoStep({ data, onNext }: Props) {
  const [adventureName, setAdventureName] = useState(data.adventureName)
  const [worldName, setWorldName] = useState(data.worldName)

  function handleNext() {
    if (!adventureName.trim() || !worldName.trim()) return
    onNext({ adventureName: adventureName.trim(), worldName: worldName.trim() })
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1.5">
        <label className="text-xs uppercase tracking-wider text-zinc-400">Adventure Name</label>
        <input
          type="text"
          value={adventureName}
          onChange={(e) => setAdventureName(e.target.value)}
          placeholder="The Shattered Reaches"
          className="bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-500 px-3 py-2.5 rounded-xl text-sm focus:outline-none focus:border-accent transition-colors duration-150"
          autoFocus
        />
        <p className="text-xs text-zinc-600">Displayed in your adventure list.</p>
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-xs uppercase tracking-wider text-zinc-400">World Name</label>
        <input
          type="text"
          value={worldName}
          onChange={(e) => setWorldName(e.target.value)}
          placeholder="Vaeltharion"
          className="bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-500 px-3 py-2.5 rounded-xl text-sm focus:outline-none focus:border-accent transition-colors duration-150"
        />
        <p className="text-xs text-zinc-600">Used to seed the world map and set the DM's tone.</p>
      </div>

      <div className="flex justify-end pt-2">
        <button
          onClick={handleNext}
          disabled={!adventureName.trim() || !worldName.trim()}
          className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150 disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  )
}
