interface ActionEntryProps {
  actorName: string
  actorColor: string
  narrative: string
  actionType: string
  outcome?: string
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

export default function ActionEntry({ actorName, actorColor, narrative, actionType, outcome }: ActionEntryProps) {
  const { speech, action } = parseNarrative(narrative)
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
