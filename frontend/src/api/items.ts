import type { ItemTemplate, ItemInstance, ResolvedItemInstance } from "../types/item";

const BASE = "http://localhost:8000";

// ── Templates ──────────────────────────────────────────────────────────────────

export async function listTemplates(adventure_id: string): Promise<ItemTemplate[]> {
  const res = await fetch(`${BASE}/item-templates?adventure_id=${adventure_id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<ItemTemplate[]>;
}

export async function getTemplate(id: string): Promise<ItemTemplate> {
  const res = await fetch(`${BASE}/item-templates/${id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<ItemTemplate>;
}

export async function createTemplate(
  payload: Omit<ItemTemplate, "id">
): Promise<ItemTemplate> {
  const res = await fetch(`${BASE}/item-templates`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<ItemTemplate>;
}

// ── Instances ──────────────────────────────────────────────────────────────────

export async function getInstance(id: string): Promise<ResolvedItemInstance> {
  // Always returns the merged (resolved) form
  const res = await fetch(`${BASE}/item-instances/${id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<ResolvedItemInstance>;
}

export async function listInstances(filters: {
  owner_id?: string;
  adventure_id?: string;
}): Promise<ItemInstance[]> {
  const params = new URLSearchParams(
    Object.fromEntries(Object.entries(filters).filter(([, v]) => v != null)) as Record<string, string>
  );
  const res = await fetch(`${BASE}/item-instances?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<ItemInstance[]>;
}

export async function createInstance(
  payload: Omit<ItemInstance, "id">
): Promise<ItemInstance> {
  const res = await fetch(`${BASE}/item-instances`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<ItemInstance>;
}

export async function updateInstance(
  id: string,
  updates: Partial<Pick<ItemInstance, "owner_id" | "overrides" | "notes">>
): Promise<ItemInstance> {
  const res = await fetch(`${BASE}/item-instances/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<ItemInstance>;
}
