import { useEffect, useRef } from 'react'
import ActionEntry from './ActionEntry'
import CheckEmbed from './CheckEmbed'
import type { ActionRecord } from '../../types/combat'
import type { Character } from '../../types/character'
import type { PendingCheck } from '../../types/round'
import { NPC_HOSTILE, NPC_NEUTRAL, NARRATOR_COLOR } from '../../constants/colors'
import { usePlayerColors } from '../../hooks/usePlayerColors'

interface ActionLogProps {
  actions: ActionRecord[]
  characters: Character[]
  playerCharacterId: string | null
  isLoading?: boolean
  pendingPlayerText?: string | null
  pendingPassed?: boolean
  dmThinking?: boolean
  pendingChecks?: PendingCheck[]
}

function resolveActorColor(
  actorId: string,
  displayName: string | null,
  characters: Character[],
  playerCharacterId: string | null,
  playerColors: string[]
): { name: string; color: string } {
  if (actorId === 'narrator') return { name: 'Narrator', color: NARRATOR_COLOR }

  // Ephemeral NPC (no persistent Character record) -- speaks/acts via a display_name
  // carried directly on the ActionRecord instead of a party lookup.
  if (actorId.startsWith('npc:')) return { name: displayName ?? 'Someone', color: NPC_NEUTRAL }

  const char = characters.find((c) => c.id === actorId)
  if (!char) return { name: displayName ?? actorId, color: NARRATOR_COLOR }

  if (char.is_player) {
    const players = characters.filter((c) => c.is_player)
    const idx = players.indexOf(char)
    const color = idx === 0 && char.id === playerCharacterId
      ? playerColors[0]
      : playerColors[idx % playerColors.length]
    return { name: char.name, color }
  }

  return { name: char.name, color: NPC_HOSTILE }
}

function DmThinkingBubble() {
  return (
    <div className="px-4 py-3 flex items-start gap-2">
      <div className="flex flex-col gap-1 min-w-0">
        <span className="text-xs font-semibold" style={{ color: NARRATOR_COLOR }}>
          Narrator
        </span>
        <div className="flex items-center gap-1 mt-0.5">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-zinc-400"
              style={{
                animation: 'bounce 1.2s ease-in-out infinite',
                animationDelay: `${i * 0.2}s`,
              }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

export default function ActionLog({
  actions,
  characters,
  playerCharacterId,
  isLoading,
  pendingPlayerText,
  pendingPassed,
  dmThinking,
  pendingChecks = [],
}: ActionLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const prevCount = useRef(0)
  const playerColors = usePlayerColors()

  const hasPending = !!pendingPlayerText || !!pendingPassed
  const totalEntries = actions.length + (hasPending ? 1 : 0) + (dmThinking ? 1 : 0) + pendingChecks.length
  useEffect(() => {
    if (totalEntries > prevCount.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
    prevCount.current = totalEntries
  }, [totalEntries])

  const hasContent = actions.length > 0 || hasPending || dmThinking || pendingChecks.length > 0

  return (
    <>
      {/* Keyframe for the dot bounce animation */}
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
          40%            { transform: translateY(-4px); opacity: 1; }
        }
      `}</style>

      <div className="flex-1 overflow-y-auto flex flex-col divide-y divide-zinc-800/50">
        {isLoading && (
          <div className="px-4 py-3 text-sm text-zinc-500">Loading...</div>
        )}
        {!isLoading && !hasContent && (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-sm text-zinc-600">The story has not yet begun.</p>
          </div>
        )}
        {actions.map((action) => {
          const { name, color } = resolveActorColor(
            action.actor_id, action.display_name, characters, playerCharacterId, playerColors
          )
          return (
            <ActionEntry
              key={action.id}
              actorName={name}
              actorColor={color}
              narrative={action.narrative}
              actionType={action.action_type}
              outcome={action.outcome}
              speech={action.speech}
              actionText={action.action_text}
            />
          )
        })}

        {/* Pending player message — shown immediately on submit or pass */}
        {hasPending && (() => {
          const playerChar = playerCharacterId
            ? characters.find((c) => c.id === playerCharacterId)
            : null
          const players = characters.filter((c) => c.is_player)
          const idx = playerChar ? players.indexOf(playerChar) : 0
          const color = playerColors[idx % playerColors.length]
          const name = playerChar?.name ?? 'You'
          return (
            <ActionEntry
              actorName={name}
              actorColor={color}
              narrative={pendingPassed ? '(passed)' : pendingPlayerText ?? ''}
              actionType="narrative"
              outcome=""
            />
          )
        })()}

        {/* Pending skill checks — visible to everyone, interactive only for your own */}
        {pendingChecks.map((check) => (
          <CheckEmbed key={check.id} check={check} isMine={check.character_id === playerCharacterId} />
        ))}

        {/* DM thinking animation */}
        {dmThinking && <DmThinkingBubble />}

        <div ref={bottomRef} />
      </div>
    </>
  )
}
