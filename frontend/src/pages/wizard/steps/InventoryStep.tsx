import { useState } from 'react'
import InventoryPicker from '../../../components/character/creation/InventoryPicker'
import InstanceModal from '../../../components/blueprint/InstanceModal'
import { resolveDraftInstance } from '../draftTypes'
import type { DraftInstance } from '../draftTypes'
import type { Kind } from '../../../types/blueprint'
import type { WizardData } from '../wizardData'

interface Props {
  data: WizardData
  onNext: (patch: Partial<WizardData>) => void
  onBack: () => void
}

const ADDABLE_KINDS: { value: Kind; label: string }[] = [
  { value: 'weapon', label: 'Weapon' },
  { value: 'wearable', label: 'Wearable' },
  { value: 'consumable', label: 'Consumable' },
  { value: 'custom', label: 'Custom' },
]
const INVENTORY_KINDS: Kind[] = ADDABLE_KINDS.map((k) => k.value)

export default function InventoryStep({ data, onNext, onBack }: Props) {
  const [draftInstances, setDraftInstances] = useState<DraftInstance[]>(data.draftInstances)
  const [selectedIds, setSelectedIds] = useState<string[]>(data.inventoryTempIds)
  const [addingKind, setAddingKind] = useState<Kind | null>(null)

  const candidates = draftInstances
    .filter((i) => INVENTORY_KINDS.includes(i.kind) && !i.ownerTempId)
    .map((i) => resolveDraftInstance(i, data.draftTemplates))

  function handleNewInstance(draft: DraftInstance) {
    setDraftInstances((prev) => [...prev, draft])
  }

  return (
    <div className="flex flex-col gap-5">
      <p className="text-sm text-zinc-400">
        Pick up anything from the adventure to start with, or create something new. Optional --
        skip if you'd rather start empty-handed.
      </p>

      <InventoryPicker candidates={candidates} selectedIds={selectedIds} onChange={setSelectedIds} />

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

      {addingKind && (
        <InstanceModal
          open={Boolean(addingKind)} onClose={() => setAddingKind(null)} onSave={handleNewInstance}
          templates={data.draftTemplates.filter((t) => t.kind === addingKind)} kind={addingKind}
        />
      )}

      <div className="flex justify-between pt-2">
        <button onClick={onBack} className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150">
          Back
        </button>
        <button
          onClick={() => onNext({ draftInstances, inventoryTempIds: selectedIds })}
          className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150"
        >
          Next
        </button>
      </div>
    </div>
  )
}
