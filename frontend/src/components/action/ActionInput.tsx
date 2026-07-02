import { useState } from 'react'
import { useGameStore } from '../../store/gameStore'

interface ActionInputProps {
  onSendAction: (text: string) => void
  onEndTurn?: () => void
  onOpenMap?: () => void
  disabled?: boolean
}

export default function ActionInput({ onSendAction, onEndTurn, onOpenMap, disabled = false }: ActionInputProps) {
  const [text, setText] = useState('')
  const combatActive = useGameStore((s) => s.combatActive)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSendAction(trimmed)
    setText('')
  }

  return (
    <div className="border-t border-zinc-800 bg-zinc-900 shrink-0">
      {/* Quick actions */}
      <div className="flex items-center gap-1 px-3 pt-2">
        <button
          onClick={onOpenMap}
          className="px-2.5 py-1 rounded-lg text-xs text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 border border-zinc-700 hover:border-zinc-600 transition-colors duration-150"
        >
          World Map
        </button>
        {combatActive && (
          <button
            onClick={onEndTurn}
            disabled={disabled}
            className="px-2.5 py-1 rounded-lg text-xs text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 border border-zinc-700 hover:border-zinc-600 transition-colors duration-150 disabled:opacity-40"
          >
            End Turn
          </button>
        )}
      </div>

      {/* Text input */}
      <form onSubmit={handleSubmit} className="flex items-center gap-2 px-3 py-2">
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={disabled}
          placeholder={disabled ? 'DM is thinking...' : combatActive ? 'Describe your action...' : 'Speak or act...'}
          className="flex-1 bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-500 px-3 py-2 rounded-lg text-sm focus:outline-none focus:border-accent transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <button
          type="submit"
          disabled={disabled || !text.trim()}
          className="px-3 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold text-sm rounded-lg transition-colors duration-150 disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </div>
  )
}
