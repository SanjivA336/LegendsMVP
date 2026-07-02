import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useGameStore } from '../../store/gameStore'
import { createWorldMap } from '../../api/world'
import { createAdventureRecord } from '../../api/adventures'
import { createWorldState } from '../../api/context'
import { createContextCard } from '../../api/context'
import { createCharacter } from '../../api/characters'
import { createQuest } from '../../api/quests'
import { createWorldBible, generateOpeningScene } from '../../api/worldbible'
import { seedMapPOIs } from '../../api/pois'
import AdventureInfoStep from './steps/AdventureInfoStep'
import MapSizeStep from './steps/MapSizeStep'
import BiomeSetupStep from './steps/BiomeSetupStep'
import WorldBibleStep from './steps/WorldBibleStep'
import CharacterCreationStep from './steps/CharacterCreationStep'
import StatRollStep from './steps/StatRollStep'
import ExtraContextStep from './steps/ExtraContextStep'
import QuestSetupStep from './steps/QuestSetupStep'
import type { QuestLength } from '../../types/quest'

// ── Biome config types ─────────────────────────────────────────────────────────

export interface BioTierConfig {
  tier: 1 | 2 | 3
  name: string
  color: string
}

export interface BioFamilyConfig {
  id: number          // BiomeFamily.value from biomes.py
  familyName: string  // display / custom name
  enabled: boolean    // include in world generation
  locked: boolean     // can't be disabled (Ocean, Mountain)
  tiers: BioTierConfig[]
}

// Default biome families mirroring biomes.py (id + (tier-1)*10 = biome_id)
const DEFAULT_BIOME_CONFIG: BioFamilyConfig[] = [
  { id: 0, familyName: 'Arid',      enabled: true,  locked: false, tiers: [
    { tier: 1, name: 'Savannah',       color: '#c8a951' },
    { tier: 2, name: 'Desert',         color: '#d4a347' },
    { tier: 3, name: 'Scorched Earth', color: '#8b4513' },
  ]},
  { id: 1, familyName: 'Grassland', enabled: true,  locked: false, tiers: [
    { tier: 1, name: 'Plains',         color: '#7cbc5a' },
    { tier: 2, name: 'Steppe',         color: '#5a9444' },
    { tier: 3, name: 'Barren Fields',  color: '#4a7c34' },
  ]},
  { id: 2, familyName: 'Woodland',  enabled: true,  locked: false, tiers: [
    { tier: 1, name: 'Forest',         color: '#2d6e2d' },
    { tier: 2, name: 'Wild Forest',    color: '#1e5c1e' },
    { tier: 3, name: 'Ancient Forest', color: '#0f4f14' },
  ]},
  { id: 3, familyName: 'Tropical',  enabled: true,  locked: false, tiers: [
    { tier: 1, name: 'Rainforest',     color: '#1a9a2a' },
    { tier: 2, name: 'Jungle',         color: '#0d7a1e' },
    { tier: 3, name: 'Overgrown Jungle', color: '#055a14' },
  ]},
  { id: 4, familyName: 'Wetland',   enabled: true,  locked: false, tiers: [
    { tier: 1, name: 'Floodplains',    color: '#4a7c5c' },
    { tier: 2, name: 'Swamp',          color: '#3b6b48' },
    { tier: 3, name: 'Blighted Swamp', color: '#2a4a35' },
  ]},
  { id: 5, familyName: 'Arctic',    enabled: true,  locked: false, tiers: [
    { tier: 1, name: 'Taiga',          color: '#a8c4a8' },
    { tier: 2, name: 'Frozen Tundra',  color: '#c8d8d8' },
    { tier: 3, name: 'Frozen Wastes',  color: '#e8f0f0' },
  ]},
  { id: 6, familyName: 'Ocean',     enabled: true,  locked: true,  tiers: [
    { tier: 1, name: 'Coast',          color: '#2a6a9a' },
    { tier: 2, name: 'Storm Sea',      color: '#1a5080' },
    { tier: 3, name: 'Abyssal Depths', color: '#0a3060' },
  ]},
  { id: 7, familyName: 'Mountain',  enabled: true,  locked: true,  tiers: [
    { tier: 1, name: 'Foothills',      color: '#78716c' },
    { tier: 2, name: 'Broken Mountains', color: '#57534e' },
    { tier: 3, name: 'Jagged Peaks',   color: '#a89890' },
  ]},
  { id: 8, familyName: 'Volcanic',  enabled: true,  locked: false, tiers: [
    { tier: 1, name: 'Ash Foothills',  color: '#6b5a4a' },
    { tier: 2, name: 'Cinder Mountains', color: '#3d2b1f' },
    { tier: 3, name: 'Infernal Cauldron', color: '#8b0000' },
  ]},
]

// ── World Bible config ─────────────────────────────────────────────────────────

export interface WorldBibleData {
  attributeNames: Record<string, string>
  currencyName: string
}

// ── Wizard data ────────────────────────────────────────────────────────────────

export interface WizardData {
  adventureName: string
  worldName: string
  mapSize: 'small' | 'medium' | 'large'
  biomeConfig: BioFamilyConfig[]
  worldBible: WorldBibleData
  characterName: string
  characterDescription: string
  characterTone: string
  rolledStats: number[]
  statAssignments: Record<string, number>
  extraCards: { label: string; content: string; keyword: string }[]
  questEnabled: boolean
  questLength: QuestLength
  questContextHint: string
}

const DEFAULT_ATTRIBUTE_NAMES: Record<string, string> = {
  strength: 'Strength',
  dexterity: 'Dexterity',
  intelligence: 'Intelligence',
  fortitude: 'Fortitude',
  charisma: 'Charisma',
  reflex: 'Reflex',
}

const INITIAL_DATA: WizardData = {
  adventureName: '',
  worldName: '',
  mapSize: 'medium',
  biomeConfig: DEFAULT_BIOME_CONFIG,
  worldBible: { attributeNames: { ...DEFAULT_ATTRIBUTE_NAMES }, currencyName: 'Gold' },
  characterName: '',
  characterDescription: '',
  characterTone: '',
  rolledStats: [],
  statAssignments: {},
  extraCards: [],
  questEnabled: false,
  questLength: 'medium',
  questContextHint: '',
}

const STEP_TITLES = [
  'Adventure Info',
  'Map Size',
  'World Generation',
  'World Bible',
  'Your Character',
  'Assign Stats',
  'Extra Context',
  'Opening Quest',
]

const CREATION_STEPS = [
  'Creating world map...',
  'Establishing world state...',
  'Building world bible...',
  'Forging your character...',
  'Weaving the opening quest...',
  'The DM prepares the scene...',
]

function hashSeed(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = Math.imul(31, h) + s.charCodeAt(i)
    h |= 0
  }
  return Math.abs(h) % 2_147_483_647
}

export default function AdventureWizard() {
  const [step, setStep] = useState(0)
  const [wizardData, setWizardData] = useState<WizardData>(INITIAL_DATA)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [creationStep, setCreationStep] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const addAdventure = useGameStore((s) => s.addAdventure)
  const navigate = useNavigate()

  function applyPatch<T extends Partial<WizardData>>(patch: T) {
    setWizardData((prev) => ({ ...prev, ...patch }))
    setStep((s) => s + 1)
  }

  async function handleFinish(finalPatch: Pick<WizardData, 'questEnabled' | 'questLength' | 'questContextHint'>) {
    const data = { ...wizardData, ...finalPatch }
    setIsSubmitting(true)
    setCreationStep(0)
    setError(null)

    try {
      const adventureId = crypto.randomUUID()
      const seed = hashSeed(data.worldName)

      // Derive allowed land families (non-locked enabled families)
      const enabledLandFamilyIds = data.biomeConfig
        .filter((f) => f.enabled && !f.locked)
        .map((f) => f.id)

      // Volcanic is family id=8; disable it by setting volcano_chance=0 when excluded
      const volcanoEnabled = data.biomeConfig.find((f) => f.id === 8)?.enabled ?? true

      const MAP_DIMS = { small: 32, medium: 64, large: 128 }
      const mapDim = MAP_DIMS[data.mapSize] ?? 64

      // 1. Create world map
      setCreationStep(0)
      const worldMap = await createWorldMap({
        adventure_id: adventureId,
        seed,
        width: mapDim,
        height: mapDim,
        allowed_land_families: enabledLandFamilyIds.length > 0 ? enabledLandFamilyIds : undefined,
        volcano_chance: volcanoEnabled ? 0.35 : 0.0,
      })

      // 2. Create world state (facts derived from enabled biome families)
      setCreationStep(1)
      const biomeNames = data.biomeConfig
        .filter((f) => f.enabled)
        .map((f) => f.familyName)
      await createWorldState({
        adventure_id: adventureId,
        facts: [`World biomes: ${biomeNames.join(', ')}`],
      })

      // 3. Create world bible (attribute names + biome overrides) and seed POIs
      setCreationStep(2)
      const biomeNameOverrides: Record<string, string> = {}
      const biomeColorOverrides: Record<string, string> = {}
      for (const family of data.biomeConfig) {
        for (const t of family.tiers) {
          const biomeId = family.id + (t.tier - 1) * 10  // MAGIC_NUMBER = 10
          biomeNameOverrides[String(biomeId)] = t.name
          biomeColorOverrides[String(biomeId)] = t.color
        }
      }
      await createWorldBible({
        adventure_id: adventureId,
        attribute_names: data.worldBible.attributeNames,
        currency_name: data.worldBible.currencyName,
        biome_name_overrides: biomeNameOverrides,
      })
      // Seed all POIs for the new map (non-fatal if it fails)
      try {
        await seedMapPOIs({ adventure_id: adventureId, map_id: worldMap.id })
      } catch {
        // POI seeding failure doesn't block adventure creation
      }

      // 4. Extra keyword-triggered context cards
      for (const card of data.extraCards) {
        await createContextCard({
          adventure_id: adventureId,
          label: card.label,
          content: card.content,
          always_inject: false,
          keyword_trigger: card.keyword,
          event_trigger: null,
        })
      }

      // 5. Create player character
      setCreationStep(3)
      const character = await createCharacter({
        adventure_id: adventureId,
        name: data.characterName,
        description: data.characterDescription,
        tone: data.characterTone,
        is_player: true,
        inventory_ids: [],
        equipped_weapon_id: null,
        stats: {
          strength: data.statAssignments.strength ?? 10,
          dexterity: data.statAssignments.dexterity ?? 10,
          intelligence: data.statAssignments.intelligence ?? 10,
          fortitude: data.statAssignments.fortitude ?? 10,
          charisma: data.statAssignments.charisma ?? 10,
          reflex: data.statAssignments.reflex ?? 10,
        },
        metadata: {},
      })

      // 6. Optionally create opening quest
      setCreationStep(4)
      if (data.questEnabled) {
        await createQuest({
          adventure_id: adventureId,
          length: data.questLength,
          context_hint: data.questContextHint || undefined,
        })
      }

      // 7. Generate DM opening scene
      setCreationStep(5)
      let openingNarrative: string | null = null
      try {
        const result = await generateOpeningScene({
          adventure_id: adventureId,
          character_name: data.characterName,
          world_name: data.worldName,
        })
        openingNarrative = result.narrative || null
      } catch {
        // Opening scene failure is non-fatal
      }

      // 8. Persist adventure to Firestore (non-fatal if backend returns 401 before auth is wired)
      let inviteCode: string | null = null
      try {
        const result = await createAdventureRecord({
          adventure_id: adventureId,
          name: data.adventureName,
          world_name: data.worldName,
          world_map_id: worldMap.id,
        })
        inviteCode = result.adventure.invite_code ?? null
      } catch {
        // Non-fatal during dev — adventure still playable locally
      }

      // 9. Write adventure meta to Zustand store
      addAdventure({
        id: adventureId,
        name: data.adventureName,
        worldName: data.worldName,
        worldMapId: worldMap.id,
        playerCharacterId: character.id,
        role: 'owner',
        inviteCode,
        createdAt: new Date().toISOString(),
        attributeNames: data.worldBible.attributeNames,
        openingNarrative,
        biomeColorOverrides,
        spawnTileX: worldMap.spawn_tile_x ?? 32,
        spawnTileY: worldMap.spawn_tile_y ?? 32,
      })

      navigate(`/adventures/${adventureId}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Is the backend running?')
      setIsSubmitting(false)
    }
  }

  const totalSteps = STEP_TITLES.length

  return (
    <>
      {/* Loading overlay */}
      {isSubmitting && (
        <div className="fixed inset-0 bg-zinc-950/85 backdrop-blur-sm z-50 flex flex-col items-center justify-center gap-5">
          <div className="w-9 h-9 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          <div className="flex flex-col items-center gap-1">
            <p className="text-zinc-200 text-sm font-semibold">Creating your adventure</p>
            <p className="text-zinc-500 text-xs">{CREATION_STEPS[creationStep]}</p>
          </div>
        </div>
      )}

      <div className="flex-1 flex items-start justify-center px-4 py-12">
        <div className="w-full max-w-2xl">
          {/* Progress bar */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs uppercase tracking-wider text-zinc-400">
                Step {step + 1} of {totalSteps}
              </span>
              <span className="text-xs font-semibold text-zinc-300">{STEP_TITLES[step]}</span>
            </div>
            <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-accent rounded-full transition-[width] duration-300"
                style={{ width: `${((step + 1) / totalSteps) * 100}%` }}
              />
            </div>
          </div>

          {/* Step card */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
            <h2 className="text-lg font-semibold tracking-tight text-zinc-100 mb-5">
              {STEP_TITLES[step]}
            </h2>

            {error && (
              <div className="mb-4 p-3 bg-red-950 border border-red-800 rounded-xl text-sm text-red-300">
                {error}
              </div>
            )}

            {step === 0 && <AdventureInfoStep data={wizardData} onNext={applyPatch} onBack={() => {}} />}
            {step === 1 && <MapSizeStep       data={wizardData} onNext={applyPatch} onBack={() => setStep(0)} />}
            {step === 2 && <BiomeSetupStep    data={wizardData} onNext={applyPatch} onBack={() => setStep(1)} />}
            {step === 3 && <WorldBibleStep    data={wizardData} onNext={applyPatch} onBack={() => setStep(2)} />}
            {step === 4 && <CharacterCreationStep data={wizardData} onNext={applyPatch} onBack={() => setStep(3)} />}
            {step === 5 && <StatRollStep      data={wizardData} onNext={applyPatch} onBack={() => setStep(4)} />}
            {step === 6 && <ExtraContextStep  data={wizardData} onNext={applyPatch} onBack={() => setStep(5)} />}
            {step === 7 && (
              <QuestSetupStep
                data={wizardData}
                onNext={handleFinish}
                onBack={() => setStep(6)}
                isSubmitting={isSubmitting}
              />
            )}
          </div>
        </div>
      </div>
    </>
  )
}
