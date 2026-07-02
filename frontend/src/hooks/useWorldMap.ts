import { useQuery } from '@tanstack/react-query'
import { getWorldMap } from '../api/world'

export function useWorldMap(mapId: string | null) {
  return useQuery({
    queryKey: ['world-map', mapId],
    queryFn: () => getWorldMap(mapId!),
    enabled: !!mapId,
    staleTime: 5 * 60_000,
  })
}
