import { useAuth } from '../contexts/AuthContext'
import { PLAYER_COLORS } from '../constants/colors'

export function usePlayerColors(): string[] {
  const { preferences } = useAuth()
  return preferences.playerColors ?? PLAYER_COLORS
}
