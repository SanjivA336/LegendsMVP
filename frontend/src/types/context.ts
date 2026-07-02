// Mirrors backend/models/context.py — keep in sync when fields change

export interface ContextCard {
  id: string;
  adventure_id: string;
  label: string;
  content: string;
  keyword_trigger: string | null;
  event_trigger: string | null;
  always_inject: boolean;
}

export interface WorldState {
  id: string;
  adventure_id: string;
  facts: string[];
  token_count: number;
}

export interface RelationshipEdge {
  id: string;
  adventure_id: string;
  from_id: string;
  to_id: string;
  affinity: number;   // -1.0 to 1.0
  fear: number;       // 0.0 to 1.0
  submission: number; // 0.0 to 1.0
}

export interface RelationshipMap {
  nodes: string[];
  edges: RelationshipEdge[];
}
