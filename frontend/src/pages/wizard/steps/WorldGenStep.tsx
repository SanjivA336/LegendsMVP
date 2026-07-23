import { useState } from 'react'
import WorldMapGrid from '../../../components/world/WorldMapGrid'
import { previewWorldMap } from '../../../api/world'
import type { WorldMapGenerateRequest } from '../../../api/world'
import type { WorldMap, Tile } from '../../../types/world'
import type { WizardData, BioFamilyConfig } from '../wizardData'

interface Props {
  data: WizardData
  onNext: (patch: Partial<WizardData>) => void
  onBack: () => void
}

type PlacementMode = 'off' | 'elevation' | 'land'

const TIER_LABELS = ['T1', 'T2', 'T3'] as const

function biomeColorOverrides(families: BioFamilyConfig[]): Record<string, string> {
  const overrides: Record<string, string> = {}
  for (const family of families) {
    for (const t of family.tiers) {
      const biomeId = family.id + (t.tier - 1) * 10   // MAGIC_NUMBER = 10, matches biomes.py
      overrides[String(biomeId)] = t.color
    }
  }
  return overrides
}

export default function WorldGenStep({ data, onNext, onBack }: Props) {
  const [worldName, setWorldName] = useState(data.worldName)
  const [params, setParams] = useState(data.worldGenParams)
  const [families, setFamilies] = useState<BioFamilyConfig[]>(data.biomeConfig)
  const [map, setMap] = useState<WorldMap | null>(data.previewedMap)
  // The exact request body that produced `map` -- NOT necessarily equal to `params`,
  // since params can be edited after the last Regenerate click without a new preview
  // being fetched yet. Launch must reuse this exact body to reproduce `map` tile-for-tile,
  // so Next is disabled whenever it's out of sync with the currently displayed map.
  const [lastAppliedRequest, setLastAppliedRequest] = useState<WorldMapGenerateRequest | null>(
    data.previewedMap ? data.worldGenParams : null
  )
  const [placementMode, setPlacementMode] = useState<PlacementMode>('off')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function deriveGenParams(base = params) {
    const enabledLandFamilyIds = families.filter((f) => f.enabled && !f.locked).map((f) => f.id)
    const volcanoEnabled = families.find((f) => f.id === 8)?.enabled ?? true
    return {
      ...base,
      allowed_land_families: enabledLandFamilyIds.length > 0 ? enabledLandFamilyIds : undefined,
      volcano_chance: volcanoEnabled ? 0.35 : 0,
    }
  }

  async function regenerate(overrideParams = params) {
    setLoading(true)
    setError(null)
    try {
      const request = deriveGenParams(overrideParams)
      const result = await previewWorldMap(request)
      setMap(result)
      setParams(overrideParams)
      setLastAppliedRequest(request)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not generate a preview.')
    } finally {
      setLoading(false)
    }
  }

  function updateParam<K extends keyof typeof params>(key: K, value: (typeof params)[K]) {
    setParams((p) => ({ ...p, [key]: value, elevation_seed_positions: null, land_biome_seed_positions: null }))
  }

  function handleTileClick(tile: Tile) {
    if (placementMode === 'off') return
    if (placementMode === 'elevation') {
      const current = params.elevation_seed_positions ?? []
      const already = current.some(([x, y]) => x === tile.x && y === tile.y)
      const next = already
        ? current.filter(([x, y]) => !(x === tile.x && y === tile.y))
        : current.length < 3 ? [...current, [tile.x, tile.y] as [number, number]] : current
      setParams((p) => ({ ...p, elevation_seed_positions: next.length > 0 ? next : null }))
    } else {
      const current = params.land_biome_seed_positions ?? []
      const already = current.some(([x, y]) => x === tile.x && y === tile.y)
      const next = already
        ? current.filter(([x, y]) => !(x === tile.x && y === tile.y))
        : current.length < 12 ? [...current, [tile.x, tile.y] as [number, number]] : current
      setParams((p) => ({ ...p, land_biome_seed_positions: next.length > 0 ? next : null }))
    }
  }

  function toggleEnabled(id: number) {
    setFamilies((prev) => prev.map((f) => (f.id === id && !f.locked ? { ...f, enabled: !f.enabled } : f)))
  }

  function setFamilyName(id: number, name: string) {
    setFamilies((prev) => prev.map((f) => (f.id === id ? { ...f, familyName: name } : f)))
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

  // True whenever the currently displayed `map` was generated from different params
  // than what's now configured (a slider/toggle/seed change since the last Regenerate
  // click) -- Next is disabled until the user regenerates, so worldGenParams saved into
  // WizardData always exactly reproduces the previewed map at Launch.
  const isStale = !lastAppliedRequest || JSON.stringify(deriveGenParams(params)) !== JSON.stringify(lastAppliedRequest)

  function handleNext() {
    if (!map || !lastAppliedRequest) return
    onNext({
      worldName: worldName.trim() || data.worldName,
      worldGenParams: lastAppliedRequest,
      previewedMap: map,
      biomeConfig: families,
    })
  }

  const cellSize = Math.max(2, Math.min(9, Math.floor(340 / params.width!)))
  const enabledCount = families.filter((f) => f.enabled).length

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <input
          type="text" value={worldName}
          onChange={(e) => setWorldName(e.target.value)}
          className="flex-1 bg-transparent border-b border-zinc-700 text-zinc-100 text-base font-semibold py-1 focus:outline-none focus:border-accent transition-colors duration-150"
        />
      </div>

      <div className="grid grid-cols-2 gap-5">
        {/* Left: map preview + generation params */}
        <div className="flex flex-col gap-3">
          <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-2 flex items-center justify-center min-h-[220px]">
            {map ? (
              <WorldMapGrid map={map} cellSize={cellSize} onTileClick={handleTileClick}
                biomeColorOverrides={biomeColorOverrides(families)} />
            ) : (
              <p className="text-xs text-zinc-600">
                {loading ? 'Generating...' : 'No preview yet -- click Regenerate.'}
              </p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="flex flex-col gap-1">
              <label className="text-[10px] uppercase tracking-wider text-zinc-600">Map Size</label>
              <input
                type="number" min={8} max={128} value={params.width}
                onChange={(e) => {
                  const size = Number(e.target.value) || 64
                  updateParam('width', size)
                  updateParam('height', size)
                }}
                className="bg-zinc-800 border border-zinc-700 text-zinc-100 px-2.5 py-1.5 rounded-lg text-xs focus:outline-none focus:border-accent transition-colors duration-150"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] uppercase tracking-wider text-zinc-600">Seed</label>
              <input
                type="number" value={params.seed}
                onChange={(e) => updateParam('seed', Number(e.target.value) || 0)}
                className="bg-zinc-800 border border-zinc-700 text-zinc-100 px-2.5 py-1.5 rounded-lg text-xs focus:outline-none focus:border-accent transition-colors duration-150"
              />
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-wider text-zinc-600 flex justify-between">
              <span>Sea Level</span><span>{Math.round((params.percent_ocean ?? 0) * 100)}%</span>
            </label>
            <input
              type="range" min={0} max={60} value={Math.round((params.percent_ocean ?? 0) * 100)}
              onChange={(e) => updateParam('percent_ocean', Number(e.target.value) / 100)}
              className="w-full accent-accent"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-wider text-zinc-600 flex justify-between">
              <span>Mountain Level</span><span>{Math.round((params.percent_mountain ?? 0) * 100)}%</span>
            </label>
            <input
              type="range" min={0} max={60} value={Math.round((params.percent_mountain ?? 0) * 100)}
              onChange={(e) => updateParam('percent_mountain', Number(e.target.value) / 100)}
              className="w-full accent-accent"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-wider text-zinc-600">Manual Seed Placement</label>
            <div className="flex gap-1.5">
              {(['off', 'elevation', 'land'] as PlacementMode[]).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setPlacementMode(mode)}
                  className={`flex-1 py-1.5 rounded-lg text-[11px] font-semibold uppercase tracking-wider transition-colors duration-150 ${
                    placementMode === mode
                      ? 'bg-accent text-zinc-950'
                      : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
                  }`}
                >
                  {mode === 'off' ? 'Off' : mode === 'elevation' ? 'Mountains' : 'Biomes'}
                </button>
              ))}
            </div>
            {placementMode !== 'off' && (
              <p className="text-[10px] text-zinc-600 mt-0.5">
                Click the map to place (click again to remove). {placementMode === 'elevation' ? 'Up to 3.' : 'Up to 12.'}
              </p>
            )}
          </div>

          {error && <p className="text-xs text-red-400">{error}</p>}

          <button
            onClick={() => regenerate()}
            disabled={loading}
            className="px-3 py-2 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-200 text-sm font-semibold rounded-xl transition-colors duration-150 disabled:opacity-50"
          >
            {loading ? 'Generating...' : 'Regenerate'}
          </button>
        </div>

        {/* Right: biome family/tier panel */}
        <div className="flex flex-col gap-2 max-h-[520px] overflow-y-auto pr-1">
          {[...families].sort((a, b) => a.familyName.localeCompare(b.familyName)).map((family) => (
            <div
              key={family.id}
              className={`rounded-xl border transition-colors duration-150 ${
                family.enabled ? 'border-zinc-700 bg-zinc-800/60' : 'border-zinc-800 bg-zinc-900/60 opacity-60'
              }`}
            >
              <div className="flex items-center gap-2 px-3 pt-2.5 pb-1.5">
                <button
                  onClick={() => toggleEnabled(family.id)}
                  disabled={family.locked}
                  className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 transition-colors duration-150 ${
                    family.locked
                      ? 'border-zinc-600 bg-zinc-600/30 cursor-not-allowed'
                      : family.enabled ? 'border-accent bg-accent' : 'border-zinc-600 hover:border-zinc-400'
                  }`}
                  title={family.locked ? 'Always present' : family.enabled ? 'Disable' : 'Enable'}
                >
                  {(family.enabled || family.locked) && (
                    <svg width="8" height="8" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="2" className="text-zinc-950">
                      <path d="M1.5 5L4 7.5L8.5 2.5" />
                    </svg>
                  )}
                </button>
                <input
                  type="text" value={family.familyName}
                  onChange={(e) => setFamilyName(family.id, e.target.value)}
                  disabled={!family.enabled && !family.locked}
                  className="flex-1 bg-transparent border-b border-zinc-700 text-zinc-100 text-xs font-semibold py-0.5 focus:outline-none focus:border-accent transition-colors duration-150 disabled:opacity-50"
                />
              </div>
              <div className="flex flex-col gap-0 px-3 pb-2.5">
                {family.tiers.map((t) => (
                  <div key={t.tier} className="flex items-center gap-2 py-0.5">
                    <span className="text-[9px] uppercase tracking-wider text-zinc-600 w-5 shrink-0 font-mono">
                      {TIER_LABELS[t.tier - 1]}
                    </span>
                    <input
                      type="text" value={t.name}
                      onChange={(e) => setTierField(family.id, t.tier as 1 | 2 | 3, 'name', e.target.value)}
                      disabled={!family.enabled && !family.locked}
                      className="flex-1 bg-zinc-700/50 border border-zinc-700 text-zinc-100 text-xs px-2 py-1 rounded-lg focus:outline-none focus:border-accent transition-colors duration-150 disabled:opacity-50"
                    />
                    <label className="relative cursor-pointer shrink-0" title={`Pick color for ${t.name}`}>
                      <div className="w-5 h-5 rounded-md border-2 border-zinc-600 hover:border-zinc-400 transition-colors duration-150"
                        style={{ backgroundColor: t.color }} />
                      <input
                        type="color" value={t.color}
                        onChange={(e) => setTierField(family.id, t.tier as 1 | 2 | 3, 'color', e.target.value)}
                        className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                      />
                    </label>
                  </div>
                ))}
              </div>
            </div>
          ))}
          <p className="text-xs text-zinc-600">{enabledCount} {enabledCount === 1 ? 'family' : 'families'} enabled</p>
        </div>
      </div>

      <div className="flex items-center justify-between pt-2">
        <button onClick={onBack} className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150">
          Back
        </button>
        <div className="flex items-center gap-3">
          {map && isStale && (
            <span className="text-xs text-zinc-500">Regenerate to apply your changes</span>
          )}
          <button
            onClick={handleNext}
            disabled={!map || isStale}
            className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
