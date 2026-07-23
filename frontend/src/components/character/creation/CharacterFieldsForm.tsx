import CustomFieldListEditor from "../../blueprint/CustomFieldListEditor";
import type { CustomField } from "../../../types/blueprint";

interface Props {
  name: string;
  onNameChange: (v: string) => void;
  description: string;
  onDescriptionChange: (v: string) => void;
  tone: string;
  onToneChange: (v: string) => void;
  raceId: string | null;
  onRaceChange: (v: string | null) => void;
  classId: string | null;
  onClassChange: (v: string | null) => void;
  races: { id: string; name: string }[];
  classes: { id: string; name: string }[];
  customFields: CustomField[];
  onCustomFieldsChange: (fields: CustomField[]) => void;
  showCustomFields: boolean;
}

const inputClass =
  "bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-500 px-3 py-2.5 rounded-xl text-sm focus:outline-none focus:border-accent transition-colors duration-150";

export default function CharacterFieldsForm({
  name, onNameChange, description, onDescriptionChange, tone, onToneChange,
  raceId, onRaceChange, classId, onClassChange, races, classes,
  customFields, onCustomFieldsChange, showCustomFields,
}: Props) {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-1.5">
        <label className="text-xs uppercase tracking-wider text-zinc-400">Name</label>
        <input
          type="text" value={name} autoFocus
          onChange={(e) => onNameChange(e.target.value)}
          placeholder="Kael Ashveil"
          className={inputClass}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-xs uppercase tracking-wider text-zinc-400">Description</label>
        <textarea
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          placeholder="A wandering swordsman with a troubled past..."
          rows={3}
          className={`${inputClass} resize-none`}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-xs uppercase tracking-wider text-zinc-400">Speaking Tone</label>
        <input
          type="text" value={tone}
          onChange={(e) => onToneChange(e.target.value)}
          placeholder="Terse, dry humor, formal when nervous"
          className={inputClass}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs uppercase tracking-wider text-zinc-400">Race</label>
          <select
            value={raceId ?? ""}
            onChange={(e) => onRaceChange(e.target.value || null)}
            className={inputClass}
          >
            <option value="">None</option>
            {races.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-xs uppercase tracking-wider text-zinc-400">Class</label>
          <select
            value={classId ?? ""}
            onChange={(e) => onClassChange(e.target.value || null)}
            className={inputClass}
          >
            <option value="">None</option>
            {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
      </div>

      {showCustomFields && (
        <div className="flex flex-col gap-1.5">
          <label className="text-xs uppercase tracking-wider text-zinc-400">
            Additional Fields
          </label>
          <p className="text-xs text-zinc-600 -mt-1">
            From this adventure's character template.
          </p>
          <CustomFieldListEditor fields={customFields} onChange={onCustomFieldsChange} />
        </div>
      )}
    </div>
  );
}
