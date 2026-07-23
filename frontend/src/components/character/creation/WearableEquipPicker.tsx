import type { ItemCandidate } from "./types";

interface Props {
  candidates: ItemCandidate[];
  equippedIds: string[];
  onChange: (ids: string[]) => void;
  onAddNew: () => void;
}

function groupBySlot(candidates: ItemCandidate[]): Map<string, ItemCandidate[]> {
  const groups = new Map<string, ItemCandidate[]>();
  for (const c of candidates) {
    const slot = c.slot?.trim() || "unslotted";
    const group = groups.get(slot) ?? [];
    group.push(c);
    groups.set(slot, group);
  }
  return groups;
}

export default function WearableEquipPicker({ candidates, equippedIds, onChange, onAddNew }: Props) {
  const groups = groupBySlot(candidates);
  const equippedSet = new Set(equippedIds);

  function pick(slotCandidates: ItemCandidate[], id: string) {
    // one item per slot -- selecting a new one for this slot replaces whatever
    // was equipped there, clicking the already-equipped one unequips it
    const slotIds = new Set(slotCandidates.map((c) => c.id));
    const withoutSlot = equippedIds.filter((eid) => !slotIds.has(eid));
    onChange(equippedSet.has(id) ? withoutSlot : [...withoutSlot, id]);
  }

  if (candidates.length === 0) {
    return (
      <div className="flex flex-col gap-3">
        <p className="text-xs text-zinc-600">No wearables available yet in this adventure.</p>
        <button
          onClick={onAddNew}
          className="self-start px-3 py-1.5 text-xs font-semibold text-accent hover:text-accent-hover border border-zinc-700 hover:border-accent rounded-lg transition-colors duration-150"
        >
          + New Item
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {Array.from(groups.entries()).map(([slot, group]) => (
        <div key={slot} className="flex flex-col gap-1.5">
          <span className="text-[10px] uppercase tracking-wider text-zinc-600">{slot}</span>
          <div className="flex flex-wrap gap-2">
            {group.map((c) => (
              <button
                key={c.id}
                onClick={() => pick(group, c.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors duration-150 ${
                  equippedSet.has(c.id)
                    ? "border-accent bg-accent/10 text-zinc-100"
                    : "border-zinc-700 hover:border-zinc-600 text-zinc-400"
                }`}
              >
                {c.name}
              </button>
            ))}
          </div>
        </div>
      ))}
      <button
        onClick={onAddNew}
        className="self-start px-3 py-1.5 text-xs font-semibold text-accent hover:text-accent-hover border border-zinc-700 hover:border-accent rounded-lg transition-colors duration-150"
      >
        + New Item
      </button>
    </div>
  );
}
