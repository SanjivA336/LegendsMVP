import { useQuery } from '@tanstack/react-query'
import { getResolvedInstance } from '../api/entities'

export function useResolvedInstance(instanceId: string | null) {
  return useQuery({
    queryKey: ['instance', instanceId],
    queryFn: () => getResolvedInstance(instanceId!),
    enabled: !!instanceId,
  })
}
