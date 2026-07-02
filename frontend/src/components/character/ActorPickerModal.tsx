import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchActors, addActorSlot, type Actor } from '../../api/actors'
import ActorCreateModal from './ActorCreateModal'

interface Props {
  open: boolean
  adventureId: string
  onClose: () => void
}

const STANCE_LABELS = ['', 'Pacifist', 'Defensive', 'Balanced', 'Aggressive', 'Berserker']
const TACTICS_LABELS = ['', 'Calculated', 'Methodical', 'Adaptive', 'Bold', 'Reckless']
const DISPOSITION_LABELS = ['', 'Noble', 'Principled', 'Pragmatic', 'Cunning', 'Ruthless']

function actorAxisSummary(actor: Actor): string {
  return [
    STANCE_LABELS[actor.stance] ?? 'Balanced',
    TACTICS_LABELS[actor.tactics] ?? 'Adaptive',
    DISPOSITION_LABELS[actor.disposition] ?? 'Pragmatic',
  ].join(' · ')
}

export default function ActorPickerModal({ open, adventureId, onClose }: Props) {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [adding, setAdding] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)

  const { data: actors = [] } = useQuery({
    queryKey: ['actors'],
    queryFn: fetchActors,
    enabled: open,
  })

  const filtered = actors.filter((a) =>
    a.name.toLowerCase().includes(search.toLowerCase())
  )

  async function handlePick(actor: Actor) {
    if (adding) return
    setAdding(actor.id)
    try {
      await addActorSlot(adventureId, actor.id)
      await queryClient.invalidateQueries({ queryKey: ['actor-slots', adventureId] })
      onClose()
    } catch {
      // Non-fatal
    } finally {
      setAdding(null)
    }
  }

  function handleActorCreated(actor: Actor) {
    queryClient.setQueryData<Actor[]>(['actors'], (prev = []) => [...prev, actor])
    setCreateOpen(false)
  }

  if (!open) return null

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/70 backdrop-blur-sm">
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 w-full max-w-2xl mx-4 flex flex-col gap-4 max-h-[80vh]">
          <div className="flex items-center justify-between shrink-0">
            <h2 className="text-base font-semibold text-zinc-100">Add Actor</h2>
            <button
              onClick={onClose}
              className="text-zinc-500 hover:text-zinc-200 text-xl leading-none transition-colors"
            >
              &#x2715;
            </button>
          </div>

          {/* Search + Create button — 10/2 column split */}
          <div className="grid grid-cols-12 gap-2 shrink-0">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search actors…"
              className="col-span-10 px-3 py-2 rounded-xl bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-accent transition-colors"
            />
            <button
              onClick={() => setCreateOpen(true)}
              className="col-span-2 px-2 py-2 rounded-xl bg-zinc-700 hover:bg-zinc-600 text-xs font-semibold text-zinc-200 transition-colors text-center"
            >
              + Create
            </button>
          </div>

          {/* Actor grid */}
          <div className="overflow-y-auto flex-1">
            {actors.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
                <p className="text-sm text-zinc-500">No actors yet.</p>
                <button
                  onClick={() => setCreateOpen(true)}
                  className="text-sm text-accent hover:text-accent/80 transition-colors"
                >
                  Create your first actor
                </button>
              </div>
            ) : filtered.length === 0 ? (
              <p className="text-center text-sm text-zinc-600 py-8">No actors match your search.</p>
            ) : (
              <div className="grid grid-cols-3 gap-3">
                {filtered.map((actor) => (
                  <button
                    key={actor.id}
                    onClick={() => handlePick(actor)}
                    disabled={adding === actor.id}
                    className="h-28 flex flex-col justify-between p-3 rounded-xl border border-zinc-700 bg-zinc-800/60 hover:border-zinc-500 hover:bg-zinc-800 text-left transition-colors duration-150 disabled:opacity-60"
                  >
                    <div>
                      <div className="text-sm font-semibold text-zinc-100 truncate">{actor.name}</div>
                      {actor.description && (
                        <div className="text-xs text-zinc-500 mt-0.5 line-clamp-1">{actor.description}</div>
                      )}
                    </div>
                    <div className="text-[10px] text-zinc-600 font-mono">
                      {actorAxisSummary(actor)}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <ActorCreateModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={handleActorCreated}
      />
    </>
  )
}
