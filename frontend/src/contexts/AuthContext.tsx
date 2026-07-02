import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut as firebaseSignOut,
  type User,
} from 'firebase/auth'
import { auth } from '../firebase'
import { authFetch, BASE } from '../api/apiClient'

interface AuthState {
  user: User | null
  loading: boolean
  displayName: string | null
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string, displayName: string) => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [displayName, setDisplayName] = useState<string | null>(null)

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, async (firebaseUser) => {
      setUser(firebaseUser)
      if (firebaseUser) {
        try {
          const res = await authFetch(`${BASE}/users/me`)
          if (res.ok) {
            const data = await res.json()
            setDisplayName(data.display_name ?? null)
          }
        } catch {
          // Non-fatal: user doc may not exist yet
        }
      } else {
        setDisplayName(null)
      }
      setLoading(false)
    })
    return unsub
  }, [])

  async function signIn(email: string, password: string) {
    await signInWithEmailAndPassword(auth, email, password)
  }

  async function signUp(email: string, password: string, displayNameInput: string) {
    await createUserWithEmailAndPassword(auth, email, password)
    await authFetch(`${BASE}/users/me`, {
      method: 'POST',
      body: JSON.stringify({ display_name: displayNameInput }),
    })
    setDisplayName(displayNameInput)
  }

  async function signOut() {
    await firebaseSignOut(auth)
    setDisplayName(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, displayName, signIn, signUp, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
