interface ActionEntryProps {
  actorName: string
  actorColor: string
  narrative: string
  actionType: string
  outcome?: string
  speech?: string | null
  actionText?: string | null
}

function parseNarrative(text: string): { speech: string | null; action: string | null } {
  // Detect leading speech: `"..." rest`
  const speechMatch = text.match(/^"([^"]+)"(.*)/)
  if (speechMatch) {
    return {
      speech: speechMatch[1].trim(),
      action: speechMatch[2].trim() || null,
    }
  }
  return { speech: null, action: text || null }
}

export default function ActionEntry({
  actorName, actorColor, narrative, actionType, outcome, speech: explicitSpeech, actionText: explicitAction,
}: ActionEntryProps) {
  // Structured speech/action (from NPC dialogue records) takes precedence over the
  // regex-based guess, which stays as a fallback for player/DM records -- ActionRecord
  // always carries these as `null` (not `undefined`) when unset, so the check must be
  // "is either genuinely non-null," not just "was a prop passed."
  const hasStructured = explicitSpeech != null || explicitAction != null
  const { speech, action } = hasStructured
    ? { speech: explicitSpeech ?? null, action: explicitAction ?? null }
    : parseNarrative(narrative)
  const isEndTurn = actionType === 'end_turn'

  if (isEndTurn) {
    return (
      <div className="py-1 px-4">
        <span className="text-xs text-zinc-600 font-mono">
          — <span style={{ color: actorColor }} className="font-semibold">{actorName}</span> ends their turn
        </span>
      </div>
    )
  }

  return (
    <div className="py-2.5 px-4 flex flex-col gap-1">
      <span className="text-sm font-bold" style={{ color: actorColor }}>
        {actorName}
        {outcome && (
          <span className="ml-2 text-xs font-normal text-zinc-500 uppercase tracking-wider">
            {outcome}
          </span>
        )}
      </span>
      {speech && (
        <p className="text-sm text-zinc-300 leading-snug">
          &ldquo;{speech}&rdquo;
        </p>
      )}
      {action && (
        <p className="text-sm text-zinc-500 italic leading-snug">{action}</p>
      )}
    </div>
  )
}
