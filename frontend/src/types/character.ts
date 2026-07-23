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
  equipped_wearable_ids: string[];
  inventory_ids: string[];
  description: string;
  tone: string;
  metadata: Record<string, unknown>;
  race_instance_id: string | null;   // a kind="race" Instance id -- resolve via
  class_instance_id: string | null;  // GET /instances/{id} to display its name
}

// Inventory resolves item IDs into full merged items
export type CharacterInventory = ResolvedItemInstance[];
