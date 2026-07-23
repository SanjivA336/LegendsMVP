import { useQuery } from '@tanstack/react-query'
import { getRoundStatus, getRoundChecks } from '../api/narrator'

// Polling is the only cross-client sync mechanism in this app (no websockets) --
// a round can transition idle/resolved -> collecting from another player's action at
// any time, so round-status must never stop polling entirely. It backs off to a slow
// cadence at rest instead; the acting client invalidates this query itself on submit
// so backoff doesn't add latency for the person who just acted (see GamePage.tsx).
const ACTIVE_POLL_MS = 2000
const IDLE_POLL_MS = 10000

export function useRoundStatus(encounterId: string | null) {
  return useQuery({
    queryKey: ['round-status', encounterId],
    queryFn: () => getRoundStatus(encounterId!),
    enabled: !!encounterId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      const roundInFlight = status === 'collecting' || status === 'awaiting_checks' || status === 'resolving'
      return roundInFlight ? ACTIVE_POLL_MS : IDLE_POLL_MS
    },
    refetchIntervalInBackground: false,
  })
}

// Scoped by round_number, so a new round always starts a fresh query -- safe to stop
// entirely once a round's checks are all resolved (or there were never any).
export function usePendingChecks(encounterId: string | null, roundNumber: number) {
  return useQuery({
    queryKey: ['round-checks', encounterId, roundNumber],
    queryFn: () => getRoundChecks(encounterId!, roundNumber),
    enabled: !!encounterId && roundNumber > 0,
    refetchInterval: (query) => {
      const checks = query.state.data
      if (!checks) return ACTIVE_POLL_MS
      return checks.some((c) => c.status === 'pending') ? ACTIVE_POLL_MS : false
    },
    refetchIntervalInBackground: false,
  })
}
