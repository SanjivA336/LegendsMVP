// Local-draft shapes used while authoring the wizard, before anything is real. Every
// draft carries a client-generated tempId (crypto.randomUUID()) instead of a backend id --
// see the "draft-first, single commit at Launch" architecture in the wizard plan.

import { mergeFields, getFieldValue } from "../../types/blueprint";
import type { CustomField, Kind } from "../../types/blueprint";
import type { ItemCandidate } from "../../components/character/creation/types";

export interface DraftTemplate {
  tempId: string;
  kind: Kind;
  name: string;
  description: string;
  tags: string[];
  fields: CustomField[];
}

export interface DraftInstance {
  tempId: string;
  kind: Kind;
  templateTempId: string | null;
  fields: CustomField[];
  ownerTempId?: string | null;
  notes: string;
}

// Resolves a draft instance's display name/slot (template default merged with its own
// overrides) into the shape the equip/inventory pickers expect -- item-like kinds get
// their name from the Template itself (no "name" CustomField exists for them), matching
// the same convention resolve_instance() uses server-side.
export function resolveDraftInstance(instance: DraftInstance, templates: DraftTemplate[]): ItemCandidate {
  const template = templates.find((t) => t.tempId === instance.templateTempId) ?? null;
  const merged = mergeFields(template?.fields ?? [], instance.fields);
  const slot = getFieldValue(merged, "slot");
  return {
    id: instance.tempId,
    name: template?.name ?? "Unnamed Item",
    slot: typeof slot === "string" ? slot : undefined,
  };
}
