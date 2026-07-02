import { useQuery } from '@tanstack/react-query'
import { listCharacters, getInventory } from '../api/characters'

export function useParty(adventureId: string | null) {
  return useQuery({
    queryKey: ['party', adventureId],
    queryFn: () => listCharacters(adventureId!),
    enabled: !!adventureId,
  })
}

export function useInventory(characterId: string | null) {
  return useQuery({
    queryKey: ['inventory', characterId],
    queryFn: () => getInventory(characterId!),
    enabled: !!characterId,
  })
}
