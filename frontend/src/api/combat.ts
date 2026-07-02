import type {
  Encounter, EncounterCreate, EncounterUpdate,
  Arena, ActionRecord,
  StartCombatRequest, PlayerTurnRequest, EndCombatRequest,
  TurnResult, EndCombatResult,
} from "../types/combat";

const BASE = "http://localhost:8000";

// ── Encounter CRUD ────────────────────────────────────────────────────────────

export async function createEncounter(payload: EncounterCreate): Promise<Encounter> {
  const res = await fetch(`${BASE}/encounters`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Encounter>;
}

export async function listEncounters(adventure_id: string, status?: string): Promise<Encounter[]> {
  const params = new URLSearchParams({ adventure_id });
  if (status) params.set("status", status);
  const res = await fetch(`${BASE}/encounters?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Encounter[]>;
}

export async function getEncounter(encounter_id: string): Promise<Encounter> {
  const res = await fetch(`${BASE}/encounters/${encounter_id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Encounter>;
}

export async function updateEncounter(
  encounter_id: string,
  payload: EncounterUpdate,
): Promise<Encounter> {
  const res = await fetch(`${BASE}/encounters/${encounter_id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Encounter>;
}

// ── Combat Flow ───────────────────────────────────────────────────────────────

export async function startCombat(
  encounter_id: string,
  payload: StartCombatRequest,
): Promise<Arena> {
  const res = await fetch(`${BASE}/encounters/${encounter_id}/start-combat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Arena>;
}

export async function getArena(encounter_id: string): Promise<Arena> {
  const res = await fetch(`${BASE}/encounters/${encounter_id}/arena`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Arena>;
}

export async function listActions(encounter_id: string): Promise<ActionRecord[]> {
  const res = await fetch(`${BASE}/encounters/${encounter_id}/actions`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<ActionRecord[]>;
}

export async function playerTurn(
  encounter_id: string,
  payload: PlayerTurnRequest,
): Promise<TurnResult> {
  const res = await fetch(`${BASE}/encounters/${encounter_id}/player-turn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<TurnResult>;
}

export async function npcTurn(encounter_id: string): Promise<TurnResult> {
  const res = await fetch(`${BASE}/encounters/${encounter_id}/npc-turn`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<TurnResult>;
}

export async function endCombat(
  encounter_id: string,
  payload: EndCombatRequest = {},
): Promise<EndCombatResult> {
  const res = await fetch(`${BASE}/encounters/${encounter_id}/end-combat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<EndCombatResult>;
}
