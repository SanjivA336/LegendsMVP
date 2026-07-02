const BASE = "http://localhost:8000";

export interface NarratorActRequest {
  adventure_id: string;
  encounter_id?: string | null;
  player_text: string;
  character_id: string;
}

export interface NarratorActResponse {
  encounter_id: string;
  narrative: string;
}

export async function narratorAct(payload: NarratorActRequest): Promise<NarratorActResponse> {
  const res = await fetch(`${BASE}/narrator/act`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<NarratorActResponse>;
}

export interface OOCRequest {
  adventure_id: string;
  character_id: string;
  player_text: string;
  user_display_name?: string;
}

export async function oocChat(payload: OOCRequest): Promise<{ response: string }> {
  const res = await fetch(`${BASE}/narrator/ooc`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ response: string }>;
}
