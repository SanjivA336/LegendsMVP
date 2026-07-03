import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { PLAYER_COLORS } from '../constants/colors'

const DEFAULT_ACCENT = '#F8961E'
const PLAYER_LABELS = ['Player 1', 'Player 2', 'Player 3', 'Player 4']

export default function PreferencesPage() {
  const { preferences, updatePreferences } = useAuth()
  const [accentColor, setAccentColor] = useState(preferences.accentColor)
  const [playerColors, setPlayerColors] = useState(preferences.playerColors ?? PLAYER_COLORS)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  function setPlayerColor(index: number, color: string) {
    setPlayerColors((prev) => prev.map((c, i) => (i === index ? color : c)))
  }

  function resetPlayerColor(index: number) {
    setPlayerColors((prev) => prev.map((c, i) => (i === index ? PLAYER_COLORS[index] : c)))
  }

  async function handleSave() {
    setError(null)
    setSaved(false)
    setSaving(true)
    try {
      await updatePreferences({ accentColor, playerColors })
      setSaved(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save preferences')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-12 w-full">
      <h1 className="text-2xl font-semibold tracking-tight text-zinc-100 mb-8">Preferences</h1>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-zinc-200">Accent Color</h2>
          <button
            onClick={() => setAccentColor(null)}
            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors duration-150"
          >
            Reset to default
          </button>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="color"
            value={accentColor ?? DEFAULT_ACCENT}
            onChange={(e) => setAccentColor(e.target.value)}
            className="w-10 h-10 rounded-lg border border-zinc-700 bg-zinc-800 cursor-pointer"
          />
          <span className="text-sm text-zinc-400 font-mono">{accentColor ?? DEFAULT_ACCENT}</span>
        </div>
      </div>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-zinc-200">Player Colors</h2>
          <button
            onClick={() => setPlayerColors(PLAYER_COLORS)}
            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors duration-150"
          >
            Reset all
          </button>
        </div>
        <div className="flex flex-col gap-3">
          {PLAYER_LABELS.map((label, i) => (
            <div key={label} className="flex items-center gap-3">
              <input
                type="color"
                value={playerColors[i]}
                onChange={(e) => setPlayerColor(i, e.target.value)}
                className="w-10 h-10 rounded-lg border border-zinc-700 bg-zinc-800 cursor-pointer"
              />
              <span className="text-sm text-zinc-300 flex-1">{label}</span>
              <span className="text-xs text-zinc-500 font-mono">{playerColors[i]}</span>
              <button
                onClick={() => resetPlayerColor(i)}
                className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors duration-150"
              >
                Reset
              </button>
            </div>
          ))}
        </div>
      </div>

      {error && <p className="mb-4 text-sm text-red-400">{error}</p>}
      {saved && !error && <p className="mb-4 text-sm text-accent">Saved.</p>}

      <button
        onClick={handleSave}
        disabled={saving}
        className="px-5 py-2.5 rounded-xl bg-accent text-sm font-semibold text-zinc-950 hover:bg-accent/90 disabled:opacity-60 transition-colors"
      >
        {saving ? 'Saving…' : 'Save Preferences'}
      </button>
    </div>
  )
}
