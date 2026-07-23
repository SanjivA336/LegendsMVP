import { useEffect, useState } from 'react'
import Modal from '../ui/Modal'
import CharacterFieldsForm from './creation/CharacterFieldsForm'
import WearableEquipPicker from './creation/WearableEquipPicker'
import InventoryPicker from './creation/InventoryPicker'
import CharacterSummary from './creation/CharacterSummary'
import InstanceModal from '../blueprint/InstanceModal'
import { listTemplates, listInstances, createInstance } from '../../api/entities'
import { createCharacter } from '../../api/characters'
import { mergeFields, getFieldValue } from '../../types/blueprint'
import { nonCanonicalFields } from './creation/types'
import type { Template, Instance, CustomField, Kind } from '../../types/blueprint'
import type { DraftTemplate, DraftInstance } from '../../pages/wizard/draftTypes'
import type { ItemCandidate } from './creation/types'

interface Props {
  open: boolean
  adventureId: string
  onClose: () => void
  onCreated?: () => void
}

type ModalStep = 'fields' | 'equip' | 'inventory' | 'confirm'
const STEP_ORDER: ModalStep[] = ['fields', 'equip', 'inventory', 'confirm']
const STEP_TITLES: Record<ModalStep, string> = {
  fields: 'Create Character', equip: 'Equip Gear', inventory: 'Inventory', confirm: 'Confirm',
}

const INVENTORY_KINDS: Kind[] = ['weapon', 'wearable', 'consumable', 'custom']
const ADDABLE_KINDS: { value: Kind; label: string }[] = [
  { value: 'weapon', label: 'Weapon' },
  { value: 'wearable', label: 'Wearable' },
  { value: 'consumable', label: 'Consumable' },
  { value: 'custom', label: 'Custom' },
]

function toDraftTemplate(t: Template): DraftTemplate {
  return { tempId: t.id, kind: t.kind, name: t.name, description: t.description, tags: t.tags, fields: t.fields }
}

function resolveCandidate(instance: Instance, templatesById: Map<string, Template>): ItemCandidate {
  const template = instance.template_id ? templatesById.get(instance.template_id) ?? null : null
  const merged = mergeFields(template?.fields ?? [], instance.fields)
  const slot = getFieldValue(merged, 'slot')
  return { id: instance.id, name: template?.name ?? 'Unnamed Item', slot: typeof slot === 'string' ? slot : undefined }
}

function resolveDraftCandidate(draft: DraftInstance, draftTemplates: DraftTemplate[]): ItemCandidate {
  const template = draftTemplates.find((t) => t.tempId === draft.templateTempId) ?? null
  const merged = mergeFields(template?.fields ?? [], draft.fields)
  const slot = getFieldValue(merged, 'slot')
  return { id: draft.tempId, name: template?.name ?? 'Unnamed Item', slot: typeof slot === 'string' ? slot : undefined }
}

export default function CharacterCreationModal({ open, adventureId, onClose, onCreated }: Props) {
  const [step, setStep] = useState<ModalStep>('fields')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [committing, setCommitting] = useState(false)

  const [races, setRaces] = useState<Template[]>([])
  const [classes, setClasses] = useState<Template[]>([])
  const [characterTemplate, setCharacterTemplate] = useState<Template | null>(null)
  const [items, setItems] = useState<Instance[]>([])
  const [itemTemplates, setItemTemplates] = useState<Template[]>([])
  const [newDraftInstances, setNewDraftInstances] = useState<DraftInstance[]>([])
  const [addingKind, setAddingKind] = useState<Kind | null>(null)

  const [isPlayer, setIsPlayer] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [tone, setTone] = useState('')
  const [raceId, setRaceId] = useState<string | null>(null)
  const [classId, setClassId] = useState<string | null>(null)
  const [customFields, setCustomFields] = useState<CustomField[]>([])
  const [equippedIds, setEquippedIds] = useState<string[]>([])
  const [inventoryIds, setInventoryIds] = useState<string[]>([])

  useEffect(() => {
    if (!open) return
    setStep('fields'); setError(null); setLoading(true)
    setIsPlayer(false); setName(''); setDescription(''); setTone('')
    setRaceId(null); setClassId(null); setCustomFields([])
    setEquippedIds([]); setInventoryIds([]); setNewDraftInstances([])

    Promise.all([
      listTemplates(adventureId, 'race'),
      listTemplates(adventureId, 'class'),
      listTemplates(adventureId, 'character'),
      Promise.all(INVENTORY_KINDS.map((k) => listTemplates(adventureId, k))),
      Promise.all(INVENTORY_KINDS.map((k) => listInstances(adventureId, k))),
    ])
      .then(([raceList, classList, charTemplates, templateLists, instanceLists]) => {
        setRaces(raceList)
        setClasses(classList)
        const charTemplate = charTemplates[0] ?? null
        setCharacterTemplate(charTemplate)
        setCustomFields(charTemplate ? nonCanonicalFields(mergeFields(charTemplate.fields, [])) : [])
        setItemTemplates(templateLists.flat())
        setItems(instanceLists.flat().filter((i) => i.owner_id === null))
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load adventure content'))
      .finally(() => setLoading(false))
  }, [open, adventureId])

  if (!open) return null

  const templatesById = new Map(itemTemplates.map((t) => [t.id, t]))
  const realCandidates = items.map((i) => resolveCandidate(i, templatesById))
  const draftCandidates = newDraftInstances.map((d) => resolveDraftCandidate(d, itemTemplates.map(toDraftTemplate)))
  const allCandidates = [...realCandidates, ...draftCandidates]
  const wearableCandidates = allCandidates.filter((c) => {
    const real = items.find((i) => i.id === c.id)
    const draft = newDraftInstances.find((d) => d.tempId === c.id)
    return (real?.kind ?? draft?.kind) === 'wearable'
  })

  function handleNewInstance(draft: DraftInstance) {
    setNewDraftInstances((prev) => [...prev, draft])
  }

  function goNextStep() {
    const idx = STEP_ORDER.indexOf(step)
    setStep(STEP_ORDER[Math.min(idx + 1, STEP_ORDER.length - 1)])
  }
  function goPrevStep() {
    const idx = STEP_ORDER.indexOf(step)
    if (idx === 0) { onClose(); return }
    setStep(STEP_ORDER[idx - 1])
  }

  async function handleCreate() {
    setCommitting(true)
    setError(null)
    try {
      // Newly-drafted items only exist locally so far -- create them for real first,
      // then resolve every selection (pre-existing real ids or freshly-created ones)
      // into the id set create_character claims ownership of.
      const draftIdMap: Record<string, string> = {}
      for (const draft of newDraftInstances) {
        const created = await createInstance({
          adventure_id: adventureId, kind: draft.kind, template_id: draft.templateTempId,
          fields: draft.fields, notes: draft.notes,
        })
        draftIdMap[draft.tempId] = created.id
      }
      const resolve = (id: string) => draftIdMap[id] ?? id
      const startingInventoryIds = inventoryIds.map(resolve)
      const startingEquippedWearableIds = equippedIds.map(resolve)

      await createCharacter({
        adventure_id: adventureId, name: name.trim(), description: description.trim(), tone: tone.trim(),
        is_player: isPlayer, inventory_ids: [], equipped_weapon_id: null,
        race_template_id: raceId, class_template_id: classId,
        custom_fields: customFields,
        starting_inventory_ids: startingInventoryIds,
        starting_equipped_wearable_ids: startingEquippedWearableIds,
        stats: { strength: 10, dexterity: 10, intelligence: 10, fortitude: 10, charisma: 10, reflex: 10 },
        metadata: {},
      })

      onCreated?.()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create character')
    } finally {
      setCommitting(false)
    }
  }

  const raceOptions = races.map((r) => ({ id: r.id, name: r.name }))
  const classOptions = classes.map((c) => ({ id: c.id, name: c.name }))
  const raceName = races.find((r) => r.id === raceId)?.name ?? null
  const className = classes.find((c) => c.id === classId)?.name ?? null
  const equippedItems = allCandidates.filter((c) => equippedIds.includes(c.id))
  const inventoryItems = allCandidates.filter((c) => Array.from(new Set([...inventoryIds, ...equippedIds])).includes(c.id))

  return (
    <Modal open={open} onClose={onClose} title={STEP_TITLES[step]} maxWidth="max-w-2xl">
      {loading ? (
        <p className="text-sm text-zinc-500">Loading adventure content...</p>
      ) : (
        <div className="flex flex-col gap-5">
          {error && (
            <div className="p-3 bg-red-950 border border-red-800 rounded-xl text-sm text-red-300">{error}</div>
          )}

          {step === 'fields' && (
            <>
              <label className="flex items-center gap-2 text-xs text-zinc-400 -mb-2">
                <input type="checkbox" checked={isPlayer} onChange={(e) => setIsPlayer(e.target.checked)} />
                This is a player character (unchecked = NPC)
              </label>
              <CharacterFieldsForm
                name={name} onNameChange={setName}
                description={description} onDescriptionChange={setDescription}
                tone={tone} onToneChange={setTone}
                raceId={raceId} onRaceChange={setRaceId}
                classId={classId} onClassChange={setClassId}
                races={raceOptions} classes={classOptions}
                customFields={customFields} onCustomFieldsChange={setCustomFields}
                showCustomFields={Boolean(characterTemplate)}
              />
            </>
          )}

          {step === 'equip' && (
            <WearableEquipPicker
              candidates={wearableCandidates} equippedIds={equippedIds}
              onChange={setEquippedIds} onAddNew={() => setAddingKind('wearable')}
            />
          )}

          {step === 'inventory' && (
            <div className="flex flex-col gap-3">
              <InventoryPicker candidates={allCandidates} selectedIds={inventoryIds} onChange={setInventoryIds} />
              <div className="flex flex-wrap gap-2">
                {ADDABLE_KINDS.map((k) => (
                  <button
                    key={k.value}
                    onClick={() => setAddingKind(k.value)}
                    className="px-3 py-1.5 text-xs font-semibold text-accent hover:text-accent-hover border border-zinc-700 hover:border-accent rounded-lg transition-colors duration-150"
                  >
                    + New {k.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 'confirm' && (
            <CharacterSummary
              name={name} description={description} tone={tone}
              raceName={raceName} className={className}
              stats={{ strength: 10, dexterity: 10, intelligence: 10, fortitude: 10, charisma: 10, reflex: 10 }}
              attributeNames={{}}
              customFields={customFields}
              equippedItems={equippedItems} inventoryItems={inventoryItems}
            />
          )}

          {addingKind && (
            <InstanceModal
              open={Boolean(addingKind)} onClose={() => setAddingKind(null)} onSave={handleNewInstance}
              templates={itemTemplates.filter((t) => t.kind === addingKind).map(toDraftTemplate)}
              kind={addingKind}
            />
          )}

          <div className="flex justify-between pt-2">
            <button
              onClick={goPrevStep}
              className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150"
            >
              {step === 'fields' ? 'Cancel' : 'Back'}
            </button>
            {step === 'confirm' ? (
              <button
                onClick={handleCreate}
                disabled={committing || !name.trim()}
                className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150 disabled:opacity-40"
              >
                {committing ? 'Creating...' : 'Create Character'}
              </button>
            ) : (
              <button
                onClick={goNextStep}
                disabled={step === 'fields' && !name.trim()}
                className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150 disabled:opacity-40"
              >
                Next
              </button>
            )}
          </div>
        </div>
      )}
    </Modal>
  )
}
