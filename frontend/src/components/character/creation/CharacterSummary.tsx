import { getFieldValue } from "../../../types/blueprint";
import type { CustomField } from "../../../types/blueprint";
import type { ItemCandidate } from "./types";

interface Props {
  name: string;
  description: string;
  tone: string;
  raceName: string | null;
  className: string | null;
  stats: Record<string, number>;
  attributeNames: Record<string, string>;
  customFields: CustomField[];
  equippedItems: ItemCandidate[];
  inventoryItems: ItemCandidate[];   // full carried set, including equipped ones
}

export default function CharacterSummary({
  name, description, tone, raceName, className, stats, attributeNames,
  customFields, equippedItems, inventoryItems,
}: Props) {
  const equippedIds = new Set(equippedItems.map((i) => i.id));
  const carriedOnly = inventoryItems.filter((i) => !equippedIds.has(i.id));

  return (
    <div className="flex flex-col gap-4">
      <div>
        <div className="text-lg font-semibold text-zinc-100">{name || "(unnamed)"}</div>
        {(raceName || className) && (
          <div className="text-xs text-zinc-500">{[raceName, className].filter(Boolean).join(" · ")}</div>
        )}
        {description && <p className="text-sm text-zinc-400 mt-1">{description}</p>}
        {tone && <p className="text-xs text-zinc-600 mt-0.5">Speaks: {tone}</p>}
      </div>

      <div className="grid grid-cols-3 gap-2">
        {Object.entries(stats).map(([key, value]) => (
          <div key={key} className="bg-zinc-800/60 border border-zinc-700 rounded-lg px-2.5 py-1.5 text-center">
            <div className="text-[10px] uppercase tracking-wider text-zinc-600">
              {attributeNames[key] ?? key}
            </div>
            <div className="text-sm font-mono font-bold text-zinc-100">{value}</div>
          </div>
        ))}
      </div>

      {customFields.length > 0 && (
        <div className="flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wider text-zinc-500">Additional Fields</span>
          {customFields.map((f) => (
            <div key={f.key} className="text-sm text-zinc-300 flex justify-between">
              <span className="text-zinc-500">{f.label || f.key}</span>
              <span>{String(getFieldValue(customFields, f.key) ?? "")}</span>
            </div>
          ))}
        </div>
      )}

      <div className="flex flex-col gap-1">
        <span className="text-xs uppercase tracking-wider text-zinc-500">Worn</span>
        {equippedItems.length === 0 ? (
          <p className="text-xs text-zinc-600">Nothing equipped.</p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {equippedItems.map((i) => (
              <span key={i.id} className="px-2 py-1 bg-accent/10 border border-accent/40 text-accent text-xs rounded-lg">
                {i.name}{i.slot ? ` (${i.slot})` : ""}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <span className="text-xs uppercase tracking-wider text-zinc-500">Carrying</span>
        {carriedOnly.length === 0 ? (
          <p className="text-xs text-zinc-600">Nothing else in inventory.</p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {carriedOnly.map((i) => (
              <span key={i.id} className="px-2 py-1 bg-zinc-800 border border-zinc-700 text-zinc-300 text-xs rounded-lg">
                {i.name}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
