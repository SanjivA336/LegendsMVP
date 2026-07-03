// Mirrors backend/models/combat.py — keep in sync when fields change

// ── AI Component Types ─────────────────────────────────────────────────────────

export type MovementType     = "ground" | "air" | "sea" | "teleport";
export type TargetSelection  = "closest" | "furthest" | "strongest" | "weakest" | "last_assailant" | "random";
export type IntelligenceType = "drone" | "beast" | "lurker" | "soldier" | "alpha";

export interface AIProfile {
  movement_type: MovementType;
  preferred_distance: number;
  target_selection: TargetSelection;
  intelligence: IntelligenceType;
  last_assailant_id: string | null;
}

// ── Tile System ───────────────────────────────────────────────────────────────

export interface ArenaTile {
  passable: boolean;
  terrain_tag: string;
  elevation: number;
  movement_cost: number;
  aura: string | null;
  hazard: number;
  /** [N, E, S, W] — 0=open, 1=cover, 2=barrier, 3=sealed */
  edges: [number, number, number, number];
}

// ── Arena Objects ─────────────────────────────────────────────────────────────

export type ArenaObjectType = "bulwark" | "cache";

export interface ArenaObject {
  id: string;
  x: number;
  y: number;
  object_type: ArenaObjectType;
  item_ids: string[];
  looted: boolean;
}

// ── Arena Combatant ───────────────────────────────────────────────────────────

export interface ArenaCombatant {
  id: string;
  x: number;
  y: number;
  team: number;
  hp: number;
  max_hp: number;
  stats: Record<string, number>;
  equipped_weapon_id: string | null;
  ai_profile: AIProfile | null;
  status: string[];
}

// ── Arena ─────────────────────────────────────────────────────────────────────

export interface Arena {
  id: string;
  encounter_id: string;
  adventure_id: string;
  width: number;
  height: number;
  indoor: boolean;
  /** Row-major: tiles[y][x] */
  tiles: ArenaTile[][];
  objects: ArenaObject[];
  combatants: ArenaCombatant[];
  turn_order: string[];
  current_turn_idx: number;
  round: number;
  teams: Record<string, number>;
  persisted: boolean;
}

// ── Persisted Models ──────────────────────────────────────────────────────────

export type EncounterStatus = "pending" | "active" | "completed" | "fled";

export interface Encounter {
  id: string;
  adventure_id: string;
  mode: string;
  location_id: string | null;
  stage_ids: string[];
  action_ids: string[];
  status: EncounterStatus;
  arena_id: string | null;
}

export interface EncounterCreate {
  adventure_id: string;
  mode?: string;
  location_id?: string | null;
  stage_ids?: string[];
}

export interface EncounterUpdate {
  stage_ids?: string[];
  status?: EncounterStatus;
}

export interface ActionRecord {
  id: string;
  adventure_id: string;
  encounter_id: string;
  actor_id: string;
  action_type: string;
  target_id: string | null;
  description: string;
  dice_results: number[];
  outcome: string;
  narrative: string;
  round_number: number;
  sequence: number;
  display_name: string | null;
  speech: string | null;
  action_text: string | null;
}

// ── Request / Response Bodies ─────────────────────────────────────────────────

export interface StartCombatRequest {
  teams: Record<string, number>;
  arena_width?: number;
  arena_height?: number;
  indoor?: boolean;
}

export type PlayerActionType = "move" | "attack" | "use_item" | "loot" | "end_turn";

export interface PlayerTurnRequest {
  actor_id: string;
  action_type: PlayerActionType;
  target_id?: string | null;
  to_x?: number | null;
  to_y?: number | null;
  item_id?: string | null;
  object_id?: string | null;
  stat_key?: string;
  dc_stat_key?: string;
}

export interface EndCombatRequest {
  outcome?: "completed" | "fled";
}

export interface TurnResult {
  arena: Arena;
  action: ActionRecord;
  killed: string[];
  quests_advanced: string[];
  combat_ended: boolean;
  combat_outcome: string | null;
  narrative: string;
  looted_items: string[];
}

export interface EndCombatResult {
  narrative: string;
  encounter_id: string;
  outcome: string;
}
