import type { WizardData, WizardStepId } from '../wizardData'

interface Props {
  data: WizardData
  onNext: (patch: Partial<WizardData>) => void
  onBack: () => void
  jumpTo: (step: WizardStepId) => void
}

function Section({ title, step, jumpTo, children }: {
  title: string; step: WizardStepId; jumpTo: (step: WizardStepId) => void; children: React.ReactNode
}) {
  return (
    <div className="bg-zinc-800/60 border border-zinc-700 rounded-xl px-4 py-3 flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wider text-zinc-500">{title}</span>
        <button
          onClick={() => jumpTo(step)}
          className="text-xs text-accent hover:text-accent-hover transition-colors duration-150"
        >
          Edit
        </button>
      </div>
      <div className="text-sm text-zinc-200">{children}</div>
    </div>
  )
}

export default function ReviewStep({ data, onNext, onBack, jumpTo }: Props) {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-zinc-400 mb-1">
        One last look before launch. Click "Edit" on any section to jump back and change it.
      </p>

      <Section title="Basics" step="basics" jumpTo={jumpTo}>
        <strong>{data.campaignName}</strong> -- {data.worldName}
      </Section>

      <Section title="World" step="worldgen" jumpTo={jumpTo}>
        {data.worldGenParams.width}x{data.worldGenParams.height} map,{' '}
        {data.biomeConfig.filter((f) => f.enabled).length} biome families,{' '}
        currency: {data.currencyName}
      </Section>

      <Section title="Content" step="templates" jumpTo={jumpTo}>
        {data.draftTemplates.length} template{data.draftTemplates.length === 1 ? '' : 's'},{' '}
        {data.draftInstances.length} instance{data.draftInstances.length === 1 ? '' : 's'}
      </Section>

      <Section title="Quest" step="quest" jumpTo={jumpTo}>
        {data.questEnabled ? `Opening quest (${data.questLength})` : 'No opening quest'}
      </Section>

      <Section title="Party" step="dmchoice" jumpTo={jumpTo}>
        {data.dmMode === 'human'
          ? "You'll be the DM"
          : `AI DM -- your character: ${data.characterName || '(unnamed)'}`}
      </Section>

      <Section title="Invite" step="invite" jumpTo={jumpTo}>
        Code: <span className="font-mono">{data.inviteCode}</span>
      </Section>

      <div className="flex justify-between pt-2">
        <button onClick={onBack} className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150">
          Back
        </button>
        <button
          onClick={() => onNext({})}
          className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150"
        >
          Launch Adventure
        </button>
      </div>
    </div>
  )
}
