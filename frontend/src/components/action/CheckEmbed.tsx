import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { MINIGAMES } from '../../minigames/registry'
import { tierLabelForRoll, TIER_COLORS } from '../../utils/diceScoring'
import { resolveCheck } from '../../api/narrator'
import type { PendingCheck } from '../../types/round'

interface CheckEmbedProps {
  check: PendingCheck
  isMine: boolean
}

interface RawResultShape {
  effective?: number
  rolls?: number[]
}

export default function CheckEmbed({ check, isMine }: CheckEmbedProps) {
  const [expanded, setExpanded] = useState(check.status === 'pending')
  const [submitting, setSubmitting] = useState(false)
  const queryClient = useQueryClient()

  async function handleComplete(rawResult: Record<string, unknown>) {
    setSubmitting(true)
    try {
      await resolveCheck(check.id, rawResult)
      await queryClient.invalidateQueries({ queryKey: ['round-checks', check.encounter_id, check.round_number] })
      await queryClient.invalidateQueries({ queryKey: ['round-status', check.encounter_id] })
    } finally {
      setSubmitting(false)
    }
  }

  if (check.status === 'resolved') {
    const raw = (check.raw_result ?? {}) as RawResultShape
    const effective = raw.effective ?? raw.rolls?.[0] ?? null
    const tier = check.minigame_id === 'dice-roll' && effective !== null && check.target !== null
      ? tierLabelForRoll(effective, check.target, check.die_size)
      : null
    const color = tier ? TIER_COLORS[tier] : '#9AA0A6'

    if (!expanded) {
      return (
        <button
          onClick={() => setExpanded(true)}
          className="mx-4 my-1 px-2 py-1 rounded-lg text-[10px] font-semibold self-start border transition-colors duration-150"
          style={{ color, borderColor: color + '60', backgroundColor: color + '15' }}
        >
          {check.character_name} — {check.skill_name}{tier ? `: ${tier}` : ''}
        </button>
      )
    }
    return (
      <div className="mx-4 my-1 p-2 rounded-lg border text-xs" style={{ borderColor: color + '60', backgroundColor: color + '15' }}>
        <div className="flex items-center justify-between gap-3">
          <span className="font-semibold" style={{ color }}>{check.character_name} — {check.skill_name}</span>
          <button onClick={() => setExpanded(false)} className="text-zinc-500 hover:text-zinc-300">
            &#x2715;
          </button>
        </div>
        {effective !== null && (
          <div className="mt-1 font-mono" style={{ color }}>
            Rolled {effective}{tier ? ` — ${tier}` : ''}
          </div>
        )}
      </div>
    )
  }

  const minigame = MINIGAMES[check.minigame_id]
  const Minigame = minigame?.component

  return (
    <div className="mx-4 my-1 p-2 rounded-lg border border-zinc-700 bg-zinc-800/60">
      {isMine && Minigame ? (
        <Minigame
          checkId={check.id}
          skillName={check.skill_name}
          dieSize={check.die_size}
          target={check.show_target ? check.target : null}
          advDisadv={check.adv_disadv}
          onComplete={handleComplete}
        />
      ) : (
        <div className="text-xs text-zinc-400 px-2 py-1">
          {check.character_name} is rolling {check.skill_name}…
        </div>
      )}
      {submitting && <div className="text-[10px] text-zinc-500 px-2">submitting…</div>}
    </div>
  )
}
