import type { Minigame } from './types'
import DiceRollMinigame from './DiceRollMinigame'

// Adding a new minigame is: write its component (matching MinigameProps), add one entry here.
// Nothing else in the app needs to change.
export const MINIGAMES: Record<string, Minigame> = {
  'dice-roll': { id: 'dice-roll', component: DiceRollMinigame },
}
