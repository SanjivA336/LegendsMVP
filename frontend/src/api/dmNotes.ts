import { authFetch, BASE } from './apiClient'

export interface DmNotes {
  adventure_id: string
  public_notes: string
  updated_at: string
}

export async function fetchDmNotes(adventure_id: string): Promise<DmNotes> {
  const res = await authFetch(`${BASE}/adventures/${adventure_id}/dm-notes`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function updateDmNotes(adventure_id: string, public_notes: string): Promise<DmNotes> {
  const res = await authFetch(`${BASE}/adventures/${adventure_id}/dm-notes`, {
    method: 'PATCH',
    body: JSON.stringify({ public_notes }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
