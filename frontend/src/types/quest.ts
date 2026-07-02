// Mirrors backend/models/event.py and backend/models/quest.py — keep in sync when fields change

// ── Event Types ───────────────────────────────────────────────────────────────

export type GameEventType =
  | "killed"
  | "acquired"
  | "delivered"
  | "reached"
  | "talked_to"
  | "survived";

export type QuestEventType =
  | "quest_created"
  | "quest_step_completed"
  | "quest_step_failed"
  | "quest_completed"
  | "quest_failed";

export type EventType = GameEventType | QuestEventType;

export interface EventCondition {
  type: GameEventType;
  entity_id?: string | null;
  item_id?: string | null;
  item_type?: string | null;
  poi_id?: string | null;
  tile_x?: number | null;
  tile_y?: number | null;
  encounter_id?: string | null;
  quantity?: number;
}

export interface FireEventRequest {
  adventure_id: string;
  type: EventType;
  entity_id?: string;
  item_id?: string;
  item_type?: string;
  poi_id?: string;
  tile_x?: number;
  tile_y?: number;
  encounter_id?: string;
  quest_id?: string;
}

export interface Event {
  id: string;
  adventure_id: string;
  type: EventType;
  entity_id: string | null;
  item_id: string | null;
  item_type: string | null;
  poi_id: string | null;
  tile_x: number | null;
  tile_y: number | null;
  encounter_id: string | null;
  quest_id: string | null;
}

export interface FireEventResult {
  event_id: string;
  quests_advanced: string[];
  quests_failed: string[];
}

// ── Quest Types ───────────────────────────────────────────────────────────────

export type QuestLength = "short" | "medium" | "long";
export type QuestStatus = "active" | "completed" | "failed";
export type StepStatus  = "pending" | "active" | "completed" | "failed";

export interface QuestStep {
  id: string;
  description: string;
  completion_condition: string;
  completion_event: EventCondition | null;
  failure_event: EventCondition | null;
  status: StepStatus;
  narrative_on_complete: string | null;
}

export interface Quest {
  id: string;
  adventure_id: string;
  title: string;
  length: QuestLength;
  status: QuestStatus;
  target_middle_count: number;
  first_step: QuestStep;
  last_step: QuestStep;
  middle_steps: QuestStep[];
}

export interface QuestCreate {
  adventure_id: string;
  length: QuestLength;
  context_hint?: string;
}

export interface QuestUpdate {
  status?: QuestStatus;
  title?: string;
}

export interface QuestStepUpdate {
  status?: StepStatus;
  narrative_on_complete?: string | null;
}

export interface ResolveStepRequest {
  recent_context: string;
  world_state_id: string;
}

export interface ResolveStepResult {
  quest: Quest;
  step_completed: boolean;
  narrative: string;
  quest_completed: boolean;
}
