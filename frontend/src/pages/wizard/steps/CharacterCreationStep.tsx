import { useState } from 'react'
import CharacterFieldsForm from '../../../components/character/creation/CharacterFieldsForm'
import { mergeFields } from '../../../types/blueprint'
import { nonCanonicalFields } from '../../../components/character/creation/types'
import type { WizardData } from '../wizardData'

interface Props {
  data: WizardData
  onNext: (patch: Partial<WizardData>) => void
  onBack: () => void
}

export default function CharacterCreationStep({ data, onNext, onBack }: Props) {
  const [name, setName] = useState(data.characterName)
  const [description, setDescription] = useState(data.characterDescription)
  const [tone, setTone] = useState(data.characterTone)
  const [raceTempId, setRaceTempId] = useState(data.raceTemplateTempId)
  const [classTempId, setClassTempId] = useState(data.classTemplateTempId)

  const characterTemplate = data.draftTemplates.find((t) => t.kind === 'character')
  const [customFields, setCustomFields] = useState(() =>
    data.characterCustomFields.length > 0
      ? data.characterCustomFields
      : nonCanonicalFields(characterTemplate ? mergeFields(characterTemplate.fields, []) : [])
  )

  const races = data.draftTemplates.filter((t) => t.kind === 'race')
  const classes = data.draftTemplates.filter((t) => t.kind === 'class')

  function handleNext() {
    if (!name.trim()) return
    onNext({
      characterName: name.trim(), characterDescription: description.trim(), characterTone: tone.trim(),
      raceTemplateTempId: raceTempId, classTemplateTempId: classTempId,
      characterCustomFields: customFields,
    })
  }

  return (
    <div className="flex flex-col gap-5">
      <CharacterFieldsForm
        name={name} onNameChange={setName}
        description={description} onDescriptionChange={setDescription}
        tone={tone} onToneChange={setTone}
        raceId={raceTempId} onRaceChange={setRaceTempId}
        classId={classTempId} onClassChange={setClassTempId}
        races={races.map((r) => ({ id: r.tempId, name: r.name }))}
        classes={classes.map((c) => ({ id: c.tempId, name: c.name }))}
        customFields={customFields} onCustomFieldsChange={setCustomFields}
        showCustomFields={Boolean(characterTemplate)}
      />
      <p className="text-xs text-zinc-600 -mt-3">
        Race and class are optional -- from the templates you set up earlier.
      </p>

      <div className="flex justify-between pt-2">
        <button
          onClick={onBack}
          className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150"
        >
          Back
        </button>
        <button
          onClick={handleNext}
          disabled={!name.trim()}
          className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150 disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  )
}
