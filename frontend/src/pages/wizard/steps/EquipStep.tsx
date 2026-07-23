import { useState } from 'react'
import WearableEquipPicker from '../../../components/character/creation/WearableEquipPicker'
import InstanceModal from '../../../components/blueprint/InstanceModal'
import { resolveDraftInstance } from '../draftTypes'
import type { DraftInstance } from '../draftTypes'
import type { WizardData } from '../wizardData'

interface Props {
  data: WizardData
  onNext: (patch: Partial<WizardData>) => void
  onBack: () => void
}

export default function EquipStep({ data, onNext, onBack }: Props) {
  const [draftInstances, setDraftInstances] = useState<DraftInstance[]>(data.draftInstances)
  const [equippedIds, setEquippedIds] = useState<string[]>(data.equippedWearableTempIds)
  const [modalOpen, setModalOpen] = useState(false)

  const wearableTemplates = data.draftTemplates.filter((t) => t.kind === 'wearable')
  const candidates = draftInstances
    .filter((i) => i.kind === 'wearable' && !i.ownerTempId)
    .map((i) => resolveDraftInstance(i, data.draftTemplates))

  function handleNewInstance(draft: DraftInstance) {
    setDraftInstances((prev) => [...prev, draft])
  }

  return (
    <div className="flex flex-col gap-5">
      <p className="text-sm text-zinc-400">
        Equip gear from what's available in this adventure, or create something new on the spot.
      </p>

      <WearableEquipPicker
        candidates={candidates}
        equippedIds={equippedIds}
        onChange={setEquippedIds}
        onAddNew={() => setModalOpen(true)}
      />

      <InstanceModal
        open={modalOpen} onClose={() => setModalOpen(false)} onSave={handleNewInstance}
        templates={wearableTemplates} kind="wearable"
      />

      <div className="flex justify-between pt-2">
        <button onClick={onBack} className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150">
          Back
        </button>
        <button
          onClick={() => onNext({ draftInstances, equippedWearableTempIds: equippedIds })}
          className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150"
        >
          Next
        </button>
      </div>
    </div>
  )
}
