const BASE = "http://localhost:8000";

export interface ThemeExpansion {
  world_name: string;
  attribute_names: Record<string, string>;
  currency_name: string;
  biome_family_names: Record<string, string>;
}

// Read-only, non-persisting -- lets BasicInfoStep's custom-theme path pre-fill
// naming suggestions from a one-line pitch. Callers should treat failure as
// non-fatal and fall back to blank/default values (matches map preview's role).
export async function expandTheme(pitch: string): Promise<ThemeExpansion> {
  const res = await fetch(`${BASE}/theme/expand`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pitch }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<ThemeExpansion>;
}
