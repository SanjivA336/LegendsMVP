import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useGameStore } from '../store/gameStore'
import { useAdventure } from '../hooks/useAdventure'
import { useParty } from '../hooks/useCharacter'
import { useRelationships } from '../hooks/useContextCards'
import { useActionLog } from '../hooks/useCombat'
import { narratorAct } from '../api/narrator'
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
  const [dmThinking, setDmThinking] = useState(false)

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

  const adventureExists = adventures.some((a) => a.id === id)
  const openingNarrative = adventure?.openingNarrative ?? null

  const handleSendAction = useCallback(async (text: string) => {
    if (!id || !activeCharacterId || dmThinking) return

    setPendingPlayerText(text)
    setDmThinking(true)

    try {
      const result = await narratorAct({
        adventure_id: id,
        encounter_id: activeEncounterId ?? undefined,
        player_text: text,
        character_id: activeCharacterId,
      })

      // Save encounter ID so the action log fetches for this encounter
      if (!activeEncounterId || activeEncounterId !== result.encounter_id) {
        setNarrativeEncounter(id, result.encounter_id)
      }

      // Invalidate the action log so it refetches with both new entries
      await queryClient.invalidateQueries({ queryKey: ['action-log', result.encounter_id] })
    } catch (err) {
      console.error('Narrator act failed:', err)
    } finally {
      setPendingPlayerText(null)
      setDmThinking(false)
    }
  }, [id, activeCharacterId, activeEncounterId, dmThinking, setNarrativeEncounter, queryClient])

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
      stageCharacters={party}
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
          dmThinking={dmThinking}
        />
        <ActionInput
          onSendAction={handleSendAction}
          onOpenMap={() => setMapModalOpen(true)}
          disabled={dmThinking}
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
