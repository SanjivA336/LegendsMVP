import { useQuery } from '@tanstack/react-query'
import { listQuests } from '../../api/quests'
import type { Quest } from '../../types/quest'

interface QuestTrackerProps {
  adventureId: string | null
}

function getActiveStep(quest: Quest) {
  const all = [quest.first_step, ...quest.middle_steps, quest.last_step]
  return all.find((s) => s.status === 'active') ?? null
}

function StatusBadge({ status }: { status: Quest['status'] }) {
  const styles: Record<string, string> = {
    active: 'bg-accent/15 text-accent',
    completed: 'bg-green-900/40 text-green-400',
    failed: 'bg-red-900/40 text-red-400',
  }
  return (
    <span className={`text-[10px] uppercase tracking-wider font-semibold px-1.5 py-0.5 rounded ${styles[status]}`}>
      {status}
    </span>
  )
}

function QuestCard({ quest }: { quest: Quest }) {
  const activeStep = getActiveStep(quest)
  const totalSteps = 2 + quest.middle_steps.length
  const completedSteps = [quest.first_step, ...quest.middle_steps, quest.last_step].filter(
    (s) => s.status === 'completed'
  ).length

  return (
    <div className="px-3 py-3 border-b border-zinc-800 last:border-0">
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <span className="text-xs font-semibold text-zinc-200 leading-snug">{quest.title}</span>
        <StatusBadge status={quest.status} />
      </div>

      {/* Step progress bar */}
      <div className="flex gap-0.5 mb-2">
        {Array.from({ length: totalSteps }).map((_, i) => {
          const stepList = [quest.first_step, ...quest.middle_steps, quest.last_step]
          const s = stepList[i]
          const color =
            s?.status === 'completed'
              ? 'bg-green-500'
              : s?.status === 'active'
              ? 'bg-accent'
              : s?.status === 'failed'
              ? 'bg-red-500'
              : 'bg-zinc-700'
          return <div key={i} className={`h-1 flex-1 rounded-full ${color}`} />
        })}
      </div>

      <div className="text-[10px] text-zinc-500 mb-1">
        {completedSteps}/{totalSteps} steps
      </div>

      {activeStep && quest.status === 'active' && (
        <p className="text-xs text-zinc-400 leading-relaxed">{activeStep.description}</p>
      )}

      {quest.status === 'completed' && (
        <p className="text-xs text-green-500">Quest complete.</p>
      )}

      {quest.status === 'failed' && (
        <p className="text-xs text-red-400">Quest failed.</p>
      )}
    </div>
  )
}

export default function QuestTracker({ adventureId }: QuestTrackerProps) {
  const { data: quests = [], isLoading } = useQuery({
    queryKey: ['quests', adventureId],
    queryFn: () => listQuests(adventureId!),
    enabled: !!adventureId,
    refetchInterval: 15_000,
  })

  if (isLoading) {
    return (
      <div className="px-3 py-4 text-xs text-zinc-600 text-center">Loading quests...</div>
    )
  }

  if (quests.length === 0) {
    return (
      <div className="px-3 py-4 text-xs text-zinc-600 text-center">No quests yet.</div>
    )
  }

  const active = quests.filter((q) => q.status === 'active')
  const other = quests.filter((q) => q.status !== 'active')

  return (
    <div className="flex flex-col">
      {active.map((q) => <QuestCard key={q.id} quest={q} />)}
      {other.length > 0 && active.length > 0 && (
        <div className="text-[10px] uppercase tracking-wider text-zinc-600 px-3 pt-3 pb-0.5">
          Completed / Failed
        </div>
      )}
      {other.map((q) => <QuestCard key={q.id} quest={q} />)}
    </div>
  )
}
