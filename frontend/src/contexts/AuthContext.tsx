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
import { fetchAdventures } from '../api/adventures'
import { useGameStore } from '../store/gameStore'
import { darkenHex } from '../utils/color'

// Keep in sync with index.css's --color-accent default
const DEFAULT_ACCENT = '#F8961E'

export interface UserPreferences {
  accentColor: string | null
  playerColors: string[] | null
}

const DEFAULT_PREFERENCES: UserPreferences = { accentColor: null, playerColors: null }

interface AuthState {
  user: User | null
  loading: boolean
  displayName: string | null
  preferences: UserPreferences
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string, displayName: string) => Promise<void>
  signOut: () => Promise<void>
  updateDisplayName: (name: string) => Promise<void>
  updatePreferences: (prefs: UserPreferences) => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [displayName, setDisplayName] = useState<string | null>(null)
  const [preferences, setPreferences] = useState<UserPreferences>(DEFAULT_PREFERENCES)
  const setAdventures = useGameStore((s) => s.setAdventures)

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, async (firebaseUser) => {
      setUser(firebaseUser)
      if (firebaseUser) {
        try {
          const res = await authFetch(`${BASE}/users/me`)
          if (res.ok) {
            const data = await res.json()
            setDisplayName(data.display_name ?? null)
            setPreferences({
              accentColor: data.preferences?.accent_color ?? null,
              playerColors: data.preferences?.player_colors ?? null,
            })
          }
        } catch {
          // Non-fatal: user doc may not exist yet
        }
        try {
          setAdventures(await fetchAdventures())
        } catch {
          // Non-fatal: adventures list will retry via AdventureListPage's own fetch
        }
      } else {
        setDisplayName(null)
        setPreferences(DEFAULT_PREFERENCES)
      }
      setLoading(false)
    })
    return unsub
  }, [setAdventures])

  useEffect(() => {
    const root = document.documentElement.style
    const accent = preferences.accentColor ?? DEFAULT_ACCENT
    const hover = darkenHex(accent, 0.12)
    root.setProperty('--color-accent', accent)
    root.setProperty('--color-accent-hover', hover)
    root.setProperty('--accent', accent)
    root.setProperty('--accent-hover', hover)
  }, [preferences.accentColor])

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
    setPreferences(DEFAULT_PREFERENCES)
  }

  async function updateDisplayName(name: string) {
    await authFetch(`${BASE}/users/me`, {
      method: 'POST',
      body: JSON.stringify({ display_name: name }),
    })
    setDisplayName(name)
  }

  async function updatePreferences(prefs: UserPreferences) {
    await authFetch(`${BASE}/users/me`, {
      method: 'POST',
      body: JSON.stringify({
        preferences: { accent_color: prefs.accentColor, player_colors: prefs.playerColors },
      }),
    })
    setPreferences(prefs)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        displayName,
        preferences,
        signIn,
        signUp,
        signOut,
        updateDisplayName,
        updatePreferences,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
