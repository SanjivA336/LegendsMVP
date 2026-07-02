// Mirrors backend/models/poi.py — keep in sync when fields change

export type POIType = "settlement" | "encampment" | "dungeon" | "ruins";

export interface POI {
  id: string;
  adventure_id: string;
  map_id: string;
  tile_x: number;
  tile_y: number;
  type: POIType;
  tier: 1 | 2 | 3;
  detail_card_id: string | null;
  generated: boolean;
}

export interface POIUpdate {
  detail_card_id?: string | null;
  generated?: boolean;
}

// ── Dungeon ───────────────────────────────────────────────────────────────────

export type ExitDirection = "north" | "south" | "east" | "west" | "down" | "up";

export interface Exit {
  direction: ExitDirection;
  leads_to_room_id: string | null;
  leads_to_floor: number | null;
}

export interface Dungeon {
  id: string;
  adventure_id: string;
  poi_id: string | null;
  ruin_structure_id: string | null;
  floor_count: number;
  door_budget_per_floor: Record<string, number>;
  stairs_placed: Record<string, boolean>;
  floors_initialized: number[];
}

export interface DungeonRoom {
  id: string;
  adventure_id: string;
  dungeon_id: string;
  floor: number;
  x: number;
  y: number;
  is_entrance: boolean;
  is_boss_room: boolean;
  exits: Exit[];
  content: string[];
}

export interface DungeonRoomUpdate {
  exits?: Exit[];
  content?: string[];
}

// ── Settlement ────────────────────────────────────────────────────────────────

export interface SettlementLocation {
  id: string;
  name: string | null;
  detail_card_id: string | null;
}

export interface Settlement {
  id: string;
  adventure_id: string;
  poi_id: string;
  location_count: number;
  locations: SettlementLocation[];
  generated: boolean;
}

export interface SettlementUpdate {
  locations?: SettlementLocation[];
  generated?: boolean;
}

// ── Ruins ─────────────────────────────────────────────────────────────────────

export interface RuinStructure {
  id: string;
  label: string | null;
  floor_count: number;
  dungeon_id: string | null;
}

export interface Ruin {
  id: string;
  adventure_id: string;
  poi_id: string;
  structures: RuinStructure[];
  generated: boolean;
}

// ── Request bodies ────────────────────────────────────────────────────────────

export interface DiscoverRequest {
  adventure_id: string;
  map_id: string;
  tile_x: number;
  tile_y: number;
}

export interface EnterRequest {
  adventure_id: string;
  poi_id: string;
}

export interface ExploreRequest {
  from_room_id: string;
  direction: ExitDirection;
}

export interface SettlementEnterRequest {
  adventure_id: string;
  poi_id: string;
}

export interface RuinEnterRequest {
  adventure_id: string;
  poi_id: string;
}
