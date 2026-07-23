import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useGameStore } from '../store/gameStore'
import { useAdventure } from '../hooks/useAdventure'
import { useParty } from '../hooks/useCharacter'
import { useRelationships } from '../hooks/useContextCards'
import { useActionLog, useEncounter } from '../hooks/useCombat'
import { useRoundStatus, usePendingChecks } from '../hooks/useNarrator'
import { submitRoundAction, forceResolveRound } from '../api/narrator'
import { playerTurn } from '../api/combat'
import GameLayout from '../components/layout/GameLayout'
import ActionLog from '../components/action/ActionLog'
import ActionInput from '../components/action/ActionInput'
import StageBar from '../components/encounter/StageBar'
import WorldMapModal from '../components/world/WorldMapModal'
import ArenaPanel from '../components/combat/ArenaPanel'

export default function GamePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [mapModalOpen, setMapModalOpen] = useState(false)
  const [pendingPlayerText, setPendingPlayerText] = useState<string | null>(null)
  const [pendingPassed, setPendingPassed] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const lastConsumedRound = useRef(0)

  const setActiveAdventure = useGameStore((s) => s.setActiveAdventure)
  const activeCharacterId = useGameStore((s) => s.activeCharacterId)
  const activeEncounterId = useGameStore((s) => s.activeEncounterId)
  const combatActive = useGameStore((s) => s.combatActive)
  const adventures = useGameStore((s) => s.adventures)
  const setNarrativeEncounter = useGameStore((s) => s.setNarrativeEncounter)

  useEffect(() => {
    if (id) setActiveAdventure(id)
  }, [id, setActiveAdventure])

  const adventure = useAdventure()
  const { data: party = [], isLoading: partyLoading } = useParty(id ?? null)
  const { data: relationships = [] } = useRelationships(id ?? null)
  const { data: actions = [], isLoading: actionsLoading } = useActionLog(activeEncounterId)
  const { data: roundStatus } = useRoundStatus(activeEncounterId)
  const { data: pendingChecks = [] } = usePendingChecks(activeEncounterId, roundStatus?.round_number ?? 0)
  const { data: encounter } = useEncounter(activeEncounterId)

  // Scope the stage bar to who's actually present, falling back to the whole roster
  // until the first round populates stage_ids (see backend Part B).
  const stagedParty = encounter?.stage_ids?.length
    ? party.filter((c) => encounter.stage_ids.includes(c.id))
    : party

  const adventureExists = adventures.some((a) => a.id === id)
  const openingNarrative = adventure?.openingNarrative ?? null

  // Cross-client sync: when polling reveals a round resolved (by us or anyone else), refetch the log
  useEffect(() => {
    if (!roundStatus || !id) return
    if (roundStatus.status === 'resolved' && roundStatus.round_number > lastConsumedRound.current) {
      lastConsumedRound.current = roundStatus.round_number
      queryClient.invalidateQueries({ queryKey: ['action-log', activeEncounterId] })
      queryClient.invalidateQueries({ queryKey: ['arena', activeEncounterId] })
      setPendingPlayerText(null)
      setPendingPassed(false)
    }
  }, [roundStatus, id, activeEncounterId, queryClient])

  // A resolved/idle round has no bearing on the NEXT round (which only gets created
  // lazily on the next submission) -- only an in-progress round can mean "you've already acted."
  const roundInProgress = roundStatus?.status === 'collecting' || roundStatus?.status === 'awaiting_checks'
  const myEntry = roundStatus?.entries.find((e) => e.character_id === activeCharacterId)
  const iHaveActed = roundInProgress && myEntry ? myEntry.status !== 'awaiting' : false
  const isResolving = roundStatus?.status === 'resolving'
  const othersWaiting = roundStatus?.entries.filter(
    (e) => e.character_id !== activeCharacterId && e.status === 'awaiting'
  ) ?? []
  const canForceResolve = adventure?.role === 'owner' || adventure?.role === 'admin'

  const handleSendAction = useCallback(async (text: string) => {
    if (!id || !activeCharacterId || submitting || iHaveActed) return

    setPendingPlayerText(text)
    setPendingPassed(false)
    setSubmitting(true)

    try {
      const result = await submitRoundAction({
        adventure_id: id,
        encounter_id: activeEncounterId ?? undefined,
        character_id: activeCharacterId,
        player_text: text,
      })

      if (!activeEncounterId || activeEncounterId !== result.encounter_id) {
        setNarrativeEncounter(id, result.encounter_id)
      }

      // round-status polling backs off when idle/resolved -- refresh it ourselves
      // right away so submitting doesn't feel delayed by that backoff.
      queryClient.invalidateQueries({ queryKey: ['round-status', result.encounter_id] })

      if (result.resolved) {
        lastConsumedRound.current = result.round_number
        await queryClient.invalidateQueries({ queryKey: ['action-log', result.encounter_id] })
        setPendingPlayerText(null)
      }
    } catch (err) {
      console.error('Round submit failed:', err)
      setPendingPlayerText(null)
    } finally {
      setSubmitting(false)
    }
  }, [id, activeCharacterId, activeEncounterId, submitting, iHaveActed, setNarrativeEncounter, queryClient])

  const handlePass = useCallback(async () => {
    if (!id || !activeCharacterId || submitting || iHaveActed) return

    setPendingPassed(true)
    setPendingPlayerText(null)
    setSubmitting(true)

    try {
      const result = await submitRoundAction({
        adventure_id: id,
        encounter_id: activeEncounterId ?? undefined,
        character_id: activeCharacterId,
        passed: true,
      })

      if (!activeEncounterId || activeEncounterId !== result.encounter_id) {
        setNarrativeEncounter(id, result.encounter_id)
      }

      queryClient.invalidateQueries({ queryKey: ['round-status', result.encounter_id] })

      if (result.resolved) {
        lastConsumedRound.current = result.round_number
        await queryClient.invalidateQueries({ queryKey: ['action-log', result.encounter_id] })
        setPendingPassed(false)
      }
    } catch (err) {
      console.error('Pass failed:', err)
      setPendingPassed(false)
    } finally {
      setSubmitting(false)
    }
  }, [id, activeCharacterId, activeEncounterId, submitting, iHaveActed, setNarrativeEncounter, queryClient])

  const handleEndTurn = useCallback(async () => {
    if (!activeEncounterId || !activeCharacterId) return
    try {
      await playerTurn(activeEncounterId, { actor_id: activeCharacterId, action_type: 'end_turn' })
      await queryClient.invalidateQueries({ queryKey: ['arena', activeEncounterId] })
      await queryClient.invalidateQueries({ queryKey: ['action-log', activeEncounterId] })
    } catch (err) {
      console.error('End turn failed:', err)
    }
  }, [activeEncounterId, activeCharacterId, queryClient])

  const handleForceResolve = useCallback(async () => {
    if (!activeEncounterId) return
    try {
      const result = await forceResolveRound(activeEncounterId)
      lastConsumedRound.current = result.round_number
      queryClient.invalidateQueries({ queryKey: ['round-status', activeEncounterId] })
      await queryClient.invalidateQueries({ queryKey: ['action-log', activeEncounterId] })
      setPendingPlayerText(null)
      setPendingPassed(false)
    } catch (err) {
      console.error('Force resolve failed:', err)
    }
  }, [activeEncounterId, queryClient])

  if (!adventureExists && !partyLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4 text-zinc-400">
        <p>Adventure not found in this browser.</p>
        <button
          onClick={() => navigate('/adventures')}
          className="text-sm text-accent hover:text-accent-hover transition-colors duration-150"
        >
          Back to Adventures
        </button>
      </div>
    )
  }

  const stageBar = (
    <StageBar
      stageCharacters={stagedParty}
      relationships={relationships}
      playerCharacterId={activeCharacterId}
    />
  )

  const center = (
    <div className="flex flex-col h-full overflow-hidden">
      {combatActive && <ArenaPanel encounterId={activeEncounterId} />}

      {/* Opening scene narrator card — permanent first entry */}
      {openingNarrative && (
        <div className="mx-3 mt-3 p-4 bg-zinc-800/60 border border-zinc-700 rounded-2xl flex flex-col gap-2 shrink-0">
          <div className="text-[10px] uppercase tracking-widest text-zinc-500 font-semibold">
            Dungeon Master
          </div>
          <p className="text-sm text-zinc-200 leading-relaxed">{openingNarrative}</p>
        </div>
      )}

      <div className="flex-1 overflow-hidden flex flex-col">
        <ActionLog
          actions={actions}
          characters={party}
          playerCharacterId={activeCharacterId}
          isLoading={actionsLoading}
          pendingPlayerText={pendingPlayerText}
          pendingPassed={pendingPassed}
          dmThinking={isResolving}
          pendingChecks={pendingChecks}
        />
        {othersWaiting.length > 0 && (
          <div className="px-4 py-2 text-xs text-zinc-500 border-t border-zinc-800/50 flex items-center gap-2 flex-wrap shrink-0">
            <span>Waiting for:</span>
            {othersWaiting.map((e) => (
              <span key={e.character_id} className="text-zinc-400">
                {e.character_name}{e.kind === 'actor' ? ' (Actor)' : ''}
              </span>
            ))}
            {canForceResolve && (
              <button
                onClick={handleForceResolve}
                className="ml-auto text-zinc-500 hover:text-red-400 transition-colors duration-150"
              >
                Force Resolve Round
              </button>
            )}
          </div>
        )}
        <ActionInput
          onSendAction={handleSendAction}
          onPass={handlePass}
          onEndTurn={handleEndTurn}
          onOpenMap={() => setMapModalOpen(true)}
          disabled={submitting || iHaveActed || isResolving}
        />
      </div>
      <WorldMapModal open={mapModalOpen} onClose={() => setMapModalOpen(false)} />
    </div>
  )

  return (
    <div className="flex flex-col h-screen">
      {/* Adventure nav bar */}
      <div className="h-10 border-b border-zinc-800 bg-zinc-950 flex items-center px-4 gap-3 shrink-0">
        <button
          onClick={() => navigate('/adventures')}
          className="text-zinc-500 hover:text-zinc-100 text-sm transition-colors duration-150"
        >
          &#x276E;
        </button>
        <span className="text-sm font-semibold text-zinc-200 truncate">
          {adventure?.name ?? 'Adventure'}
        </span>
        {adventure?.worldName && (
          <span className="text-xs text-zinc-500 truncate">{adventure.worldName}</span>
        )}
      </div>

      <div className="flex-1 overflow-hidden">
        <GameLayout center={center} stageBar={stageBar} />
      </div>
    </div>
  )
}
