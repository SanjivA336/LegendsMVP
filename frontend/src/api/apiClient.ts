import { auth } from '../firebase'

export const BASE = 'http://localhost:8000'

export async function authFetch(url: string, options?: RequestInit): Promise<Response> {
  const token = await auth.currentUser?.getIdToken()
  return fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
}
