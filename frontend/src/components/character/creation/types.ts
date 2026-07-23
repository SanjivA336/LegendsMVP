import type { CustomField } from "../../../types/blueprint";

// Shared shape for anything pickable in the equip/inventory steps -- deliberately
// decoupled from DraftInstance/Instance so these components work identically whether
// the caller is drawing from wizard drafts (tempIds) or real adventure data (real ids).
// The caller is responsible for resolving `name`/`slot` before handing candidates in
// (e.g. via mergeFields + getFieldValue over a DraftInstance/Instance + its template).

export interface ItemCandidate {
  id: string;
  name: string;
  slot?: string;   // only meaningful for wearables; absent/empty -> "Unslotted" group
}

// Mirrors backend/models/blueprint.py's KIND_FIELD_DEFS["character"] keys -- a DM's
// character-template fields get filtered against this so CharacterFieldsForm only shows
// genuinely custom fields, not duplicates of the name/stats/description/tone inputs
// already collected elsewhere.
export const CANONICAL_CHARACTER_FIELD_KEYS = new Set([
  "name", "description", "tone", "is_player", "hp", "max_hp", "age",
  "strength", "dexterity", "intelligence", "fortitude", "charisma", "reflex",
]);

export function nonCanonicalFields(fields: CustomField[]): CustomField[] {
  return fields.filter((f) => !CANONICAL_CHARACTER_FIELD_KEYS.has(f.key));
}
