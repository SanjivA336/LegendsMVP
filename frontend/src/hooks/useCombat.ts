import { useQuery } from '@tanstack/react-query'
import { getArena, listActions, getEncounter } from '../api/combat'

export function useArena(encounterId: string | null) {
  return useQuery({
    queryKey: ['arena', encounterId],
    queryFn: () => getArena(encounterId!),
    enabled: !!encounterId,
    refetchInterval: false,
  })
}

export function useEncounter(encounterId: string | null) {
  return useQuery({
    queryKey: ['encounter', encounterId],
    queryFn: () => getEncounter(encounterId!),
    enabled: !!encounterId,
  })
}

export function useActionLog(encounterId: string | null) {
  return useQuery({
    queryKey: ['action-log', encounterId],
    queryFn: async () => {
      const actions = await listActions(encounterId!)
      return [...actions].sort((a, b) =>
        a.round_number - b.round_number || a.sequence - b.sequence
      )
    },
    enabled: !!encounterId,
  })
}
