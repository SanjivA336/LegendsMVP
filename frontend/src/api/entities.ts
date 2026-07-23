import type {
  Kind, Template, Instance, ResolvedInstance, CustomField, TemplateCreate, InstanceCreate,
} from "../types/blueprint";

const BASE = "http://localhost:8000";

export async function listTemplates(adventure_id: string, kind?: Kind): Promise<Template[]> {
  const params = new URLSearchParams({ adventure_id, ...(kind ? { kind } : {}) });
  const res = await fetch(`${BASE}/templates?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Template[]>;
}

export async function getTemplateDefaultFields(kind: Kind): Promise<CustomField[]> {
  const res = await fetch(`${BASE}/templates/default-fields?kind=${kind}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<CustomField[]>;
}

export async function createTemplate(payload: TemplateCreate): Promise<Template> {
  const res = await fetch(`${BASE}/templates`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Template>;
}

export async function createInstance(payload: InstanceCreate): Promise<Instance> {
  const res = await fetch(`${BASE}/instances`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Instance>;
}

export async function listInstances(adventure_id: string, kind?: Kind): Promise<Instance[]> {
  const params = new URLSearchParams({ adventure_id, ...(kind ? { kind } : {}) });
  const res = await fetch(`${BASE}/instances?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Instance[]>;
}

export async function getResolvedInstance(id: string): Promise<ResolvedInstance> {
  const res = await fetch(`${BASE}/instances/${id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<ResolvedInstance>;
}

export async function seedStarterContent(
  adventure_id: string
): Promise<{ race_template_ids: string[]; class_template_ids: string[] }> {
  const res = await fetch(`${BASE}/templates/seed-starter-content`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ adventure_id }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
