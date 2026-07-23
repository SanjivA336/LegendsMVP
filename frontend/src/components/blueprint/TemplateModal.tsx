import { useEffect, useState } from "react";
import Modal from "../ui/Modal";
import CustomFieldListEditor from "./CustomFieldListEditor";
import { getTemplateDefaultFields } from "../../api/entities";
import type { Kind } from "../../types/blueprint";
import type { DraftTemplate } from "../../pages/wizard/draftTypes";

interface Props {
  open: boolean;
  onClose: () => void;
  onSave: (draft: DraftTemplate) => void;
  initial?: DraftTemplate | null;
}

const KIND_OPTIONS: { value: Kind; label: string }[] = [
  { value: "character", label: "Character" },
  { value: "race", label: "Race" },
  { value: "class", label: "Class" },
  { value: "weapon", label: "Weapon" },
  { value: "consumable", label: "Consumable" },
  { value: "wearable", label: "Wearable" },
  { value: "custom", label: "Custom" },
];

const inputClass =
  "bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-500 px-3 py-2.5 rounded-xl text-sm focus:outline-none focus:border-accent transition-colors duration-150";

function emptyDraft(kind: Kind): DraftTemplate {
  return { tempId: crypto.randomUUID(), kind, name: "", description: "", tags: [], fields: [] };
}

export default function TemplateModal({ open, onClose, onSave, initial }: Props) {
  const [draft, setDraft] = useState<DraftTemplate>(() => initial ?? emptyDraft("custom"));
  const [tagsText, setTagsText] = useState(initial?.tags.join(", ") ?? "");
  const isNew = !initial;

  // Re-seed whenever the modal opens fresh -- a brand-new draft pulls the server's
  // canonical default fields for its starting kind ("custom"), matching what happens
  // again below whenever the user changes kind.
  useEffect(() => {
    if (!open) return;
    if (initial) {
      setDraft(initial);
      setTagsText(initial.tags.join(", "));
      return;
    }
    const next = emptyDraft("custom");
    setDraft(next);
    setTagsText("");
    getTemplateDefaultFields(next.kind)
      .then((fields) => setDraft((d) => ({ ...d, fields })))
      .catch(() => {});
  }, [open, initial]);

  function handleKindChange(kind: Kind) {
    setDraft((d) => ({ ...d, kind }));
    getTemplateDefaultFields(kind)
      .then((fields) => setDraft((d) => ({ ...d, fields })))
      .catch(() => {});
  }

  function handleSave() {
    if (!draft.name.trim()) return;
    onSave({
      ...draft,
      name: draft.name.trim(),
      tags: tagsText.split(",").map((t) => t.trim()).filter(Boolean),
    });
    onClose();
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isNew ? "New Template" : `Edit ${draft.name || "Template"}`}
      maxWidth="max-w-2xl"
    >
      <div className="flex flex-col gap-5">
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs uppercase tracking-wider text-zinc-400">Name</label>
            <input
              type="text"
              value={draft.name}
              autoFocus
              onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
              placeholder="Rusty Sword"
              className={inputClass}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs uppercase tracking-wider text-zinc-400">Kind</label>
            <select
              value={draft.kind}
              disabled={!isNew}
              onChange={(e) => handleKindChange(e.target.value as Kind)}
              className={`${inputClass} disabled:opacity-50`}
            >
              {KIND_OPTIONS.map((k) => (
                <option key={k.value} value={k.value}>{k.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs uppercase tracking-wider text-zinc-400">Description</label>
          <textarea
            value={draft.description}
            onChange={(e) => setDraft((d) => ({ ...d, description: e.target.value }))}
            rows={2}
            className={`${inputClass} resize-none`}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs uppercase tracking-wider text-zinc-400">Tags (comma-separated)</label>
          <input
            type="text"
            value={tagsText}
            onChange={(e) => setTagsText(e.target.value)}
            placeholder="starter, common"
            className={inputClass}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs uppercase tracking-wider text-zinc-400">Fields</label>
          <CustomFieldListEditor
            fields={draft.fields}
            onChange={(fields) => setDraft((d) => ({ ...d, fields }))}
          />
        </div>

        <div className="flex justify-between pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!draft.name.trim()}
            className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150 disabled:opacity-40"
          >
            Save Template
          </button>
        </div>
      </div>
    </Modal>
  );
}
