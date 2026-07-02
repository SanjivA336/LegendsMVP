import { useState } from 'react'
import type { WizardData, BioFamilyConfig } from '../AdventureWizard'

interface Props {
  data: WizardData
  onNext: (patch: Pick<WizardData, 'biomeConfig'>) => void
  onBack: () => void
}

const TIER_LABELS = ['T1', 'T2', 'T3'] as const

export default function BiomeSetupStep({ data, onNext, onBack }: Props) {
  const [families, setFamilies] = useState<BioFamilyConfig[]>(data.biomeConfig)

  function toggleEnabled(id: number) {
    setFamilies((prev) =>
      prev.map((f) => (f.id === id && !f.locked ? { ...f, enabled: !f.enabled } : f))
    )
  }

  function setFamilyName(id: number, name: string) {
    setFamilies((prev) =>
      prev.map((f) => (f.id === id ? { ...f, familyName: name } : f))
    )
  }

  function setTierField(familyId: number, tier: 1 | 2 | 3, field: 'name' | 'color', value: string) {
    setFamilies((prev) =>
      prev.map((f) =>
        f.id === familyId
          ? { ...f, tiers: f.tiers.map((t) => (t.tier === tier ? { ...t, [field]: value } : t)) }
          : f
      )
    )
  }

  const enabledCount = families.filter((f) => f.enabled).length

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-zinc-400">
        Choose which biome families appear in your world. Rename families and tiers,
        and pick the map color for each biome.
      </p>

      <div className="grid grid-cols-2 gap-3 max-h-[55vh] overflow-y-auto pr-1">
        {[...families].sort((a, b) => a.familyName.localeCompare(b.familyName)).map((family) => (
          <div
            key={family.id}
            className={`rounded-2xl border transition-colors duration-150 ${
              family.enabled
                ? 'border-zinc-700 bg-zinc-800/60'
                : 'border-zinc-800 bg-zinc-900/60 opacity-60'
            }`}
          >
            {/* Family header row */}
            <div className="flex items-center gap-2 px-3 pt-3 pb-2">
              {/* Enable toggle */}
              <button
                onClick={() => toggleEnabled(family.id)}
                disabled={family.locked}
                className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 transition-colors duration-150 ${
                  family.locked
                    ? 'border-zinc-600 bg-zinc-600/30 cursor-not-allowed'
                    : family.enabled
                      ? 'border-accent bg-accent'
                      : 'border-zinc-600 hover:border-zinc-400'
                }`}
                title={family.locked ? 'Always present' : family.enabled ? 'Disable' : 'Enable'}
              >
                {(family.enabled || family.locked) && (
                  <svg width="8" height="8" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="2" className="text-zinc-950">
                    <path d="M1.5 5L4 7.5L8.5 2.5" />
                  </svg>
                )}
              </button>

              {/* Family name input */}
              <input
                type="text"
                value={family.familyName}
                onChange={(e) => setFamilyName(family.id, e.target.value)}
                disabled={!family.enabled && !family.locked}
                className="flex-1 bg-transparent border-b border-zinc-700 text-zinc-100 text-xs font-semibold py-0.5 focus:outline-none focus:border-accent transition-colors duration-150 disabled:opacity-50"
              />

              {family.locked && (
                <span className="text-[9px] uppercase tracking-wider text-zinc-600 shrink-0">locked</span>
              )}
            </div>

            {/* Tier rows */}
            <div className="flex flex-col gap-0 px-3 pb-3">
              {family.tiers.map((t) => (
                <div key={t.tier} className="flex items-center gap-2 py-1">
                  <span className="text-[10px] uppercase tracking-wider text-zinc-600 w-5 shrink-0 font-mono">
                    {TIER_LABELS[t.tier - 1]}
                  </span>
                  <input
                    type="text"
                    value={t.name}
                    onChange={(e) => setTierField(family.id, t.tier as 1 | 2 | 3, 'name', e.target.value)}
                    disabled={!family.enabled && !family.locked}
                    className="flex-1 bg-zinc-700/50 border border-zinc-700 text-zinc-100 text-xs px-2 py-1 rounded-lg focus:outline-none focus:border-accent transition-colors duration-150 disabled:opacity-50"
                  />
                  {/* Color swatch that opens native color picker */}
                  <label className="relative cursor-pointer shrink-0" title={`Pick color for ${t.name}`}>
                    <div
                      className="w-6 h-6 rounded-lg border-2 border-zinc-600 hover:border-zinc-400 transition-colors duration-150"
                      style={{ backgroundColor: t.color }}
                    />
                    <input
                      type="color"
                      value={t.color}
                      onChange={(e) => setTierField(family.id, t.tier as 1 | 2 | 3, 'color', e.target.value)}
                      className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                    />
                  </label>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-zinc-600">
        {enabledCount} {enabledCount === 1 ? 'family' : 'families'} enabled
      </p>

      <div className="flex justify-between pt-1">
        <button
          onClick={onBack}
          className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150"
        >
          Back
        </button>
        <button
          onClick={() => onNext({ biomeConfig: families })}
          disabled={enabledCount < 1}
          className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150 disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  )
}
