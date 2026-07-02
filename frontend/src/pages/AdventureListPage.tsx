import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useGameStore } from '../store/gameStore'
import { fetchAdventures, deleteAdventureRecord, joinAdventure } from '../api/adventures'
import type { AdventureMeta } from '../store/gameStore'

function CrownIcon() {
  return (
    <span className="shrink-0" title="Owner — full control, can delete adventure and promote to admin">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" className="text-amber-400">
        <path d="M5 16L3 5l5.5 5L12 4l3.5 6L21 5l-2 11H5zm0 2h14v2H5v-2z" />
      </svg>
    </span>
  )
}

export default function AdventureListPage() {
  const setActiveAdventure = useGameStore((s) => s.setActiveAdventure)
  const removeAdventure = useGameStore((s) => s.removeAdventure)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: adventures = [], isLoading } = useQuery({
    queryKey: ['adventures'],
    queryFn: fetchAdventures,
  })

  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [inviteCode, setInviteCode] = useState('')
  const [joining, setJoining] = useState(false)
  const [joinError, setJoinError] = useState<string | null>(null)
  const [copied, setCopied] = useState<string | null>(null)

  function handleContinue(adv: AdventureMeta) {
    setActiveAdventure(adv.id)
    navigate(`/adventures/${adv.id}`)
  }

  async function confirmAndDelete() {
    if (!confirmDelete) return
    setDeleting(true)
    try {
      await deleteAdventureRecord(confirmDelete)
      removeAdventure(confirmDelete)
      await queryClient.invalidateQueries({ queryKey: ['adventures'] })
    } catch {
      // Non-fatal; the query refetch will update the list
    } finally {
      setDeleting(false)
      setConfirmDelete(null)
    }
  }

  async function handleJoin() {
    if (!inviteCode.trim()) return
    setJoining(true)
    setJoinError(null)
    try {
      await joinAdventure(inviteCode.trim())
      setInviteCode('')
      await queryClient.invalidateQueries({ queryKey: ['adventures'] })
    } catch (err) {
      setJoinError(err instanceof Error ? err.message : 'Invalid invite code')
    } finally {
      setJoining(false)
    }
  }

  function copyInvite(code: string) {
    navigator.clipboard.writeText(code).catch(() => {})
    setCopied(code)
    setTimeout(() => setCopied(null), 2000)
  }

  const deletingAdv = adventures.find((a) => a.id === confirmDelete)

  return (
    <>
      {/* Delete confirmation modal */}
      {confirmDelete && deletingAdv && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/70 backdrop-blur-sm">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 w-full max-w-sm mx-4 flex flex-col gap-4">
            <h2 className="text-base font-semibold text-zinc-100">Delete Adventure?</h2>
            <p className="text-sm text-zinc-400">
              <span className="text-zinc-200 font-medium">{deletingAdv.name}</span> and all its data —
              characters, quests, world map, encounters — will be permanently deleted. This cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setConfirmDelete(null)}
                disabled={deleting}
                className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150"
              >
                Cancel
              </button>
              <button
                onClick={confirmAndDelete}
                disabled={deleting}
                className="px-4 py-2 text-sm bg-red-900 hover:bg-red-800 text-red-100 font-semibold rounded-xl transition-colors duration-150 disabled:opacity-60"
              >
                {deleting ? 'Deleting…' : 'Delete forever'}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-2xl mx-auto px-6 py-12 w-full">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">Adventures</h1>
          <Link
            to="/adventures/new"
            className="text-sm bg-accent hover:bg-accent-hover text-zinc-950 font-semibold px-3 py-1.5 rounded-lg transition-colors duration-150"
          >
            New Adventure
          </Link>
        </div>

        {/* Join by invite code */}
        <div className="mb-6 flex gap-2">
          <input
            type="text"
            value={inviteCode}
            onChange={(e) => setInviteCode(e.target.value)}
            placeholder="Enter invite code to join…"
            className="flex-1 px-3 py-2 rounded-xl bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-accent transition-colors"
            onKeyDown={(e) => e.key === 'Enter' && handleJoin()}
          />
          <button
            onClick={handleJoin}
            disabled={joining || !inviteCode.trim()}
            className="px-4 py-2 text-sm bg-zinc-700 hover:bg-zinc-600 text-zinc-100 font-semibold rounded-xl transition-colors disabled:opacity-50"
          >
            {joining ? 'Joining…' : 'Join'}
          </button>
        </div>
        {joinError && <p className="mb-4 text-sm text-red-400">{joinError}</p>}

        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          </div>
        ) : adventures.length === 0 ? (
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-12 flex flex-col items-center gap-4 text-center">
            <p className="text-zinc-400">No adventures yet.</p>
            <Link
              to="/adventures/new"
              className="text-sm text-accent hover:text-accent-hover transition-colors duration-150"
            >
              Create your first adventure
            </Link>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {adventures.map((adv) => (
              <div
                key={adv.id}
                className="rounded-2xl border border-zinc-800 bg-zinc-900 p-5 flex items-center gap-4 hover:border-zinc-700 transition-colors duration-150"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    {adv.role === 'owner' && <CrownIcon />}
                    <span className="font-semibold text-zinc-100 truncate">{adv.name}</span>
                  </div>
                  <div className="text-sm text-zinc-400 mt-0.5">{adv.worldName}</div>
                  <div className="text-xs text-zinc-600 mt-1 flex items-center gap-3">
                    <span>{new Date(adv.createdAt).toLocaleDateString()}</span>
                    {adv.inviteCode && (adv.role === 'owner' || adv.role === 'admin') && (
                      <button
                        onClick={() => copyInvite(adv.inviteCode!)}
                        className="text-zinc-500 hover:text-zinc-300 transition-colors"
                        title="Copy invite code"
                      >
                        {copied === adv.inviteCode ? 'Copied!' : `Code: ${adv.inviteCode}`}
                      </button>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  {adv.role === 'owner' && (
                    <button
                      onClick={() => setConfirmDelete(adv.id)}
                      className="text-sm text-zinc-600 hover:text-red-400 transition-colors duration-150"
                      title="Delete adventure"
                    >
                      &#x2715;
                    </button>
                  )}
                  <button
                    onClick={() => handleContinue(adv)}
                    className="text-sm text-accent hover:text-accent-hover font-semibold transition-colors duration-150"
                  >
                    Continue
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  )
}
