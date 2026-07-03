import type {
  RoundSubmitRequest, RoundSubmitResponse, RoundStatusResponse, PendingCheck, ResolveCheckResponse,
} from '../types/round'

const BASE = "http://localhost:8000";

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

export async function submitRoundAction(payload: RoundSubmitRequest): Promise<RoundSubmitResponse> {
  const res = await fetch(`${BASE}/narrator/round/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<RoundSubmitResponse>;
}

export async function getRoundStatus(encounterId: string): Promise<RoundStatusResponse> {
  const res = await fetch(`${BASE}/narrator/round-status?encounter_id=${encodeURIComponent(encounterId)}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<RoundStatusResponse>;
}

export async function forceResolveRound(encounterId: string): Promise<RoundSubmitResponse> {
  const res = await fetch(`${BASE}/narrator/round/force-resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ encounter_id: encounterId }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<RoundSubmitResponse>;
}

export async function getRoundChecks(encounterId: string, roundNumber: number): Promise<PendingCheck[]> {
  const params = new URLSearchParams({ encounter_id: encounterId, round_number: String(roundNumber) });
  const res = await fetch(`${BASE}/narrator/round-checks?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<PendingCheck[]>;
}

export async function resolveCheck(
  checkId: string, rawResult: Record<string, unknown>
): Promise<ResolveCheckResponse> {
  const res = await fetch(`${BASE}/narrator/round/resolve-check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ check_id: checkId, raw_result: rawResult }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<ResolveCheckResponse>;
}
