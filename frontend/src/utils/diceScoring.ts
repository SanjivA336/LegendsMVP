// Mirrors backend/utils/minigames/dice.py — keep in sync when tier logic changes.

export const TIER_COLORS: Record<string, string> = {
  'Critical Failure': '#E63946',
  'Major Failure': '#F8961E',
  'Failure': '#F5D547',
  'Success': '#4CAF50',
  'Major Success': '#4CC9F0',
  'Critical Success': '#9B5DE5',
}

export function tierLabelForRoll(roll: number, target: number, dieSize: number): string {
  if (roll <= 1) return 'Critical Failure'
  if (roll >= dieSize) return 'Critical Success'
  if (roll < target) {
    const mid = (1 + target) / 2
    return roll <= mid ? 'Major Failure' : 'Failure'
  }
  const mid = (target + dieSize) / 2
  return roll >= mid ? 'Major Success' : 'Success'
}
