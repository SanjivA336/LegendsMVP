import { useState } from 'react'
import { createActor, type Actor } from '../../api/actors'

interface Props {
  open: boolean
  onClose: () => void
  onCreated: (actor: Actor) => void
}

// All three axes: green (1) → yellow (3) → red (5)
const STAGE_COLORS = [
  'bg-emerald-600 border-emerald-500 text-white',
  'bg-lime-600 border-lime-500 text-white',
  'bg-yellow-500 border-yellow-400 text-zinc-900',
  'bg-orange-500 border-orange-400 text-white',
  'bg-red-600 border-red-500 text-white',
]

const AXES = [
  {
    key: 'stance' as const,
    label: 'Stance',
    description: 'Combat readiness',
    stages: ['Pacifist', 'Defensive', 'Balanced', 'Aggressive', 'Berserker'],
  },
  {
    key: 'tactics' as const,
    label: 'Tactics',
    description: 'Risk tolerance',
    stages: ['Calculated', 'Methodical', 'Adaptive', 'Bold', 'Reckless'],
  },
  {
    key: 'disposition' as const,
    label: 'Disposition',
    description: 'Moral bearing',
    stages: ['Noble', 'Principled', 'Pragmatic', 'Cunning', 'Ruthless'],
  },
]

export default function ActorCreateModal({ open, onClose, onCreated }: Props) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [stance, setStance] = useState(3)
  const [tactics, setTactics] = useState(3)
  const [disposition, setDisposition] = useState(3)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const values: Record<'stance' | 'tactics' | 'disposition', number> = { stance, tactics, disposition }
  const setters: Record<'stance' | 'tactics' | 'disposition', (v: number) => void> = {
    stance: setStance,
    tactics: setTactics,
    disposition: setDisposition,
  }

  async function handleSave() {
    if (!name.trim()) return
    setSaving(true)
    setError(null)
    try {
      const actor = await createActor({ name: name.trim(), description, stance, tactics, disposition })
      onCreated(actor)
      setName('')
      setDescription('')
      setStance(3)
      setTactics(3)
      setDisposition(3)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create actor')
    } finally {
      setSaving(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-60 flex items-center justify-center bg-zinc-950/70 backdrop-blur-sm">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 w-full max-w-lg mx-4 flex flex-col gap-5">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-zinc-100">Create Actor</h2>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-200 text-xl leading-none transition-colors"
          >
            &#x2715;
          </button>
        </div>

        {error && (
          <div className="p-3 bg-red-950 border border-red-800 rounded-xl text-sm text-red-300">
            {error}
          </div>
        )}

        <div className="flex flex-col gap-1">
          <label className="text-xs text-zinc-400 uppercase tracking-wider">Name *</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Actor name"
            className="px-3 py-2.5 rounded-xl bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-accent transition-colors"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-zinc-400 uppercase tracking-wider">
            Description <span className="text-zinc-600 normal-case">(optional)</span>
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            placeholder="Optional flavor text…"
            className="px-3 py-2.5 rounded-xl bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-accent transition-colors resize-none"
          />
        </div>

        {AXES.map((axis) => (
          <div key={axis.key} className="flex flex-col gap-2">
            <div className="flex items-baseline gap-2">
              <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">{axis.label}</span>
              <span className="text-xs text-zinc-600">{axis.description}</span>
            </div>
            <div className="grid grid-cols-5 gap-1">
              {axis.stages.map((stage, i) => {
                const val = i + 1
                const active = values[axis.key] === val
                return (
                  <button
                    key={stage}
                    onClick={() => setters[axis.key](val)}
                    className={`py-1.5 px-1 rounded-lg border text-xs font-medium transition-colors duration-100 ${
                      active
                        ? STAGE_COLORS[i]
                        : 'border-zinc-700 text-zinc-500 bg-transparent hover:border-zinc-600 hover:text-zinc-400'
                    }`}
                  >
                    {stage}
                  </button>
                )
              })}
            </div>
          </div>
        ))}

        <div className="flex justify-end gap-3 pt-1">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !name.trim()}
            className="px-5 py-2 rounded-xl bg-accent text-sm font-semibold text-zinc-950 hover:bg-accent/90 disabled:opacity-60 transition-colors"
          >
            {saving ? 'Saving…' : 'Create Actor'}
          </button>
        </div>
      </div>
    </div>
  )
}
