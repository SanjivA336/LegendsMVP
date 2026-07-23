import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useGameStore } from '../../../store/gameStore'
import { createWorldMap } from '../../../api/world'
import { createAdventureRecord, updateAdventureRecord } from '../../../api/adventures'
import { updateMember } from '../../../api/members'
import { createWorldState } from '../../../api/context'
import { createCharacter } from '../../../api/characters'
import { createQuest } from '../../../api/quests'
import { createWorldBible, generateOpeningScene } from '../../../api/worldbible'
import { seedMapPOIs } from '../../../api/pois'
import { createTemplate, createInstance } from '../../../api/entities'
import type { WizardData } from '../wizardData'

interface Props {
  data: WizardData
  adventureId: string
  onBack: () => void
}

const STEPS = [
  'Creating your adventure...',
  'Building the world map...',
  'Writing the world bible...',
  'Setting up templates...',
  'Placing instances...',
  'Weaving the opening quest...',
  'Forging your character...',
  'The DM prepares the scene...',
]

export default function LaunchStep({ data, adventureId, onBack }: Props) {
  const [stepIndex, setStepIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const started = useRef(false)
  const addAdventure = useGameStore((s) => s.addAdventure)
  const navigate = useNavigate()

  useEffect(() => {
    if (started.current) return
    started.current = true
    void launch()
  }, [])

  async function launch() {
    try {
      // 1. Create the adventure
      setStepIndex(0)
      const { adventure, member } = await createAdventureRecord({
        adventure_id: adventureId,
        name: data.campaignName,
        world_name: data.worldName,
        world_map_id: null,
        invite_code: data.inviteCode || undefined,
      })

      // 2. Commit the world map (exact same body as the last preview -- reproduces
      // the previewed map tile-for-tile), attach it to the adventure, seed POIs
      setStepIndex(1)
      const worldMap = await createWorldMap(data.worldGenParams)
      await updateAdventureRecord(adventureId, { world_map_id: worldMap.id })
      try {
        await seedMapPOIs({ adventure_id: adventureId, map_id: worldMap.id })
      } catch {
        // Non-fatal -- matches existing wizard precedent
      }

      // 3. World bible + world state
      setStepIndex(2)
      const biomeNameOverrides: Record<string, string> = {}
      const biomeColorOverrides: Record<string, string> = {}
      for (const family of data.biomeConfig) {
        for (const t of family.tiers) {
          const biomeId = family.id + (t.tier - 1) * 10
          biomeNameOverrides[String(biomeId)] = t.name
          biomeColorOverrides[String(biomeId)] = t.color
        }
      }
      await createWorldBible({
        adventure_id: adventureId,
        attribute_names: data.attributeNames,
        currency_name: data.currencyName,
        biome_name_overrides: biomeNameOverrides,
      })
      const enabledBiomeNames = data.biomeConfig.filter((f) => f.enabled).map((f) => f.familyName)
      await createWorldState({
        adventure_id: adventureId,
        facts: [`World biomes: ${enabledBiomeNames.join(', ')}`],
      })

      // 4. Templates -- in order, building a tempId -> real id map for step 5/7 to resolve
      setStepIndex(3)
      const templateIdMap: Record<string, string> = {}
      for (const draft of data.draftTemplates) {
        const created = await createTemplate({
          adventure_id: adventureId, kind: draft.kind, name: draft.name,
          description: draft.description, tags: draft.tags, fields: draft.fields,
        })
        templateIdMap[draft.tempId] = created.id
      }

      // 5. Instances -- resolve their template reference through the map above, and
      // record a tempId -> real id map of our own for step 7 to resolve the character's
      // equip/inventory picks (which reference draftInstances by tempId) through.
      setStepIndex(4)
      const instanceIdMap: Record<string, string> = {}
      for (const draft of data.draftInstances) {
        const created = await createInstance({
          adventure_id: adventureId, kind: draft.kind,
          template_id: draft.templateTempId ? templateIdMap[draft.templateTempId] ?? null : null,
          fields: draft.fields, notes: draft.notes,
        })
        instanceIdMap[draft.tempId] = created.id
      }

      // 6. Opening quest (optional)
      setStepIndex(5)
      if (data.questEnabled) {
        await createQuest({
          adventure_id: adventureId, length: data.questLength,
          context_hint: data.questContextHint || undefined,
        })
      }

      // 7. DM mode + (if AI) character, attached to the owner's member record
      setStepIndex(6)
      await updateAdventureRecord(adventureId, { dm_mode: data.dmMode })
      let characterId: string | null = null
      if (data.dmMode === 'ai') {
        const raceTemplateId = data.raceTemplateTempId ? templateIdMap[data.raceTemplateTempId] ?? null : null
        const classTemplateId = data.classTemplateTempId ? templateIdMap[data.classTemplateTempId] ?? null : null
        const startingInventoryIds = data.inventoryTempIds
          .map((tempId) => instanceIdMap[tempId]).filter((id): id is string => Boolean(id))
        const startingEquippedWearableIds = data.equippedWearableTempIds
          .map((tempId) => instanceIdMap[tempId]).filter((id): id is string => Boolean(id))
        const character = await createCharacter({
          adventure_id: adventureId, name: data.characterName, description: data.characterDescription,
          tone: data.characterTone, is_player: true, inventory_ids: [], equipped_weapon_id: null,
          race_template_id: raceTemplateId, class_template_id: classTemplateId,
          custom_fields: data.characterCustomFields,
          starting_inventory_ids: startingInventoryIds,
          starting_equipped_wearable_ids: startingEquippedWearableIds,
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
        characterId = character.id
        await updateMember(adventureId, member.id, { character_id: character.id })
      }

      // 8. Opening scene (non-fatal)
      setStepIndex(7)
      let openingNarrative: string | null = null
      try {
        const result = await generateOpeningScene({
          adventure_id: adventureId,
          character_name: data.dmMode === 'ai' ? data.characterName : null,
          world_name: data.worldName,
        })
        openingNarrative = result.narrative || null
      } catch {
        // Non-fatal
      }

      // 9. Write to the store and enter the game
      addAdventure({
        id: adventureId,
        name: data.campaignName,
        worldName: data.worldName,
        worldMapId: worldMap.id,
        playerCharacterId: characterId,
        role: 'owner',
        inviteCode: adventure.invite_code ?? data.inviteCode,
        createdAt: adventure.created_at,
        attributeNames: data.attributeNames,
        openingNarrative,
        biomeColorOverrides,
        spawnTileX: worldMap.spawn_tile_x ?? 32,
        spawnTileY: worldMap.spawn_tile_y ?? 32,
      })

      navigate(`/adventures/${adventureId}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Is the backend running?')
    }
  }

  function retry() {
    setError(null)
    void launch()
  }

  return (
    <div className="flex flex-col items-center gap-5 py-8">
      {!error ? (
        <>
          <div className="w-9 h-9 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          <div className="flex flex-col items-center gap-1">
            <p className="text-zinc-200 text-sm font-semibold">Launching your adventure</p>
            <p className="text-zinc-500 text-xs">{STEPS[stepIndex]}</p>
          </div>
        </>
      ) : (
        <>
          <div className="w-full p-3 bg-red-950 border border-red-800 rounded-xl text-sm text-red-300">
            {error}
          </div>
          <div className="flex gap-3">
            <button onClick={onBack} className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150">
              Back
            </button>
            <button
              onClick={retry}
              className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150"
            >
              Retry
            </button>
          </div>
        </>
      )}
    </div>
  )
}
