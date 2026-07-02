// Mirrors backend/models/character.py — keep in sync when fields change
import type { ResolvedItemInstance } from "./item";

export interface Stats {
  strength: number;
  dexterity: number;
  intelligence: number;
  fortitude: number;
  charisma: number;
  reflex: number;
}

export interface Character {
  id: string;
  adventure_id: string;
  name: string;
  is_player: boolean;
  hp: number;
  max_hp: number;
  stats: Stats;
  equipped_weapon_id: string | null;
  inventory_ids: string[];
  description: string;
  tone: string;
  metadata: Record<string, unknown>;
}

// Inventory resolves item IDs into full merged items
export type CharacterInventory = ResolvedItemInstance[];
