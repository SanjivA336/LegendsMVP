import { useState } from 'react'
import InstanceModal from '../../../components/blueprint/InstanceModal'
import { getFieldValue } from '../../../types/blueprint'
import type { Kind } from '../../../types/blueprint'
import type { DraftInstance } from '../draftTypes'
import type { WizardData } from '../wizardData'

interface Props {
  data: WizardData
  onNext: (patch: Partial<WizardData>) => void
  onBack: () => void
}

const KIND_LABELS: Record<Kind, string> = {
  race: 'Races', class: 'Classes', weapon: 'Weapons', consumable: 'Consumables',
  wearable: 'Wearables', custom: 'Custom', character: 'Characters',
}
const KIND_TABS: Kind[] = ['race', 'class', 'weapon', 'wearable', 'consumable', 'custom']

function instanceLabel(instance: DraftInstance, templateName: string): string {
  const name = getFieldValue(instance.fields, 'name')
  return typeof name === 'string' && name ? name : templateName || '(unnamed)'
}

export default function InstancesStep({ data, onNext, onBack }: Props) {
  const availableTabs = KIND_TABS.filter((k) => data.draftTemplates.some((t) => t.kind === k))
  const [activeTab, setActiveTab] = useState<Kind>(availableTabs[0] ?? 'custom')
  const [instances, setInstances] = useState<DraftInstance[]>(data.draftInstances)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<DraftInstance | null>(null)

  const templatesForTab = data.draftTemplates.filter((t) => t.kind === activeTab)
  const instancesForTab = instances.filter((i) => i.kind === activeTab)

  function openNew() {
    setEditing(null)
    setModalOpen(true)
  }

  function openEdit(instance: DraftInstance) {
    setEditing(instance)
    setModalOpen(true)
  }

  function handleSave(draft: DraftInstance) {
    setInstances((prev) => {
      const exists = prev.some((i) => i.tempId === draft.tempId)
      return exists ? prev.map((i) => (i.tempId === draft.tempId ? draft : i)) : [...prev, draft]
    })
  }

  function handleRemove(tempId: string) {
    setInstances((prev) => prev.filter((i) => i.tempId !== tempId))
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-zinc-400">
        Create specific instances of your templates -- an actual sword, a particular NPC faction
        member. Optional: skip this step if your templates are enough on their own.
      </p>

      {availableTabs.length === 0 ? (
        <p className="text-xs text-zinc-600">Add a template in the previous step first.</p>
      ) : (
        <>
          <div className="flex gap-1.5 flex-wrap">
            {availableTabs.map((kind) => (
              <button
                key={kind}
                onClick={() => setActiveTab(kind)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors duration-150 ${
                  activeTab === kind ? 'bg-zinc-700 text-zinc-100' : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                {KIND_LABELS[kind]}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-2 max-h-[40vh] overflow-y-auto pr-1">
            {instancesForTab.length === 0 && (
              <p className="text-xs text-zinc-600 col-span-2">No {KIND_LABELS[activeTab].toLowerCase()} instances yet.</p>
            )}
            {instancesForTab.map((instance) => {
              const template = data.draftTemplates.find((t) => t.tempId === instance.templateTempId)
              return (
                <div
                  key={instance.tempId}
                  className="bg-zinc-800/60 border border-zinc-700 rounded-xl px-3 py-2.5 flex items-center justify-between gap-2"
                >
                  <button onClick={() => openEdit(instance)} className="text-left flex-1 min-w-0">
                    <div className="text-sm font-semibold text-zinc-100 truncate">
                      {instanceLabel(instance, template?.name ?? '')}
                    </div>
                    {template && <div className="text-xs text-zinc-500 truncate">from {template.name}</div>}
                  </button>
                  <button
                    onClick={() => handleRemove(instance.tempId)}
                    className="text-zinc-600 hover:text-red-400 text-lg leading-none px-1 transition-colors duration-150 shrink-0"
                  >
                    &#x2715;
                  </button>
                </div>
              )
            })}
          </div>

          <button
            onClick={openNew}
            className="self-start px-3 py-1.5 text-xs font-semibold text-accent hover:text-accent-hover border border-zinc-700 hover:border-accent rounded-lg transition-colors duration-150"
          >
            + Add {KIND_LABELS[activeTab].replace(/s$/, '')}
          </button>

          <InstanceModal
            open={modalOpen} onClose={() => setModalOpen(false)} onSave={handleSave}
            initial={editing} templates={templatesForTab} kind={activeTab}
          />
        </>
      )}

      <div className="flex justify-between pt-2">
        <button onClick={onBack} className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150">
          Back
        </button>
        <button
          onClick={() => onNext({ draftInstances: instances })}
          className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150"
        >
          Next
        </button>
      </div>
    </div>
  )
}
