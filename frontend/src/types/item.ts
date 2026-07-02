// Mirrors backend/models/item.py — keep in sync when fields change

export interface ItemTemplate {
  id: string;
  adventure_id: string;
  name: string;
  description: string;
  tags: string[];
  properties: Record<string, number>;
  metadata: Record<string, unknown>;
}

export interface ItemInstance {
  id: string;
  adventure_id: string;
  template_id: string;
  owner_id: string | null;
  overrides: Record<string, number>;
  notes: string;
}

// Returned by GET /item-instances/{id} — template + overrides already merged
export interface ResolvedItemInstance {
  id: string;
  adventure_id: string;
  template_id: string;
  owner_id: string | null;
  notes: string;
  name: string;
  description: string;
  tags: string[];
  properties: Record<string, number>;
  metadata: Record<string, unknown>;
}
