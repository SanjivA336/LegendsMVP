import { useState } from 'react'
import type { WizardData } from '../AdventureWizard'

interface Props {
  data: WizardData
  onNext: (patch: Pick<WizardData, 'characterName' | 'characterDescription' | 'characterTone'>) => void
  onBack: () => void
}

export default function CharacterCreationStep({ data, onNext, onBack }: Props) {
  const [name, setName] = useState(data.characterName)
  const [description, setDescription] = useState(data.characterDescription)
  const [tone, setTone] = useState(data.characterTone)

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-1.5">
        <label className="text-xs uppercase tracking-wider text-zinc-400">Character Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Kael Ashveil"
          className="bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-500 px-3 py-2.5 rounded-xl text-sm focus:outline-none focus:border-accent transition-colors duration-150"
          autoFocus
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-xs uppercase tracking-wider text-zinc-400">Description</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="A wandering swordsman with a troubled past..."
          rows={3}
          className="bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-500 px-3 py-2.5 rounded-xl text-sm focus:outline-none focus:border-accent transition-colors duration-150 resize-none"
        />
        <p className="text-xs text-zinc-600">
          Physical appearance, backstory, motivations. The DM uses this to portray you.
        </p>
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-xs uppercase tracking-wider text-zinc-400">Speaking Tone</label>
        <input
          type="text"
          value={tone}
          onChange={(e) => setTone(e.target.value)}
          placeholder="Terse, dry humor, formal when nervous"
          className="bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-500 px-3 py-2.5 rounded-xl text-sm focus:outline-none focus:border-accent transition-colors duration-150"
        />
        <p className="text-xs text-zinc-600">
          How your character speaks. The DM narrates your dialogue in this voice.
        </p>
      </div>

      <div className="flex justify-between pt-2">
        <button
          onClick={onBack}
          className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150"
        >
          Back
        </button>
        <button
          onClick={() => onNext({ characterName: name.trim(), characterDescription: description.trim(), characterTone: tone.trim() })}
          disabled={!name.trim()}
          className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150 disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  )
}
