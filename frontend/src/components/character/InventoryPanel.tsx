import { useState } from 'react'
import type { Character } from '../../types/character'
import type { ResolvedItemInstance } from '../../types/item'

interface InventoryPanelProps {
  character: Character | null
  inventory: ResolvedItemInstance[]
}

export default function InventoryPanel({ character, inventory }: InventoryPanelProps) {
  const [query, setQuery] = useState('')

  const filtered = query
    ? inventory.filter(
        (item) =>
          item.name.toLowerCase().includes(query.toLowerCase()) ||
          item.description.toLowerCase().includes(query.toLowerCase())
      )
    : inventory

  if (!character) {
    return <p className="text-sm text-zinc-500 px-4 py-3">Select a character to view inventory.</p>
  }

  return (
    <div className="flex flex-col gap-2 px-3 py-2">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search items..."
        className="w-full bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-500 px-2.5 py-1.5 rounded-lg text-xs focus:outline-none focus:border-accent transition-colors duration-150"
      />
      {filtered.length === 0 && (
        <p className="text-xs text-zinc-600 py-2 text-center">
          {query ? 'No items match.' : 'Inventory is empty.'}
        </p>
      )}
      <div className="flex flex-col gap-1">
        {filtered.map((item) => {
          const isEquipped = character.equipped_weapon_id === item.id
          return (
            <div
              key={item.id}
              className={`px-2.5 py-2 rounded-lg text-xs flex items-start gap-2 ${
                isEquipped
                  ? 'bg-zinc-800 border border-accent/40'
                  : 'bg-zinc-800/60 border border-transparent'
              }`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="font-semibold text-zinc-200 truncate">{item.name}</span>
                  {isEquipped && (
                    <span className="text-accent text-[10px] uppercase tracking-wider shrink-0">
                      equipped
                    </span>
                  )}
                </div>
                {item.description && (
                  <p className="text-zinc-500 mt-0.5 leading-snug line-clamp-2">
                    {item.description}
                  </p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
