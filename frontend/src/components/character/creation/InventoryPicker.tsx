import type { ItemCandidate } from "./types";

interface Props {
  candidates: ItemCandidate[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
}

// Pure list + multi-select -- "add new" isn't handled here since a new inventory item can
// be any kind (weapon/wearable/consumable/custom), and InstanceModal (which this would
// open) is fixed to one kind at a time. The caller renders its own kind-specific "add new"
// affordance below this component instead.
export default function InventoryPicker({ candidates, selectedIds, onChange }: Props) {
  const selectedSet = new Set(selectedIds);

  function toggle(id: string) {
    onChange(selectedSet.has(id) ? selectedIds.filter((i) => i !== id) : [...selectedIds, id]);
  }

  return candidates.length === 0 ? (
    <p className="text-xs text-zinc-600">No items available yet in this adventure.</p>
  ) : (
    <div className="flex flex-wrap gap-2">
      {candidates.map((c) => (
        <button
          key={c.id}
          onClick={() => toggle(c.id)}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors duration-150 ${
            selectedSet.has(c.id)
              ? "border-accent bg-accent/10 text-zinc-100"
              : "border-zinc-700 hover:border-zinc-600 text-zinc-400"
          }`}
        >
          {c.name}
        </button>
      ))}
    </div>
  );
}
