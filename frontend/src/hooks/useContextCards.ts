import { useQuery } from '@tanstack/react-query'
import { listContextCards } from '../api/context'
import { listRelationships } from '../api/context'

export function useContextCards(adventureId: string | null) {
  return useQuery({
    queryKey: ['context-cards', adventureId],
    queryFn: () => listContextCards(adventureId!),
    enabled: !!adventureId,
  })
}

export function useRelationships(adventureId: string | null) {
  return useQuery({
    queryKey: ['relationships', adventureId],
    queryFn: () => listRelationships(adventureId!),
    enabled: !!adventureId,
  })
}
