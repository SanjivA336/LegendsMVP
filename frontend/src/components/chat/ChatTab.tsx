import { useState, useRef, useEffect } from 'react'
import { oocChat } from '../../api/narrator'
import { PLAYER_COLORS, NARRATOR_COLOR } from '../../constants/colors'

interface ChatMessage {
  id: string
  sender: 'player' | 'dm'
  label: string
  color: string
  text: string
}

interface ChatTabProps {
  adventureId: string | null
  characterId: string | null
  characterName: string | null
  userDisplayName: string | null
}

export default function ChatTab({ adventureId, characterId, characterName: _characterName, userDisplayName }: ChatTabProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend() {
    const text = input.trim()
    if (!text || thinking || !adventureId || !characterId) return
    setInput('')

    const playerLabel = userDisplayName ?? 'Player'
    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        sender: 'player',
        label: playerLabel,
        color: PLAYER_COLORS[0],
        text,
      },
    ])
    setThinking(true)

    try {
      const result = await oocChat({
        adventure_id: adventureId,
        character_id: characterId,
        player_text: text,
        user_display_name: userDisplayName ?? undefined,
      })
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), sender: 'dm', label: 'DM', color: NARRATOR_COLOR, text: result.response },
      ])
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), sender: 'dm', label: 'System', color: '#71717a', text: 'The DM is unavailable right now.' },
      ])
    } finally {
      setThinking(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Message list */}
      <div className="flex-1 overflow-y-auto min-h-0 p-3 flex flex-col gap-2">
        {messages.length === 0 && (
          <p className="text-xs text-zinc-600 text-center py-8 italic leading-relaxed">
            Ask the DM anything — out of character.
            <br />
            Recap, lore, clarification, tips.
          </p>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col gap-0.5 ${msg.sender === 'player' ? 'items-end' : 'items-start'}`}
          >
            <span
              className="text-[9px] font-semibold uppercase tracking-wider px-0.5"
              style={{ color: msg.color }}
            >
              {msg.label}
            </span>
            <div
              className={`max-w-[85%] px-3 py-2 text-xs leading-relaxed ${
                msg.sender === 'player'
                  ? 'rounded-2xl rounded-tr-sm'
                  : 'rounded-2xl rounded-tl-sm bg-zinc-800'
              }`}
              style={
                msg.sender === 'player'
                  ? {
                      backgroundColor: PLAYER_COLORS[0] + '22',
                      color: '#f4f4f5',
                      border: `1px solid ${PLAYER_COLORS[0]}40`,
                    }
                  : { color: '#f4f4f5' }
              }
            >
              {msg.text}
            </div>
          </div>
        ))}

        {thinking && (
          <div className="flex flex-col gap-0.5 items-start">
            <span className="text-[9px] font-semibold uppercase tracking-wider px-0.5" style={{ color: NARRATOR_COLOR }}>
              DM
            </span>
            <div className="bg-zinc-800 px-3 py-2.5 rounded-2xl rounded-tl-sm flex gap-1 items-center">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="shrink-0 border-t border-zinc-800 p-3 flex flex-col gap-1.5">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                void handleSend()
              }
            }}
            disabled={thinking || !adventureId}
            placeholder={thinking ? 'DM is thinking…' : 'Ask the DM something…'}
            className="flex-1 bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-500 px-2.5 py-1.5 rounded-xl text-xs focus:outline-none focus:border-accent transition-colors duration-150 disabled:opacity-50"
          />
          <button
            onClick={() => void handleSend()}
            disabled={thinking || !input.trim() || !adventureId}
            className="px-2.5 py-1.5 bg-accent hover:bg-accent-hover text-zinc-950 rounded-xl text-xs font-semibold transition-colors duration-150 disabled:opacity-40"
          >
            Send
          </button>
        </div>
        <p className="text-[9px] text-zinc-600 text-center">OOC · session only · not saved</p>
      </div>
    </div>
  )
}
