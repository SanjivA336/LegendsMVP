import { authFetch, BASE } from './apiClient'
import type { AdventureMeta } from '../store/gameStore'

interface ServerAdventureEntry {
  adventure: {
    id: string
    name: string
    world_name: string
    world_map_id: string | null
    invite_code: string
    created_at: string
  }
  member: {
    id: string
    adventure_id: string
    user_uid: string
    role: 'owner' | 'admin' | 'player' | 'viewer'
    character_id: string | null
    joined_at: string
  }
}

function entryToMeta(entry: ServerAdventureEntry): AdventureMeta {
  return {
    id: entry.adventure.id,
    name: entry.adventure.name,
    worldName: entry.adventure.world_name,
    worldMapId: entry.adventure.world_map_id,
    playerCharacterId: entry.member.character_id,
    role: entry.member.role,
    inviteCode: entry.adventure.invite_code,
    createdAt: entry.adventure.created_at,
    attributeNames: {},
    openingNarrative: null,
    narrativeEncounterId: null,
    spawnTileX: 32,
    spawnTileY: 32,
    lastTileX: null,
    lastTileY: null,
    biomeColorOverrides: {},
  }
}

export async function fetchAdventures(): Promise<AdventureMeta[]> {
  const res = await authFetch(`${BASE}/adventures`)
  if (!res.ok) throw new Error(await res.text())
  const entries: ServerAdventureEntry[] = await res.json()
  return entries.map(entryToMeta)
}

export async function createAdventureRecord(payload: {
  adventure_id: string
  name: string
  world_name: string
  world_map_id: string | null
}): Promise<{ adventure: ServerAdventureEntry['adventure']; member: ServerAdventureEntry['member'] }> {
  const res = await authFetch(`${BASE}/adventures`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function deleteAdventureRecord(adventure_id: string): Promise<void> {
  const res = await authFetch(`${BASE}/adventures/${adventure_id}`, {
    method: 'DELETE',
  })
  if (!res.ok && res.status !== 204) throw new Error(await res.text())
}

export async function joinAdventure(invite_code: string): Promise<AdventureMeta> {
  const res = await authFetch(`${BASE}/adventures/join`, {
    method: 'POST',
    body: JSON.stringify({ invite_code }),
  })
  if (!res.ok) throw new Error(await res.text())
  const entry: ServerAdventureEntry = await res.json()
  return entryToMeta(entry)
}
