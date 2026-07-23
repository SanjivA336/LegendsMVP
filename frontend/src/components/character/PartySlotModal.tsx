import { useState } from 'react'
import ActorPickerModal from './ActorPickerModal'
import CharacterCreationModal from './CharacterCreationModal'

interface Props {
  open: boolean
  adventureId: string
  inviteCode: string | null
  onClose: () => void
}

export default function PartySlotModal({ open, adventureId, inviteCode, onClose }: Props) {
  const [actorPickerOpen, setActorPickerOpen] = useState(false)
  const [characterCreationOpen, setCharacterCreationOpen] = useState(false)
  const [copied, setCopied] = useState(false)

  function copyCode() {
    if (!inviteCode) return
    navigator.clipboard.writeText(inviteCode).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!open) return null

  if (actorPickerOpen) {
    return (
      <ActorPickerModal
        open
        adventureId={adventureId}
        onClose={() => {
          setActorPickerOpen(false)
          onClose()
        }}
      />
    )
  }

  if (characterCreationOpen) {
    return (
      <CharacterCreationModal
        open
        adventureId={adventureId}
        onClose={() => {
          setCharacterCreationOpen(false)
          onClose()
        }}
      />
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/70 backdrop-blur-sm">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 w-full max-w-sm mx-4 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-zinc-100">Add Party Member</h2>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-200 text-xl leading-none transition-colors"
          >
            &#x2715;
          </button>
        </div>

        <div className="flex flex-col gap-3">
          {/* Invite Player option */}
          <div className="rounded-xl border border-zinc-700 p-4 flex flex-col gap-2">
            <p className="text-sm font-semibold text-zinc-200">Invite Player</p>
            <p className="text-xs text-zinc-500">Share this code with another player to let them join.</p>
            {inviteCode ? (
              <div className="flex items-center gap-2 mt-1">
                <code className="flex-1 px-3 py-2 bg-zinc-800 rounded-lg text-sm font-mono text-zinc-300 select-all">
                  {inviteCode}
                </code>
                <button
                  onClick={copyCode}
                  className="px-3 py-2 rounded-lg bg-zinc-700 hover:bg-zinc-600 text-xs font-semibold text-zinc-200 transition-colors shrink-0"
                >
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
            ) : (
              <p className="text-xs text-zinc-600">Invite code not available.</p>
            )}
          </div>

          {/* Add Actor option */}
          <button
            onClick={() => setActorPickerOpen(true)}
            className="rounded-xl border border-zinc-700 p-4 text-left hover:border-zinc-600 hover:bg-zinc-800/50 transition-colors"
          >
            <p className="text-sm font-semibold text-zinc-200">Add Actor</p>
            <p className="text-xs text-zinc-500 mt-0.5">Add an AI-controlled party member with a preset behavioral profile.</p>
          </button>

          {/* Create Character option */}
          <button
            onClick={() => setCharacterCreationOpen(true)}
            className="rounded-xl border border-zinc-700 p-4 text-left hover:border-zinc-600 hover:bg-zinc-800/50 transition-colors"
          >
            <p className="text-sm font-semibold text-zinc-200">Create Character</p>
            <p className="text-xs text-zinc-500 mt-0.5">Build a full NPC with fields, gear, and inventory from scratch.</p>
          </button>
        </div>
      </div>
    </div>
  )
}
