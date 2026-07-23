import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface AdventureMeta {
  id: string
  name: string
  worldName: string
  worldMapId: string | null
  playerCharacterId: string | null
  role: 'owner' | 'admin' | 'player' | 'viewer'
  inviteCode: string | null
  createdAt: string
  attributeNames: Record<string, string>
  openingNarrative: string | null
  narrativeEncounterId: string | null
  spawnTileX: number
  spawnTileY: number
  lastTileX: number | null
  lastTileY: number | null
  biomeColorOverrides: Record<string, string>
}

interface GameStore {
  adventures: AdventureMeta[]
  activeAdventureId: string | null
  activeCharacterId: string | null
  currentMapId: string | null
  currentTileX: number | null
  currentTileY: number | null
  leftSidebarOpen: boolean
  rightSidebarOpen: boolean
  activeEncounterId: string | null
  combatActive: boolean

  addAdventure: (meta: Omit<AdventureMeta, 'narrativeEncounterId' | 'lastTileX' | 'lastTileY'>) => void
  setAdventures: (list: AdventureMeta[]) => void
  setActiveAdventure: (id: string) => void
  removeAdventure: (id: string) => void
  setCurrentTile: (x: number, y: number) => void
  toggleLeftSidebar: () => void
  toggleRightSidebar: () => void
  setActiveEncounter: (id: string | null) => void
  setCombatActive: (active: boolean) => void
  updateAdventure: (id: string, patch: Partial<AdventureMeta>) => void
  setNarrativeEncounter: (adventureId: string, encounterId: string) => void
}

export const useGameStore = create<GameStore>()(
  persist(
    (set) => ({
      adventures: [],
      activeAdventureId: null,
      activeCharacterId: null,
      currentMapId: null,
      currentTileX: null,
      currentTileY: null,
      leftSidebarOpen: true,
      rightSidebarOpen: true,
      activeEncounterId: null,
      combatActive: false,

      addAdventure: (meta) =>
        set((s) => {
          const full: AdventureMeta = {
            ...meta,
            narrativeEncounterId: null,
            lastTileX: meta.spawnTileX,
            lastTileY: meta.spawnTileY,
          }
          return {
            adventures: [...s.adventures, full],
            activeAdventureId: full.id,
            activeCharacterId: full.playerCharacterId,
            currentMapId: full.worldMapId,
            currentTileX: meta.spawnTileX,
            currentTileY: meta.spawnTileY,
          }
        }),

      setAdventures: (list) => set({ adventures: list }),

      setActiveAdventure: (id) =>
        set((s) => {
          const meta = s.adventures.find((a) => a.id === id)
          return {
            activeAdventureId: id,
            activeCharacterId: meta?.playerCharacterId ?? null,
            currentMapId: meta?.worldMapId ?? null,
            currentTileX: meta?.lastTileX ?? meta?.spawnTileX ?? 32,
            currentTileY: meta?.lastTileY ?? meta?.spawnTileY ?? 32,
            activeEncounterId: meta?.narrativeEncounterId ?? null,
          }
        }),

      removeAdventure: (id) =>
        set((s) => ({
          adventures: s.adventures.filter((a) => a.id !== id),
          activeAdventureId: s.activeAdventureId === id ? null : s.activeAdventureId,
          activeCharacterId: s.activeAdventureId === id ? null : s.activeCharacterId,
          currentMapId: s.activeAdventureId === id ? null : s.currentMapId,
          activeEncounterId: s.activeAdventureId === id ? null : s.activeEncounterId,
        })),

      updateAdventure: (id, patch) =>
        set((s) => ({
          adventures: s.adventures.map((a) => (a.id === id ? { ...a, ...patch } : a)),
        })),

      setCurrentTile: (x, y) =>
        set((s) => ({
          currentTileX: x,
          currentTileY: y,
          adventures: s.adventures.map((a) =>
            a.id === s.activeAdventureId ? { ...a, lastTileX: x, lastTileY: y } : a
          ),
        })),

      setNarrativeEncounter: (adventureId, encounterId) =>
        set((s) => ({
          activeEncounterId: encounterId,
          adventures: s.adventures.map((a) =>
            a.id === adventureId ? { ...a, narrativeEncounterId: encounterId } : a
          ),
        })),

      toggleLeftSidebar: () => set((s) => ({ leftSidebarOpen: !s.leftSidebarOpen })),
      toggleRightSidebar: () => set((s) => ({ rightSidebarOpen: !s.rightSidebarOpen })),

      setActiveEncounter: (id) => set({ activeEncounterId: id }),
      setCombatActive: (active) => set({ combatActive: active }),
    }),
    {
      name: 'worldforge-game-store',
      partialize: (s) => ({
        activeAdventureId: s.activeAdventureId,
        activeCharacterId: s.activeCharacterId,
        currentMapId: s.currentMapId,
        currentTileX: s.currentTileX,
        currentTileY: s.currentTileY,
        leftSidebarOpen: s.leftSidebarOpen,
        rightSidebarOpen: s.rightSidebarOpen,
        activeEncounterId: s.activeEncounterId,
        combatActive: s.combatActive,
      }),
    }
  )
)
