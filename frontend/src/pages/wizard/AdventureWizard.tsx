import { useState } from 'react'
import {
  STEP_ORDER, STAGE_LABELS, STAGE_OF, nextStepId, prevStepId, makeInitialWizardData,
} from './wizardData'
import type { WizardStepId, WizardData } from './wizardData'
import BasicInfoStep from './steps/BasicInfoStep'
import WorldGenStep from './steps/WorldGenStep'
import WorldBibleStep from './steps/WorldBibleStep'
import TemplatesStep from './steps/TemplatesStep'
import InstancesStep from './steps/InstancesStep'
import QuestSetupStep from './steps/QuestSetupStep'
import DmChoiceStep from './steps/DmChoiceStep'
import CharacterCreationStep from './steps/CharacterCreationStep'
import StatRollStep from './steps/StatRollStep'
import EquipStep from './steps/EquipStep'
import InventoryStep from './steps/InventoryStep'
import CharacterSummaryStep from './steps/CharacterSummaryStep'
import InviteStep from './steps/InviteStep'
import ReviewStep from './steps/ReviewStep'
import LaunchStep from './steps/LaunchStep'

const STEP_TITLES: Record<WizardStepId, string> = {
  basics: 'Basic Info',
  worldgen: 'World Generation',
  worldbible: 'World Bible',
  templates: 'Templates',
  instances: 'Instances',
  quest: 'Opening Quest',
  dmchoice: 'Who Runs the Game?',
  character: 'Your Character',
  statroll: 'Assign Stats',
  equip: 'Equip Gear',
  inventory: 'Inventory',
  charactersummary: 'Character Summary',
  invite: 'Invite Players',
  review: 'Review',
  launch: 'Launch',
}

export default function AdventureWizard() {
  const [adventureId] = useState(() => crypto.randomUUID())
  const [currentStep, setCurrentStep] = useState<WizardStepId>('basics')
  const [returnTo, setReturnTo] = useState<WizardStepId | null>(null)
  const [wizardData, setWizardData] = useState<WizardData>(() => makeInitialWizardData(adventureId))

  function goNext(patch: Partial<WizardData> = {}) {
    setWizardData((prev) => {
      const merged = { ...prev, ...patch }
      if (returnTo) {
        setReturnTo(null)
        setCurrentStep(returnTo)
      } else {
        setCurrentStep(nextStepId(currentStep, merged.dmMode))
      }
      return merged
    })
  }

  function goBack() {
    if (returnTo) {
      setReturnTo(null)
      setCurrentStep(returnTo)
      return
    }
    setCurrentStep(prevStepId(currentStep, wizardData.dmMode))
  }

  function jumpTo(step: WizardStepId) {
    setReturnTo('review')
    setCurrentStep(step)
  }

  const stageIndex = STAGE_OF[currentStep]
  const stepIndex = STEP_ORDER.indexOf(currentStep)

  return (
    <div className="flex-1 flex items-start justify-center px-4 py-12">
      <div className="w-full max-w-3xl">
        {/* Stage tabs */}
        <div className="flex items-center gap-1 mb-6">
          {STAGE_LABELS.map((label, i) => (
            <div key={label} className="flex-1 flex flex-col items-center gap-1.5">
              <div
                className={`h-1 w-full rounded-full transition-colors duration-150 ${
                  i < stageIndex ? 'bg-accent' : i === stageIndex ? 'bg-accent' : 'bg-zinc-800'
                }`}
              />
              <span
                className={`text-[10px] uppercase tracking-wider transition-colors duration-150 ${
                  i === stageIndex ? 'text-accent font-semibold' : i < stageIndex ? 'text-zinc-400' : 'text-zinc-600'
                }`}
              >
                {label}
              </span>
            </div>
          ))}
        </div>

        {/* Step card */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg font-semibold tracking-tight text-zinc-100">
              {STEP_TITLES[currentStep]}
            </h2>
            <span className="text-xs text-zinc-600">
              Step {stepIndex + 1} of {STEP_ORDER.length}
            </span>
          </div>

          {currentStep === 'basics' && (
            <BasicInfoStep data={wizardData} onNext={goNext} />
          )}
          {currentStep === 'worldgen' && (
            <WorldGenStep data={wizardData} onNext={goNext} onBack={goBack} />
          )}
          {currentStep === 'worldbible' && (
            <WorldBibleStep data={wizardData} onNext={goNext} onBack={goBack} />
          )}
          {currentStep === 'templates' && (
            <TemplatesStep data={wizardData} onNext={goNext} onBack={goBack} />
          )}
          {currentStep === 'instances' && (
            <InstancesStep data={wizardData} onNext={goNext} onBack={goBack} />
          )}
          {currentStep === 'quest' && (
            <QuestSetupStep data={wizardData} onNext={goNext} onBack={goBack} />
          )}
          {currentStep === 'dmchoice' && (
            <DmChoiceStep data={wizardData} onNext={goNext} onBack={goBack} />
          )}
          {currentStep === 'character' && (
            <CharacterCreationStep data={wizardData} onNext={goNext} onBack={goBack} />
          )}
          {currentStep === 'statroll' && (
            <StatRollStep data={wizardData} onNext={goNext} onBack={goBack} />
          )}
          {currentStep === 'equip' && (
            <EquipStep data={wizardData} onNext={goNext} onBack={goBack} />
          )}
          {currentStep === 'inventory' && (
            <InventoryStep data={wizardData} onNext={goNext} onBack={goBack} />
          )}
          {currentStep === 'charactersummary' && (
            <CharacterSummaryStep data={wizardData} onNext={goNext} onBack={goBack} />
          )}
          {currentStep === 'invite' && (
            <InviteStep data={wizardData} onNext={goNext} onBack={goBack} />
          )}
          {currentStep === 'review' && (
            <ReviewStep data={wizardData} onNext={goNext} onBack={goBack} jumpTo={jumpTo} />
          )}
          {currentStep === 'launch' && (
            <LaunchStep data={wizardData} adventureId={adventureId} onBack={goBack} />
          )}
        </div>
      </div>
    </div>
  )
}
