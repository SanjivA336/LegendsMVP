import { authFetch, BASE } from './apiClient'

export interface Actor {
  id: string
  owner_uid: string
  name: string
  stance: number
  tactics: number
  disposition: number
  description: string
}

export interface ActorSlot {
  id: string
  adventure_id: string
  actor_id: string
  character_id: string | null
  owner_uid: string
  added_at: string
}

export async function fetchActors(): Promise<Actor[]> {
  const res = await authFetch(`${BASE}/actors`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function createActor(payload: Omit<Actor, 'id' | 'owner_uid'>): Promise<Actor> {
  const res = await authFetch(`${BASE}/actors`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function fetchActorSlots(adventure_id: string): Promise<ActorSlot[]> {
  const res = await authFetch(`${BASE}/adventures/${adventure_id}/actor-slots`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function addActorSlot(adventure_id: string, actor_id: string): Promise<ActorSlot> {
  const res = await authFetch(`${BASE}/adventures/${adventure_id}/actor-slots`, {
    method: 'POST',
    body: JSON.stringify({ actor_id }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function removeActorSlot(adventure_id: string, slot_id: string): Promise<void> {
  const res = await authFetch(`${BASE}/adventures/${adventure_id}/actor-slots/${slot_id}`, {
    method: 'DELETE',
  })
  if (!res.ok && res.status !== 204) throw new Error(await res.text())
}
