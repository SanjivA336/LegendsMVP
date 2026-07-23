import CharacterSummary from '../../../components/character/creation/CharacterSummary'
import { resolveDraftInstance } from '../draftTypes'
import type { WizardData } from '../wizardData'

interface Props {
  data: WizardData
  onNext: (patch: Partial<WizardData>) => void
  onBack: () => void
}

export default function CharacterSummaryStep({ data, onNext, onBack }: Props) {
  const race = data.draftTemplates.find((t) => t.tempId === data.raceTemplateTempId)
  const cls = data.draftTemplates.find((t) => t.tempId === data.classTemplateTempId)

  const equippedItems = data.equippedWearableTempIds
    .map((id) => data.draftInstances.find((i) => i.tempId === id))
    .filter((i) => i !== undefined)
    .map((i) => resolveDraftInstance(i, data.draftTemplates))

  const inventoryItems = Array.from(new Set([...data.inventoryTempIds, ...data.equippedWearableTempIds]))
    .map((id) => data.draftInstances.find((i) => i.tempId === id))
    .filter((i) => i !== undefined)
    .map((i) => resolveDraftInstance(i, data.draftTemplates))

  return (
    <div className="flex flex-col gap-5">
      <CharacterSummary
        name={data.characterName}
        description={data.characterDescription}
        tone={data.characterTone}
        raceName={race?.name ?? null}
        className={cls?.name ?? null}
        stats={data.statAssignments}
        attributeNames={data.attributeNames}
        customFields={data.characterCustomFields}
        equippedItems={equippedItems}
        inventoryItems={inventoryItems}
      />

      <div className="flex justify-between pt-2">
        <button onClick={onBack} className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150">
          Back
        </button>
        <button
          onClick={() => onNext({})}
          className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150"
        >
          Next
        </button>
      </div>
    </div>
  )
}
