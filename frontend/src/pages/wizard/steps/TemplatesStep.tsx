import { useState } from 'react'
import TemplateModal from '../../../components/blueprint/TemplateModal'
import type { CustomField, Kind } from '../../../types/blueprint'
import type { DraftTemplate } from '../draftTypes'
import type { WizardData } from '../wizardData'

interface Props {
  data: WizardData
  onNext: (patch: Partial<WizardData>) => void
  onBack: () => void
}

// Mirrors backend/routers/entities.py's _STARTER_RACES/_STARTER_CLASSES exactly --
// pre-populated client-side (no backend seed call) the first time this step is reached.
const STARTER_RACES: [string, Record<string, number>][] = [
  ['Human', {}], ['Elf', { dexterity: 2 }], ['Dwarf', { fortitude: 2 }], ['Halfling', { charisma: 2 }],
]
const STARTER_CLASSES: [string, Record<string, number>][] = [
  ['Fighter', { strength: 2 }], ['Wizard', { intelligence: 2 }], ['Rogue', { dexterity: 2 }], ['Cleric', { fortitude: 2 }],
]

function statBonusFields(bonuses: Record<string, number>): CustomField[] {
  return Object.entries(bonuses).map(([stat, delta]) => ({
    key: stat, label: stat[0].toUpperCase() + stat.slice(1), field_type: 'number', value: delta,
    is_enum: false, options: [], required: false, bound_behavior: 'stat', hidden: false,
  }))
}

function starterTemplates(): DraftTemplate[] {
  const races = STARTER_RACES.map(([name, bonuses]): DraftTemplate => ({
    tempId: crypto.randomUUID(), kind: 'race', name, description: '', tags: ['starter'], fields: statBonusFields(bonuses),
  }))
  const classes = STARTER_CLASSES.map(([name, bonuses]): DraftTemplate => ({
    tempId: crypto.randomUUID(), kind: 'class', name, description: '', tags: ['starter'], fields: statBonusFields(bonuses),
  }))
  return [...races, ...classes]
}

const KIND_LABELS: Record<Kind, string> = {
  race: 'Races', class: 'Classes', weapon: 'Weapons', consumable: 'Consumables',
  wearable: 'Wearables', custom: 'Custom', character: 'Characters',
}
const KIND_GROUPS: Kind[] = ['character', 'race', 'class', 'weapon', 'wearable', 'consumable', 'custom']

export default function TemplatesStep({ data, onNext, onBack }: Props) {
  const [templates, setTemplates] = useState<DraftTemplate[]>(
    () => (data.draftTemplates.length > 0 ? data.draftTemplates : starterTemplates())
  )
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<DraftTemplate | null>(null)

  const referencedTempIds = new Set(data.draftInstances.map((i) => i.templateTempId).filter(Boolean))

  function openNew() {
    setEditing(null)
    setModalOpen(true)
  }

  function openEdit(t: DraftTemplate) {
    setEditing(t)
    setModalOpen(true)
  }

  function handleSave(draft: DraftTemplate) {
    setTemplates((prev) => {
      const exists = prev.some((t) => t.tempId === draft.tempId)
      return exists ? prev.map((t) => (t.tempId === draft.tempId ? draft : t)) : [...prev, draft]
    })
  }

  function handleRemove(tempId: string) {
    if (referencedTempIds.has(tempId)) return
    setTemplates((prev) => prev.filter((t) => t.tempId !== tempId))
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-zinc-400">
        Templates are the blueprints for races, classes, weapons, and other content in your world --
        starter races and classes are pre-filled below. Add, edit, or remove as you like.
      </p>

      <div className="flex flex-col gap-4 max-h-[50vh] overflow-y-auto pr-1">
        {KIND_GROUPS.map((kind) => {
          const group = templates.filter((t) => t.kind === kind)
          if (group.length === 0) return null
          return (
            <div key={kind} className="flex flex-col gap-2">
              <div className="text-xs uppercase tracking-wider text-zinc-500">{KIND_LABELS[kind]}</div>
              <div className="grid grid-cols-2 gap-2">
                {group.map((t) => (
                  <div
                    key={t.tempId}
                    className="bg-zinc-800/60 border border-zinc-700 rounded-xl px-3 py-2.5 flex items-center justify-between gap-2"
                  >
                    <button onClick={() => openEdit(t)} className="text-left flex-1 min-w-0">
                      <div className="text-sm font-semibold text-zinc-100 truncate">{t.name}</div>
                      <div className="text-xs text-zinc-500">{t.fields.length} field{t.fields.length === 1 ? '' : 's'}</div>
                    </button>
                    <button
                      onClick={() => handleRemove(t.tempId)}
                      disabled={referencedTempIds.has(t.tempId)}
                      title={referencedTempIds.has(t.tempId) ? 'An instance uses this template' : 'Remove'}
                      className="text-zinc-600 hover:text-red-400 disabled:opacity-30 disabled:hover:text-zinc-600 text-lg leading-none px-1 transition-colors duration-150 shrink-0"
                    >
                      &#x2715;
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>

      <button
        onClick={openNew}
        className="self-start px-3 py-1.5 text-xs font-semibold text-accent hover:text-accent-hover border border-zinc-700 hover:border-accent rounded-lg transition-colors duration-150"
      >
        + Add Template
      </button>

      <TemplateModal open={modalOpen} onClose={() => setModalOpen(false)} onSave={handleSave} initial={editing} />

      <div className="flex justify-between pt-2">
        <button onClick={onBack} className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150">
          Back
        </button>
        <button
          onClick={() => onNext({ draftTemplates: templates })}
          className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150"
        >
          Next
        </button>
      </div>
    </div>
  )
}
