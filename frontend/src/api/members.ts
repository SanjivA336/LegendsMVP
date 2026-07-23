import { authFetch, BASE } from './apiClient'

export async function updateMember(
  adventure_id: string,
  member_id: string,
  patch: { role?: 'admin' | 'player' | 'viewer'; character_id?: string }
): Promise<{ id: string; adventure_id: string; user_uid: string; role: string; character_id: string | null; joined_at: string }> {
  const res = await authFetch(`${BASE}/adventures/${adventure_id}/members/${member_id}`, {
    method: 'PATCH',
    body: JSON.stringify(patch),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
