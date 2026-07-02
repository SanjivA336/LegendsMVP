import { useQuery } from '@tanstack/react-query'
import { getArena, listActions } from '../api/combat'

export function useArena(encounterId: string | null) {
  return useQuery({
    queryKey: ['arena', encounterId],
    queryFn: () => getArena(encounterId!),
    enabled: !!encounterId,
    refetchInterval: false,
  })
}

export function useActionLog(encounterId: string | null) {
  return useQuery({
    queryKey: ['action-log', encounterId],
    queryFn: () => listActions(encounterId!),
    enabled: !!encounterId,
  })
}
