// Mirrors backend/models/round.py — keep in sync when fields change

export type ParticipantKind = "human" | "actor";
export type EntryStatus = "awaiting" | "submitted" | "passed";
export type RoundStatus = "idle" | "collecting" | "awaiting_checks" | "resolving" | "resolved";

export interface RoundSubmitRequest {
  adventure_id: string;
  encounter_id?: string | null;
  character_id: string;
  player_text?: string | null;
  passed?: boolean;
}

export interface RoundSubmitResponse {
  encounter_id: string;
  round_number: number;
  resolved: boolean;
  narrative: string | null;
}

export interface RoundEntryView {
  character_id: string;
  character_name: string;
  kind: ParticipantKind;
  status: EntryStatus;
}

export interface RoundStatusResponse {
  encounter_id: string;
  round_number: number;
  status: RoundStatus;
  entries: RoundEntryView[];
  narrative: string | null;
  resolved_at: string | null;
}

export type CheckStatus = "pending" | "resolved";

export interface PendingCheck {
  id: string;
  encounter_id: string;
  round_number: number;
  character_id: string;
  character_name: string;
  skill_key: string;
  skill_name: string;
  minigame_id: string;
  show_target: boolean;
  target: number | null;
  adv_disadv: number;
  die_size: number;
  status: CheckStatus;
  raw_result: Record<string, unknown> | null;
  score: number | null;
}

export interface ResolveCheckResponse {
  check_id: string;
  score: number;
  resolved_round: boolean;
  narrative: string | null;
}
