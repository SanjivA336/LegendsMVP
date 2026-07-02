import { useState } from 'react'
import { useGameStore } from '../../store/gameStore'
import { useAdventure } from '../../hooks/useAdventure'
import { useParty, useInventory } from '../../hooks/useCharacter'
import { useAuth } from '../../contexts/AuthContext'
import PartyPanel from '../character/PartyPanel'
import InventoryPanel from '../character/InventoryPanel'
import ChatTab from '../chat/ChatTab'

interface RightSidebarProps {
  open: boolean
}

type ActiveTab = 'party' | 'inventory' | 'chat'

function PeopleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  )
}

function PackageIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="16.5" y1="9.4" x2="7.5" y2="4.21" />
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
      <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
      <line x1="12" y1="22.08" x2="12" y2="12" />
    </svg>
  )
}

function ChatBubbleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  )
}

const TAB_ICONS: Record<ActiveTab, () => React.ReactElement> = {
  party: PeopleIcon,
  inventory: PackageIcon,
  chat: ChatBubbleIcon,
}

const TAB_LABELS: Record<ActiveTab, string> = {
  party: 'Party',
  inventory: 'Inventory',
  chat: 'Chat',
}

export default function RightSidebar({ open }: RightSidebarProps) {
  const [activeTab, setActiveTab] = useState<ActiveTab>('party')
  const toggleRight = useGameStore((s) => s.toggleRightSidebar)
  const activeCharacterId = useGameStore((s) => s.activeCharacterId)
  const adventure = useAdventure()

  const { displayName } = useAuth()
  const { data: party = [] } = useParty(adventure?.id ?? null)
  const { data: inventory = [] } = useInventory(activeCharacterId)

  const playerCharacter = party.find((c) => c.id === activeCharacterId) ?? null

  if (!open) {
    return (
      <div className="flex flex-col items-center pt-2 gap-1">
        <button
          onClick={toggleRight}
          className="w-10 h-10 flex items-center justify-center text-zinc-500 hover:text-zinc-100 hover:bg-zinc-800 rounded-lg transition-colors duration-150"
          title="Expand sidebar"
        >
          &#x276E;
        </button>
        {(['party', 'inventory', 'chat'] as ActiveTab[]).map((tab) => {
          const Icon = TAB_ICONS[tab]
          return (
            <button
              key={tab}
              onClick={() => { toggleRight(); setActiveTab(tab) }}
              className="w-10 h-10 flex items-center justify-center text-zinc-500 hover:text-zinc-100 hover:bg-zinc-800 rounded-lg transition-colors duration-150"
              title={TAB_LABELS[tab]}
            >
              <Icon />
            </button>
          )
        })}
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-800 shrink-0">
        <button
          onClick={toggleRight}
          className="w-7 h-7 flex items-center justify-center text-zinc-500 hover:text-zinc-100 rounded-lg transition-colors duration-150"
          title="Collapse"
        >
          &#x276F;
        </button>
        <div className="flex gap-1">
          {(['party', 'inventory', 'chat'] as ActiveTab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors duration-150 ${
                activeTab === tab
                  ? 'bg-zinc-800 text-zinc-100'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              {TAB_LABELS[tab]}
            </button>
          ))}
        </div>
      </div>

      {/* Content — two panels always mounted, one hidden at a time */}
      <div className="flex-1 overflow-hidden">
        {/* Party + Inventory — scrollable */}
        <div className={`h-full overflow-y-auto ${activeTab === 'chat' ? 'hidden' : ''}`}>
          {activeTab === 'party' && <PartyPanel characters={party} />}
          {activeTab === 'inventory' && (
            <InventoryPanel character={playerCharacter} inventory={inventory} />
          )}
        </div>
        {/* Chat — manages its own scroll internally */}
        <div className={`h-full ${activeTab !== 'chat' ? 'hidden' : ''}`}>
          <ChatTab
            adventureId={adventure?.id ?? null}
            characterId={activeCharacterId}
            characterName={playerCharacter?.name ?? null}
            userDisplayName={displayName}
          />
        </div>
      </div>
    </div>
  )
}
