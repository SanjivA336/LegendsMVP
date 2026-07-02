import type {
  ContextCard,
  WorldState,
  RelationshipEdge,
  RelationshipMap,
} from "../types/context";

const BASE = "http://localhost:8000";

// ── Context Cards ──────────────────────────────────────────────────────────────

export async function listContextCards(adventure_id: string): Promise<ContextCard[]> {
  const res = await fetch(`${BASE}/context-cards?adventure_id=${adventure_id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<ContextCard[]>;
}

export async function getContextCard(id: string): Promise<ContextCard> {
  const res = await fetch(`${BASE}/context-cards/${id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<ContextCard>;
}

export async function createContextCard(
  payload: Omit<ContextCard, "id">
): Promise<ContextCard> {
  const res = await fetch(`${BASE}/context-cards`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<ContextCard>;
}

export async function updateContextCard(
  id: string,
  updates: Partial<Omit<ContextCard, "id" | "adventure_id">>
): Promise<ContextCard> {
  const res = await fetch(`${BASE}/context-cards/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<ContextCard>;
}

export async function deleteContextCard(id: string): Promise<void> {
  const res = await fetch(`${BASE}/context-cards/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await res.text());
}

export async function getCardsForPrompt(
  adventure_id: string,
  options: { event?: string; recent_text?: string } = {}
): Promise<ContextCard[]> {
  const params = new URLSearchParams({ adventure_id });
  if (options.event) params.set("event", options.event);
  if (options.recent_text) params.set("recent_text", options.recent_text);
  const res = await fetch(`${BASE}/context-cards/for-prompt?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<ContextCard[]>;
}

// ── World State ────────────────────────────────────────────────────────────────

export async function listWorldStates(adventure_id: string): Promise<WorldState[]> {
  const res = await fetch(`${BASE}/world-state?adventure_id=${adventure_id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<WorldState[]>;
}

export async function createWorldState(
  payload: Omit<WorldState, "id" | "token_count">
): Promise<WorldState> {
  const res = await fetch(`${BASE}/world-state`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<WorldState>;
}

export async function appendWorldStateFacts(
  id: string,
  facts: string[]
): Promise<WorldState> {
  const res = await fetch(`${BASE}/world-state/${id}/facts`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ facts }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<WorldState>;
}

// ── Relationships ──────────────────────────────────────────────────────────────

export async function listRelationships(
  adventure_id: string,
  filters: { from_id?: string; to_id?: string } = {}
): Promise<RelationshipEdge[]> {
  const params = new URLSearchParams({ adventure_id });
  if (filters.from_id) params.set("from_id", filters.from_id);
  if (filters.to_id) params.set("to_id", filters.to_id);
  const res = await fetch(`${BASE}/relationships?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<RelationshipEdge[]>;
}

export async function getRelationshipMap(adventure_id: string): Promise<RelationshipMap> {
  const res = await fetch(`${BASE}/relationships/map?adventure_id=${adventure_id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<RelationshipMap>;
}

export async function createRelationship(
  payload: Omit<RelationshipEdge, "id">
): Promise<RelationshipEdge> {
  const res = await fetch(`${BASE}/relationships`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<RelationshipEdge>;
}

export async function updateRelationship(
  id: string,
  updates: Partial<Pick<RelationshipEdge, "affinity" | "fear" | "submission">>
): Promise<RelationshipEdge> {
  const res = await fetch(`${BASE}/relationships/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<RelationshipEdge>;
}

export async function deleteRelationship(id: string): Promise<void> {
  const res = await fetch(`${BASE}/relationships/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await res.text());
}

export async function rippleRelationship(payload: {
  adventure_id: string;
  from_id: string;
  to_id: string;
  weight: "affinity" | "fear" | "submission";
  delta: number;
}): Promise<RelationshipEdge[]> {
  const res = await fetch(`${BASE}/relationships/ripple`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<RelationshipEdge[]>;
}
