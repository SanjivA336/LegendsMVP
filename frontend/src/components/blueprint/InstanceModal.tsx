import { useEffect, useState } from "react";
import Modal from "../ui/Modal";
import CustomFieldListEditor from "./CustomFieldListEditor";
import { mergeFields } from "../../types/blueprint";
import type { CustomField, Kind } from "../../types/blueprint";
import type { DraftTemplate, DraftInstance } from "../../pages/wizard/draftTypes";

interface Props {
  open: boolean;
  onClose: () => void;
  onSave: (draft: DraftInstance) => void;
  initial?: DraftInstance | null;
  templates: DraftTemplate[];   // candidate templates for this instance's kind
  kind: Kind;
}

const inputClass =
  "bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-500 px-3 py-2.5 rounded-xl text-sm focus:outline-none focus:border-accent transition-colors duration-150";

function emptyDraft(kind: Kind, templateTempId: string | null, fields: CustomField[]): DraftInstance {
  return { tempId: crypto.randomUUID(), kind, templateTempId, fields, ownerTempId: null, notes: "" };
}

export default function InstanceModal({ open, onClose, onSave, initial, templates, kind }: Props) {
  const [draft, setDraft] = useState<DraftInstance>(
    () => initial ?? emptyDraft(kind, templates[0]?.tempId ?? null, templates[0] ? [...templates[0].fields] : [])
  );
  const isNew = !initial;

  useEffect(() => {
    if (!open) return;
    if (initial) {
      setDraft(initial);
      return;
    }
    const tmpl = templates[0];
    setDraft(emptyDraft(kind, tmpl?.tempId ?? null, tmpl ? [...tmpl.fields] : []));
  }, [open, initial]);

  function handleTemplateChange(templateTempId: string) {
    const tmpl = templates.find((t) => t.tempId === templateTempId);
    setDraft((d) => ({
      ...d,
      templateTempId: templateTempId || null,
      // seed from the newly-chosen template's fields, keeping any overrides the user
      // already made that share a key -- same by-key-override semantics as the backend
      fields: tmpl ? mergeFields(tmpl.fields, d.fields) : d.fields,
    }));
  }

  function handleSave() {
    onSave(draft);
    onClose();
  }

  const selectedTemplate = templates.find((t) => t.tempId === draft.templateTempId);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isNew ? `New ${selectedTemplate?.kind ?? kind}` : `Edit ${selectedTemplate?.name ?? "Instance"}`}
      maxWidth="max-w-2xl"
    >
      <div className="flex flex-col gap-5">
        {templates.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <label className="text-xs uppercase tracking-wider text-zinc-400">Template</label>
            <select
              value={draft.templateTempId ?? ""}
              onChange={(e) => handleTemplateChange(e.target.value)}
              className={inputClass}
            >
              <option value="">(none)</option>
              {templates.map((t) => (
                <option key={t.tempId} value={t.tempId}>{t.name}</option>
              ))}
            </select>
            {selectedTemplate?.description && (
              <p className="text-xs text-zinc-600">{selectedTemplate.description}</p>
            )}
          </div>
        )}

        <div className="flex flex-col gap-1.5">
          <label className="text-xs uppercase tracking-wider text-zinc-400">Notes</label>
          <textarea
            value={draft.notes}
            onChange={(e) => setDraft((d) => ({ ...d, notes: e.target.value }))}
            rows={2}
            placeholder="DM-only notes about this specific instance"
            className={`${inputClass} resize-none`}
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
            className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150"
          >
            Save Instance
          </button>
        </div>
      </div>
    </Modal>
  );
}
