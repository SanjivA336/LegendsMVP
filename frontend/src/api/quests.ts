import type {
  Quest, QuestCreate, QuestUpdate, QuestStep, QuestStepUpdate,
  ResolveStepRequest, ResolveStepResult,
  Event, FireEventRequest, FireEventResult,
} from "../types/quest";

const BASE = "http://localhost:8000";

// ── Quests ────────────────────────────────────────────────────────────────────

export async function createQuest(payload: QuestCreate): Promise<Quest> {
  const res = await fetch(`${BASE}/quests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Quest>;
}

export async function listQuests(adventure_id: string, status?: string): Promise<Quest[]> {
  const params = new URLSearchParams({ adventure_id });
  if (status) params.set("status", status);
  const res = await fetch(`${BASE}/quests?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Quest[]>;
}

export async function getQuest(quest_id: string): Promise<Quest> {
  const res = await fetch(`${BASE}/quests/${quest_id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Quest>;
}

export async function updateQuest(quest_id: string, payload: QuestUpdate): Promise<Quest> {
  const res = await fetch(`${BASE}/quests/${quest_id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Quest>;
}

export async function deleteQuest(quest_id: string): Promise<void> {
  const res = await fetch(`${BASE}/quests/${quest_id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await res.text());
}

export async function getActiveStep(quest_id: string): Promise<QuestStep> {
  const res = await fetch(`${BASE}/quests/${quest_id}/active-step`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<QuestStep>;
}

export async function resolveStep(
  quest_id: string,
  payload: ResolveStepRequest,
): Promise<ResolveStepResult> {
  const res = await fetch(`${BASE}/quests/${quest_id}/resolve-step`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<ResolveStepResult>;
}

export async function failStep(quest_id: string): Promise<Quest> {
  const res = await fetch(`${BASE}/quests/${quest_id}/fail-step`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Quest>;
}

export async function updateStep(
  quest_id: string,
  step_id: string,
  payload: QuestStepUpdate,
): Promise<Quest> {
  const res = await fetch(`${BASE}/quests/${quest_id}/steps/${step_id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Quest>;
}

// ── Events ────────────────────────────────────────────────────────────────────

export async function fireEvent(payload: FireEventRequest): Promise<FireEventResult> {
  const res = await fetch(`${BASE}/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<FireEventResult>;
}

export async function listEvents(adventure_id: string, type?: string): Promise<Event[]> {
  const params = new URLSearchParams({ adventure_id });
  if (type) params.set("type", type);
  const res = await fetch(`${BASE}/events?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Event[]>;
}
