import type { Character, CharacterInventory } from "../types/character";

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
  payload: Omit<Character, "id" | "hp" | "max_hp"> & { hp?: number; max_hp?: number }
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
