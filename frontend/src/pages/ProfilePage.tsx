import { useState, type FormEvent } from 'react'
import { useAuth } from '../contexts/AuthContext'

export default function ProfilePage() {
  const { displayName, updateDisplayName } = useAuth()
  const [name, setName] = useState(displayName ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSaved(false)
    setSaving(true)
    try {
      await updateDisplayName(name)
      setSaved(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update profile')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-12 w-full">
      <h1 className="text-2xl font-semibold tracking-tight text-zinc-100 mb-8">Profile</h1>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-6 mb-6">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-zinc-400 uppercase tracking-wider">Display name</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="px-3 py-2.5 rounded-xl bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-accent transition-colors"
              placeholder="How you appear to others"
            />
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}
          {saved && !error && <p className="text-sm text-accent">Saved.</p>}

          <button
            type="submit"
            disabled={saving}
            className="self-start mt-2 px-5 py-2.5 rounded-xl bg-accent text-sm font-semibold text-zinc-950 hover:bg-accent/90 disabled:opacity-60 transition-colors"
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
        </form>
      </div>
    </div>
  )
}
