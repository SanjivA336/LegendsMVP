import { useState } from 'react'
import { THEME_PRESETS, findThemePreset } from '../themePresets'
import { expandTheme } from '../../../api/theme'
import type { WizardData, ThemeMode } from '../wizardData'

interface Props {
  data: WizardData
  onNext: (patch: Partial<WizardData>) => void
}

const inputClass =
  'bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-500 px-3 py-2.5 rounded-xl text-sm focus:outline-none focus:border-accent transition-colors duration-150'

export default function BasicInfoStep({ data, onNext }: Props) {
  const [campaignName, setCampaignName] = useState(data.campaignName)
  const [themeMode, setThemeMode] = useState<ThemeMode>(data.themeMode)
  const [presetId, setPresetId] = useState(data.themePresetId)
  const [pitch, setPitch] = useState(data.themePitch)
  const [worldName, setWorldName] = useState(data.worldName)
  const [attributeNames, setAttributeNames] = useState(data.attributeNames)
  const [currencyName, setCurrencyName] = useState(data.currencyName)
  const [biomeFamilyNames, setBiomeFamilyNames] = useState<Record<string, string> | null>(null)
  const [expanding, setExpanding] = useState(false)
  const [expandError, setExpandError] = useState<string | null>(null)

  function applyPreset(id: string) {
    setPresetId(id)
    const preset = findThemePreset(id)
    if (!preset) return
    setWorldName(preset.worldName)
    setAttributeNames(preset.attributeNames)
    setCurrencyName(preset.currencyName)
    setBiomeFamilyNames(preset.biomeFamilyNames)
  }

  async function handleExpand() {
    if (!pitch.trim()) return
    setExpanding(true)
    setExpandError(null)
    try {
      const result = await expandTheme(pitch.trim())
      setWorldName(result.world_name)
      setAttributeNames(result.attribute_names)
      setCurrencyName(result.currency_name)
      setBiomeFamilyNames(result.biome_family_names)
    } catch {
      setExpandError('Could not reach the DM for suggestions -- you can still continue with your own names.')
    } finally {
      setExpanding(false)
    }
  }

  function handleNext() {
    if (!campaignName.trim() || !worldName.trim()) return
    const patch: Partial<WizardData> = {
      campaignName: campaignName.trim(),
      themeMode,
      themePresetId: themeMode === 'preset' ? presetId : null,
      themePitch: themeMode === 'custom' ? pitch.trim() : '',
      worldName: worldName.trim(),
      attributeNames,
      currencyName: currencyName.trim() || 'Gold',
    }
    if (biomeFamilyNames) {
      patch.biomeConfig = data.biomeConfig.map((f) => ({
        ...f,
        familyName: biomeFamilyNames[f.familyKey] ?? f.familyName,
      }))
    }
    onNext(patch)
  }

  const canContinue = campaignName.trim() && worldName.trim() && (themeMode !== 'preset' || presetId)

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1.5">
        <label className="text-xs uppercase tracking-wider text-zinc-400">Campaign Name</label>
        <input
          type="text" value={campaignName} autoFocus
          onChange={(e) => setCampaignName(e.target.value)}
          placeholder="The Shattered Reaches"
          className={inputClass}
        />
        <p className="text-xs text-zinc-600">Displayed in your adventure list.</p>
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-xs uppercase tracking-wider text-zinc-400">Theming</label>
        <div className="flex gap-2">
          {(['preset', 'custom', 'blank'] as ThemeMode[]).map((mode) => (
            <button
              key={mode}
              onClick={() => setThemeMode(mode)}
              className={`flex-1 py-2 rounded-xl border text-xs font-semibold uppercase tracking-wider transition-colors duration-150 ${
                themeMode === mode
                  ? 'border-accent bg-accent/10 text-zinc-100'
                  : 'border-zinc-700 hover:border-zinc-600 text-zinc-400'
              }`}
            >
              {mode === 'preset' ? 'Pick a Theme' : mode === 'custom' ? 'Describe Your Own' : 'Start Blank'}
            </button>
          ))}
        </div>

        {themeMode === 'preset' && (
          <div className="grid grid-cols-2 gap-2 mt-1 max-h-64 overflow-y-auto pr-1">
            {THEME_PRESETS.map((preset) => (
              <button
                key={preset.id}
                onClick={() => applyPreset(preset.id)}
                className={`text-left rounded-xl border px-3 py-2.5 transition-colors duration-150 ${
                  presetId === preset.id
                    ? 'border-accent bg-zinc-800/80'
                    : 'border-zinc-700 bg-zinc-800/40 hover:border-zinc-600'
                }`}
              >
                <div className="text-sm font-semibold text-zinc-100">{preset.label}</div>
                <div className="text-xs text-zinc-500 mt-0.5">{preset.blurb}</div>
              </button>
            ))}
          </div>
        )}

        {themeMode === 'custom' && (
          <div className="flex flex-col gap-2 mt-1">
            <textarea
              value={pitch}
              onChange={(e) => setPitch(e.target.value)}
              placeholder="A rain-soaked cyberpunk megacity ruled by rival corporations..."
              rows={2}
              className={`${inputClass} resize-none`}
            />
            <button
              onClick={handleExpand}
              disabled={!pitch.trim() || expanding}
              className="self-start px-3 py-1.5 text-xs font-semibold text-accent hover:text-accent-hover border border-zinc-700 hover:border-accent rounded-lg transition-colors duration-150 disabled:opacity-40"
            >
              {expanding ? 'Asking the DM...' : 'Suggest Names'}
            </button>
            {expandError && <p className="text-xs text-red-400">{expandError}</p>}
          </div>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-xs uppercase tracking-wider text-zinc-400">World Name</label>
        <input
          type="text" value={worldName}
          onChange={(e) => setWorldName(e.target.value)}
          placeholder="Vaeltharion"
          className={inputClass}
        />
        <p className="text-xs text-zinc-600">
          Used to seed the world map. Attribute names, currency, and biome names can be
          fine-tuned in the next steps.
        </p>
      </div>

      <div className="flex justify-end pt-2">
        <button
          onClick={handleNext}
          disabled={!canContinue}
          className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150 disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  )
}
