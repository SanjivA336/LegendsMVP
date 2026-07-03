import type { ComponentType } from 'react'

export interface MinigameProps {
  checkId: string
  skillName: string
  dieSize: number
  target: number | null
  advDisadv: number
  onComplete: (rawResult: Record<string, unknown>) => void
}

export interface Minigame {
  id: string
  component: ComponentType<MinigameProps>
}
