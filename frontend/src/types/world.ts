// Mirrors backend/models/world.py and backend/utils/biomes.py — keep in sync when fields change

export interface Tile {
  x: number;
  y: number;
  elevation: number;         // 0.0–1.0
  is_water: boolean;
  biome_id: number | null;
  biome_name: string | null;
  tier: 1 | 2 | 3 | null;
  poi_candidate: boolean;
  poi_id: string | null;
}

export interface WorldMap {
  id: string;
  adventure_id: string;
  width: number;
  height: number;
  seed: number;
  tiles: Tile[];
  spawn_tile_x: number;
  spawn_tile_y: number;
}

export interface WorldMapMeta {
  id: string;
  adventure_id: string;
  width: number;
  height: number;
  seed: number;
}

export interface BiomeInfo {
  id: number;
  name: string;
  tier: number;
  family: string;
}

export interface BiomeGraph {
  biomes: Record<string, BiomeInfo>;
  transitions: Record<string, number[]>;
}
