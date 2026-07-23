import { useState } from 'react'
import type { WizardData } from '../wizardData'

interface Props {
  data: WizardData
  onNext: (patch: Partial<WizardData>) => void
  onBack: () => void
}

const STAT_KEYS = ['strength', 'dexterity', 'intelligence', 'fortitude', 'charisma', 'reflex'] as const
const STAT_DEFAULTS: Record<string, string> = {
  strength: 'Strength', dexterity: 'Dexterity', intelligence: 'Intelligence',
  fortitude: 'Fortitude', charisma: 'Charisma', reflex: 'Reflex',
}

export default function WorldBibleStep({ data, onNext, onBack }: Props) {
  const [attrNames, setAttrNames] = useState<Record<string, string>>(data.attributeNames)
  const [currencyName, setCurrencyName] = useState(data.currencyName)

  function setAttr(key: string, value: string) {
    setAttrNames((prev) => ({ ...prev, [key]: value }))
  }

  function handleNext() {
    const resolved: Record<string, string> = {}
    for (const key of STAT_KEYS) {
      resolved[key] = attrNames[key]?.trim() || STAT_DEFAULTS[key]
    }
    onNext({ attributeNames: resolved, currencyName: currencyName.trim() || 'Gold' })
  }

  return (
    <div className="flex flex-col gap-5">
      <p className="text-sm text-zinc-400">
        The World Bible configures how the game presents core mechanics in your world.
        These were pre-filled from your theme choice -- rename anything to fit your setting,
        the underlying rules stay the same.
      </p>

      <div>
        <div className="text-xs uppercase tracking-wider text-zinc-500 mb-3">Attribute Names</div>
        <div className="grid grid-cols-2 gap-2">
          {STAT_KEYS.map((key) => (
            <div key={key} className="flex flex-col gap-1">
              <label className="text-[10px] uppercase tracking-wider text-zinc-600">{STAT_DEFAULTS[key]}</label>
              <input
                type="text" value={attrNames[key] ?? ''}
                onChange={(e) => setAttr(key, e.target.value)}
                placeholder={STAT_DEFAULTS[key]}
                className="bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-600 px-2.5 py-1.5 rounded-lg text-xs focus:outline-none focus:border-accent transition-colors duration-150"
              />
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-[10px] uppercase tracking-wider text-zinc-600">Currency Name</label>
        <input
          type="text" value={currencyName}
          onChange={(e) => setCurrencyName(e.target.value)}
          placeholder="Gold"
          className="bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-600 px-2.5 py-1.5 rounded-lg text-xs focus:outline-none focus:border-accent transition-colors duration-150"
        />
      </div>

      <div className="flex justify-between pt-2">
        <button onClick={onBack} className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150">
          Back
        </button>
        <button onClick={handleNext} className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150">
          Next
        </button>
      </div>
    </div>
  )
}
