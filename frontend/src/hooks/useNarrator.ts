import { useQuery } from '@tanstack/react-query'
import { getRoundStatus, getRoundChecks } from '../api/narrator'

export function useRoundStatus(encounterId: string | null) {
  return useQuery({
    queryKey: ['round-status', encounterId],
    queryFn: () => getRoundStatus(encounterId!),
    enabled: !!encounterId,
    refetchInterval: 2000,
    refetchIntervalInBackground: false,
  })
}

export function usePendingChecks(encounterId: string | null, roundNumber: number) {
  return useQuery({
    queryKey: ['round-checks', encounterId, roundNumber],
    queryFn: () => getRoundChecks(encounterId!, roundNumber),
    enabled: !!encounterId && roundNumber > 0,
    refetchInterval: 2000,
    refetchIntervalInBackground: false,
  })
}
