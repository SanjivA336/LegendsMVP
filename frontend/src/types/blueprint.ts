// Mirrors backend/models/blueprint.py — keep in sync when fields change

export type FieldType = "string" | "number" | "boolean" | "dice_roll";

export interface CustomField {
  key: string;
  label: string;
  field_type: FieldType;
  value: unknown;
  is_enum: boolean;
  options: unknown[];
  required: boolean;
  bound_behavior: string | null;
  hidden: boolean;
}

export type Kind = "character" | "race" | "class" | "weapon" | "consumable" | "wearable" | "custom";

export interface Template {
  id: string;
  adventure_id: string;
  kind: Kind;
  name: string;
  description: string;
  tags: string[];
  fields: CustomField[];
  metadata: Record<string, unknown>;
}

export interface AttachedRef {
  ref_id: string;
  ref_kind: string;
  expires_at_round: number | null;
}

export interface Instance {
  id: string;
  adventure_id: string;
  kind: Kind;
  template_id: string | null;
  fields: CustomField[];
  attached: AttachedRef[];
  inventory_ids: string[];
  equipped_weapon_id: string | null;
  equipped_wearable_ids: string[];
  owner_id: string | null;
  notes: string;
}

// Returned by GET /instances/{id} — template + overrides already merged
export interface ResolvedInstance {
  id: string;
  adventure_id: string;
  kind: Kind;
  template_id: string | null;
  name: string;
  description: string;
  tags: string[];
  fields: CustomField[];
  metadata: Record<string, unknown>;
  attached: AttachedRef[];
  inventory_ids: string[];
  equipped_weapon_id: string | null;
  equipped_wearable_ids: string[];
  owner_id: string | null;
  notes: string;
}

export function getFieldValue(fields: CustomField[], key: string): unknown {
  return fields.find((f) => f.key === key)?.value ?? null;
}

// Mirrors backend/models/blueprint.py::merge_fields -- entries in `overrides` win
// wholesale for shared keys. Used client-side to seed a draft instance's editor with
// its template's fields before any of the instance's own overrides are applied.
export function mergeFields(base: CustomField[], overrides: CustomField[]): CustomField[] {
  const byKey = new Map<string, CustomField>(base.map((f) => [f.key, f]));
  for (const f of overrides) byKey.set(f.key, f);
  return Array.from(byKey.values());
}

// Payload shapes for the Launch commit sequence -- mirror backend TemplateCreate/InstanceCreate

export interface TemplateCreate {
  adventure_id: string;
  kind: Kind;
  name: string;
  description?: string;
  tags?: string[];
  fields?: CustomField[];
  metadata?: Record<string, unknown>;
}

export interface InstanceCreate {
  adventure_id: string;
  kind: Kind;
  template_id?: string | null;
  fields?: CustomField[];
  attached?: AttachedRef[];
  inventory_ids?: string[];
  equipped_weapon_id?: string | null;
  equipped_wearable_ids?: string[];
  owner_id?: string | null;
  notes?: string;
}
