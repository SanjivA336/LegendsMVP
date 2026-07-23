// Items now live on the generic kind-tagged Template/Instance system (backend/models/blueprint.py)
// rather than their own dedicated collections. This file keeps its old exported function
// names/signatures and the old ItemTemplate/ItemInstance/ResolvedItemInstance shapes (nothing
// currently calls these functions, but other code still imports the *types*), translating
// to/from the new /templates and /instances endpoints internally.

import type { ItemTemplate, ItemInstance, ResolvedItemInstance } from "../types/item";
import type { CustomField, Template, Instance, ResolvedInstance } from "../types/blueprint";

const BASE = "http://localhost:8000";

function propertiesToFields(properties: Record<string, number>): CustomField[] {
  return Object.entries(properties).map(([key, value]) => ({
    key, label: key, field_type: "number", value,
    is_enum: false, options: [], required: false, bound_behavior: null, hidden: false,
  }));
}

function fieldsToProperties(fields: CustomField[]): Record<string, number> {
  const properties: Record<string, number> = {};
  for (const f of fields) {
    if (typeof f.value === "number") properties[f.key] = f.value;
  }
  return properties;
}

function templateToItemTemplate(t: Template): ItemTemplate {
  return {
    id: t.id, adventure_id: t.adventure_id, name: t.name, description: t.description,
    tags: t.tags, properties: fieldsToProperties(t.fields), metadata: t.metadata,
  };
}

function instanceToItemInstance(i: Instance): ItemInstance {
  return {
    id: i.id, adventure_id: i.adventure_id, template_id: i.template_id ?? "",
    owner_id: i.owner_id, overrides: fieldsToProperties(i.fields), notes: i.notes,
  };
}

function resolvedToResolvedItemInstance(r: ResolvedInstance): ResolvedItemInstance {
  return {
    id: r.id, adventure_id: r.adventure_id, template_id: r.template_id ?? "",
    owner_id: r.owner_id, notes: r.notes,
    name: r.name, description: r.description, tags: r.tags,
    properties: fieldsToProperties(r.fields), metadata: r.metadata,
  };
}

// ── Templates ──────────────────────────────────────────────────────────────────

export async function listTemplates(adventure_id: string): Promise<ItemTemplate[]> {
  const res = await fetch(`${BASE}/templates?adventure_id=${adventure_id}&kind=custom`);
  if (!res.ok) throw new Error(await res.text());
  const templates = (await res.json()) as Template[];
  return templates.map(templateToItemTemplate);
}

export async function getTemplate(id: string): Promise<ItemTemplate> {
  const res = await fetch(`${BASE}/templates/${id}`);
  if (!res.ok) throw new Error(await res.text());
  return templateToItemTemplate((await res.json()) as Template);
}

export async function createTemplate(
  payload: Omit<ItemTemplate, "id">
): Promise<ItemTemplate> {
  const res = await fetch(`${BASE}/templates`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      adventure_id: payload.adventure_id, kind: "custom", name: payload.name,
      description: payload.description, tags: payload.tags,
      fields: propertiesToFields(payload.properties), metadata: payload.metadata,
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return templateToItemTemplate((await res.json()) as Template);
}

// ── Instances ──────────────────────────────────────────────────────────────────

export async function getInstance(id: string): Promise<ResolvedItemInstance> {
  // Always returns the merged (resolved) form
  const res = await fetch(`${BASE}/instances/${id}`);
  if (!res.ok) throw new Error(await res.text());
  return resolvedToResolvedItemInstance((await res.json()) as ResolvedInstance);
}

export async function listInstances(filters: {
  owner_id?: string;
  adventure_id?: string;
}): Promise<ItemInstance[]> {
  const params = new URLSearchParams(
    Object.fromEntries(Object.entries(filters).filter(([, v]) => v != null)) as Record<string, string>
  );
  const res = await fetch(`${BASE}/instances?${params}`);
  if (!res.ok) throw new Error(await res.text());
  const instances = (await res.json()) as Instance[];
  return instances.map(instanceToItemInstance);
}

export async function createInstance(
  payload: Omit<ItemInstance, "id">
): Promise<ItemInstance> {
  const res = await fetch(`${BASE}/instances`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      adventure_id: payload.adventure_id, kind: "custom", template_id: payload.template_id,
      owner_id: payload.owner_id, fields: propertiesToFields(payload.overrides), notes: payload.notes,
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return instanceToItemInstance((await res.json()) as Instance);
}

export async function updateInstance(
  id: string,
  updates: Partial<Pick<ItemInstance, "owner_id" | "overrides" | "notes">>
): Promise<ItemInstance> {
  const body: Record<string, unknown> = {};
  if (updates.owner_id !== undefined) body.owner_id = updates.owner_id;
  if (updates.overrides !== undefined) body.fields = propertiesToFields(updates.overrides);
  if (updates.notes !== undefined) body.notes = updates.notes;

  const res = await fetch(`${BASE}/instances/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return instanceToItemInstance((await res.json()) as Instance);
}
