import { useId } from "react";
import type { CustomField, FieldType } from "../../types/blueprint";
import { formatDiceNotation, parseDiceNotation } from "../../utils/dice";

interface Props {
  fields: CustomField[];
  onChange: (fields: CustomField[]) => void;
}

const FIELD_TYPES: { value: FieldType; label: string }[] = [
  { value: "string", label: "Text" },
  { value: "number", label: "Number" },
  { value: "boolean", label: "Yes/No" },
  { value: "dice_roll", label: "Dice Roll" },
];

// Unconstrained string server-side -- this is a convenience datalist, not an enum.
const KNOWN_BOUND_BEHAVIORS = [
  "stat", "hp", "max_hp", "is_player", "hit_roll", "damage_roll", "weight",
  "heal_amount", "grants_status_effect", "consumed_on_use", "defense",
  "stat_modifier_key", "stat_modifier_delta", "container", "readable", "key", "value",
];

function emptyField(): CustomField {
  return {
    key: "", label: "", field_type: "string", value: "",
    is_enum: false, options: [], required: false, bound_behavior: null, hidden: false,
  };
}

function defaultValueForType(type: FieldType): unknown {
  switch (type) {
    case "number": return 0;
    case "boolean": return false;
    case "dice_roll": return "1d6";
    default: return "";
  }
}

const inputClass =
  "bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-500 px-3 py-2 rounded-lg text-sm focus:outline-none focus:border-accent transition-colors duration-150";

function MiniToggle({ on, onToggle, label }: { on: boolean; onToggle: () => void; label: string }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer select-none">
      <div
        onClick={onToggle}
        className={`w-8 h-4 rounded-full relative transition-colors duration-150 shrink-0 ${
          on ? "bg-accent" : "bg-zinc-700"
        }`}
      >
        <div
          className={`absolute top-0.5 w-3 h-3 bg-white rounded-full shadow transition-transform duration-150 ${
            on ? "translate-x-4" : "translate-x-0.5"
          }`}
        />
      </div>
      <span className="text-xs text-zinc-400">{label}</span>
    </label>
  );
}

function ValueEditor({ field, onChange }: { field: CustomField; onChange: (value: unknown) => void }) {
  if (field.is_enum) {
    return (
      <select
        value={String(field.value ?? "")}
        onChange={(e) => onChange(e.target.value)}
        className={inputClass}
      >
        {field.options.length === 0 && <option value="">(no options set)</option>}
        {field.options.map((opt) => (
          <option key={String(opt)} value={String(opt)}>{String(opt)}</option>
        ))}
      </select>
    );
  }

  if (field.field_type === "boolean") {
    return (
      <MiniToggle
        on={Boolean(field.value)}
        onToggle={() => onChange(!field.value)}
        label={field.value ? "True" : "False"}
      />
    );
  }

  if (field.field_type === "dice_roll") {
    let count = 1, sides = 6, bonus = 0;
    try {
      const parsed = parseDiceNotation(String(field.value ?? "1d6"));
      count = parsed.count; sides = parsed.sides; bonus = parsed.bonus;
    } catch {
      // leave defaults on unparsable notation (e.g. mid-edit)
    }
    const emit = (c: number, s: number, b: number) => onChange(formatDiceNotation(c, s, b));
    return (
      <div className="flex items-center gap-1.5">
        <input
          type="number" min={1} value={count}
          onChange={(e) => emit(Number(e.target.value) || 1, sides, bonus)}
          className={`${inputClass} w-14`}
        />
        <span className="text-zinc-500 text-sm">d</span>
        <input
          type="number" min={1} value={sides}
          onChange={(e) => emit(count, Number(e.target.value) || 1, bonus)}
          className={`${inputClass} w-16`}
        />
        <span className="text-zinc-500 text-sm">+</span>
        <input
          type="number" value={bonus}
          onChange={(e) => emit(count, sides, Number(e.target.value) || 0)}
          className={`${inputClass} w-16`}
        />
      </div>
    );
  }

  if (field.field_type === "number") {
    return (
      <input
        type="number" value={Number(field.value ?? 0)}
        onChange={(e) => onChange(Number(e.target.value))}
        className={inputClass}
      />
    );
  }

  return (
    <input
      type="text" value={String(field.value ?? "")}
      onChange={(e) => onChange(e.target.value)}
      className={inputClass}
    />
  );
}

export default function CustomFieldListEditor({ fields, onChange }: Props) {
  const datalistId = useId();

  function updateField(index: number, patch: Partial<CustomField>) {
    const next = fields.slice();
    next[index] = { ...next[index], ...patch };
    onChange(next);
  }

  function removeField(index: number) {
    onChange(fields.filter((_, i) => i !== index));
  }

  function addField() {
    onChange([...fields, emptyField()]);
  }

  function handleTypeChange(index: number, field_type: FieldType) {
    updateField(index, { field_type, value: defaultValueForType(field_type) });
  }

  function handleOptionsChange(index: number, text: string) {
    const options = text.split(",").map((s) => s.trim()).filter(Boolean);
    updateField(index, { options });
  }

  return (
    <div className="flex flex-col gap-3">
      <datalist id={datalistId}>
        {KNOWN_BOUND_BEHAVIORS.map((b) => <option key={b} value={b} />)}
      </datalist>

      {fields.length === 0 && (
        <p className="text-xs text-zinc-600">No fields yet -- add one below.</p>
      )}

      {fields.map((field, i) => (
        <div key={i} className="bg-zinc-800/60 border border-zinc-700 rounded-xl p-3 flex flex-col gap-2.5">
          <div className="flex items-center gap-2">
            <input
              type="text" value={field.key} placeholder="key"
              onChange={(e) => updateField(i, { key: e.target.value })}
              className={`${inputClass} flex-1 min-w-0`}
            />
            <input
              type="text" value={field.label} placeholder="Label"
              onChange={(e) => updateField(i, { label: e.target.value })}
              className={`${inputClass} flex-1 min-w-0`}
            />
            <select
              value={field.field_type}
              onChange={(e) => handleTypeChange(i, e.target.value as FieldType)}
              className={`${inputClass} shrink-0`}
            >
              {FIELD_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
            <button
              onClick={() => removeField(i)}
              className="text-zinc-600 hover:text-red-400 text-lg leading-none px-1 transition-colors duration-150 shrink-0"
              title="Remove field"
            >
              &#x2715;
            </button>
          </div>

          <div className="flex items-center gap-4 flex-wrap">
            <MiniToggle on={field.required} onToggle={() => updateField(i, { required: !field.required })} label="Required" />
            <MiniToggle
              on={field.is_enum}
              onToggle={() => updateField(i, { is_enum: !field.is_enum })}
              label="Enum"
            />
            <MiniToggle on={field.hidden} onToggle={() => updateField(i, { hidden: !field.hidden })} label="Hidden" />
            <input
              type="text" value={field.bound_behavior ?? ""} placeholder="bound_behavior (optional)"
              list={datalistId}
              onChange={(e) => updateField(i, { bound_behavior: e.target.value || null })}
              className={`${inputClass} flex-1 min-w-[10rem]`}
            />
          </div>

          {field.is_enum && (
            <input
              type="text"
              value={field.options.join(", ")}
              placeholder="option1, option2, option3"
              onChange={(e) => handleOptionsChange(i, e.target.value)}
              className={inputClass}
            />
          )}

          <div className="flex flex-col gap-1">
            <span className="text-xs uppercase tracking-wider text-zinc-500">Value</span>
            <ValueEditor field={field} onChange={(value) => updateField(i, { value })} />
          </div>
        </div>
      ))}

      <button
        onClick={addField}
        className="self-start px-3 py-1.5 text-xs font-semibold text-accent hover:text-accent-hover border border-zinc-700 hover:border-accent rounded-lg transition-colors duration-150"
      >
        + Add Field
      </button>
    </div>
  );
}
