import type { Character, CharacterInventory } from "../types/character";
import type { CustomField } from "../types/blueprint";

const BASE = "http://localhost:8000";

export async function listCharacters(adventure_id: string): Promise<Character[]> {
  const res = await fetch(`${BASE}/characters?adventure_id=${adventure_id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Character[]>;
}

export async function getCharacter(id: string): Promise<Character> {
  const res = await fetch(`${BASE}/characters/${id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Character>;
}

export async function createCharacter(
  payload: Omit<Character, "id" | "hp" | "max_hp" | "race_instance_id" | "class_instance_id" | "equipped_wearable_ids"> & {
    hp?: number;
    max_hp?: number;
    race_template_id?: string | null;   // chosen from a kind="race" Template; the backend
    class_template_id?: string | null;  // creates and attaches a fresh Instance of it
    custom_fields?: CustomField[];             // values for a DM-authored character template's
                                                // non-canonical fields (snapshotted in, not linked)
    starting_inventory_ids?: string[];         // unowned Instance ids to claim
    starting_equipped_wearable_ids?: string[]; // subset of the above -- what ends up worn
  }
): Promise<Character> {
  const res = await fetch(`${BASE}/characters`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Character>;
}

export async function getInventory(character_id: string): Promise<CharacterInventory> {
  const res = await fetch(`${BASE}/characters/${character_id}/inventory`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<CharacterInventory>;
}

export async function equipItem(character_id: string, item_id: string): Promise<Character> {
  const res = await fetch(`${BASE}/characters/${character_id}/equip/${item_id}`, { method: "PATCH" });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Character>;
}

export async function unequipItem(character_id: string): Promise<Character> {
  const res = await fetch(`${BASE}/characters/${character_id}/unequip`, { method: "PATCH" });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Character>;
}

export async function updateCharacter(
  id: string,
  updates: Partial<Omit<Character, "id" | "adventure_id">>
): Promise<Character> {
  const res = await fetch(`${BASE}/characters/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Character>;
}
