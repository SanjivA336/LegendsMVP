const BASE = "http://localhost:8000";

export interface WorldBibleCreate {
  adventure_id: string;
  attribute_names: Record<string, string>;
  currency_name: string;
  biome_name_overrides?: Record<string, string>;
}

export interface WorldBible {
  id: string;
  adventure_id: string;
  attribute_names: Record<string, string>;
  currency_name: string;
}

export async function createWorldBible(payload: WorldBibleCreate): Promise<WorldBible> {
  const res = await fetch(`${BASE}/world-bible`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<WorldBible>;
}

export interface OpeningSceneRequest {
  adventure_id: string;
  character_name: string;
  world_name: string;
}

export async function generateOpeningScene(payload: OpeningSceneRequest): Promise<{ narrative: string }> {
  const res = await fetch(`${BASE}/narrator/open`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ narrative: string }>;
}
