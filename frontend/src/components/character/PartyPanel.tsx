import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import ColorAvatar from '../ui/ColorAvatar'
import HPBar from '../ui/HPBar'
import CharacterDossier from './CharacterDossier'
import PartySlotModal from './PartySlotModal'
import type { Character } from '../../types/character'
import { useAdventure } from '../../hooks/useAdventure'
import { usePlayerColors } from '../../hooks/usePlayerColors'
import { fetchActorSlots, type Actor, type ActorSlot, fetchActors } from '../../api/actors'

const MAX_PARTY = 4

interface PartyPanelProps {
  characters: Character[]
}

// ── Role icons ──────────────────────────────────────────────────────────────

function CrownIcon() {
  return (
    <span className="shrink-0" title="Owner — full control, delete adventure, promote to admin, all gameplay">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor" className="text-amber-400">
        <path d="M5 16L3 5l5.5 5L12 4l3.5 6L21 5l-2 11H5zm0 2h14v2H5v-2z" />
      </svg>
    </span>
  )
}

function ShieldIcon() {
  return (
    <span className="shrink-0" title="Admin — edit adventure details, add/remove players, all gameplay">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor" className="text-sky-400">
        <path d="M12 2L4 6v6c0 5.25 3.5 10.15 8 11.45C16.5 22.15 20 17.25 20 12V6l-8-4z" />
      </svg>
    </span>
  )
}

function PersonIcon() {
  return (
    <span className="shrink-0" title="Player — gameplay actions">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor" className="text-zinc-400">
        <circle cx="12" cy="7" r="4" />
        <path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8" />
      </svg>
    </span>
  )
}

function BinocularsIcon() {
  return (
    <span className="shrink-0" title="Viewer — view only, no gameplay actions">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-zinc-600">
        <path d="M9 5H5a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h4M15 5h4a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-4M9 5a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H9z" />
      </svg>
    </span>
  )
}

function RobotIcon({ title }: { title: string }) {
  return (
    <span className="shrink-0" title={title}>
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-violet-400">
        <rect x="3" y="11" width="18" height="10" rx="2" />
        <path d="M12 11V7M8 7h8M10 15h.01M14 15h.01" />
        <circle cx="12" cy="4" r="1" />
      </svg>
    </span>
  )
}

// ── Role icon selector ──────────────────────────────────────────────────────

function RoleIcon({ role }: { role: 'owner' | 'admin' | 'player' | 'viewer' }) {
  if (role === 'owner') return <CrownIcon />
  if (role === 'admin') return <ShieldIcon />
  if (role === 'player') return <PersonIcon />
  return <BinocularsIcon />
}

// ── Axis labels ─────────────────────────────────────────────────────────────

const STANCE_LABELS = ['', 'Pacifist', 'Defensive', 'Balanced', 'Aggressive', 'Berserker']
const TACTICS_LABELS = ['', 'Calculated', 'Methodical', 'Adaptive', 'Bold', 'Reckless']
const DISPOSITION_LABELS = ['', 'Noble', 'Principled', 'Pragmatic', 'Cunning', 'Ruthless']

function actorTooltip(actor: Actor, name: string): string {
  const s = STANCE_LABELS[actor.stance] ?? 'Balanced'
  const t = TACTICS_LABELS[actor.tactics] ?? 'Adaptive'
  const d = DISPOSITION_LABELS[actor.disposition] ?? 'Pragmatic'
  return `${name} (Actor) — ${s} · ${t} · ${d}`
}

// ── Main component ──────────────────────────────────────────────────────────

export default function PartyPanel({ characters }: PartyPanelProps) {
  const [selectedChar, setSelectedChar] = useState<Character | null>(null)
  const [dossierOpen, setDossierOpen] = useState(false)
  const [slotModalOpen, setSlotModalOpen] = useState(false)

  const adventure = useAdventure()
  const adventureId = adventure?.id ?? null
  const playerColors = usePlayerColors()

  const { data: actorSlots = [] } = useQuery<ActorSlot[]>({
    queryKey: ['actor-slots', adventureId],
    queryFn: () => fetchActorSlots(adventureId!),
    enabled: !!adventureId,
  })

  const { data: allActors = [] } = useQuery<Actor[]>({
    queryKey: ['actors'],
    queryFn: fetchActors,
    enabled: !!adventureId,
  })

  const actorMap = Object.fromEntries(allActors.map((a) => [a.id, a]))
  const charMap = Object.fromEntries(characters.map((c) => [c.id, c]))

  const players = characters.filter((c) => c.is_player)

  function slotColor(index: number): string {
    return playerColors[index % playerColors.length]
  }

  function openDossier(char: Character) {
    setSelectedChar(char)
    setDossierOpen(true)
  }

  // Build the 4 slots in order: human players first, then actor slots, then empty
  const totalSlots = MAX_PARTY
  const usedCount = players.length + actorSlots.length

  return (
    <div className="flex flex-col gap-1 px-3 py-2">
      {/* Human player slots */}
      {players.map((char, i) => {
        const color = slotColor(i)
        return (
          <button
            key={char.id}
            onClick={() => openDossier(char)}
            className="flex items-center gap-2.5 px-2 py-2 rounded-xl hover:bg-zinc-800 transition-colors duration-150 text-left w-full"
          >
            <ColorAvatar name={char.name} color={color} size="sm" ringColor={color} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                {adventure?.role && <RoleIcon role={adventure.role} />}
                <span className="text-xs font-semibold text-zinc-200 truncate">{char.name}</span>
              </div>
              <HPBar hp={char.hp} maxHp={char.max_hp} className="mt-1" />
              <div className="text-[10px] text-zinc-500 font-mono mt-0.5">
                {char.hp}/{char.max_hp}
              </div>
            </div>
          </button>
        )
      })}

      {/* Actor slots */}
      {actorSlots.map((slot, i) => {
        const actor = actorMap[slot.actor_id]
        const char = slot.character_id ? charMap[slot.character_id] : null
        const slotIndex = players.length + i
        const color = slotColor(slotIndex)
        const displayName = char?.name ?? actor?.name ?? 'Actor'
        const tooltip = actor ? actorTooltip(actor, displayName) : 'Actor'

        return (
          <button
            key={slot.id}
            onClick={() => char && openDossier(char)}
            className="flex items-center gap-2.5 px-2 py-2 rounded-xl hover:bg-zinc-800 transition-colors duration-150 text-left w-full"
          >
            <ColorAvatar name={displayName} color={color} size="sm" ringColor={color} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <RobotIcon title={tooltip} />
                <span className="text-xs font-semibold text-zinc-200 truncate">{displayName}</span>
              </div>
              {char && (
                <>
                  <HPBar hp={char.hp} maxHp={char.max_hp} className="mt-1" />
                  <div className="text-[10px] text-zinc-500 font-mono mt-0.5">
                    {char.hp}/{char.max_hp}
                  </div>
                </>
              )}
            </div>
          </button>
        )
      })}

      {/* Empty slots */}
      {Array.from({ length: Math.max(0, totalSlots - usedCount) }).map((_, i) => (
        <button
          key={`empty-${i}`}
          onClick={() => setSlotModalOpen(true)}
          className="flex items-center gap-2.5 px-2 py-2 rounded-xl border border-dashed border-zinc-700 hover:border-zinc-500 transition-colors duration-150 w-full text-zinc-600 hover:text-zinc-400"
        >
          <div className="w-7 h-7 rounded-full border border-dashed border-zinc-700 flex items-center justify-center text-sm leading-none shrink-0">
            +
          </div>
          <span className="text-xs">Add member</span>
        </button>
      ))}

      <CharacterDossier
        character={selectedChar}
        open={dossierOpen}
        onClose={() => setDossierOpen(false)}
        accentColor={
          selectedChar
            ? slotColor(players.indexOf(selectedChar))
            : playerColors[0]
        }
      />

      {adventureId && (
        <PartySlotModal
          open={slotModalOpen}
          adventureId={adventureId}
          inviteCode={adventure?.inviteCode ?? null}
          onClose={() => setSlotModalOpen(false)}
        />
      )}
    </div>
  )
}
