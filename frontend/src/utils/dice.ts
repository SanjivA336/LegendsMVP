// Pure TS mirror of backend/models/blueprint.py's format_dice_notation/parse_dice_notation --
// used only for the dice_roll field composer's live display (3 inputs -> "2d6+4" preview);
// the canonical parse/format still happens server-side whenever a dice_roll field is used.

const DICE_NOTATION_RE = /^(\d+)d(\d+)([+-]\d+)?$/;

export function formatDiceNotation(count: number, sides: number, bonus = 0): string {
  const suffix = bonus ? (bonus > 0 ? `+${bonus}` : `${bonus}`) : "";
  return `${count}d${sides}${suffix}`;
}

export function parseDiceNotation(notation: string): { count: number; sides: number; bonus: number } {
  const match = DICE_NOTATION_RE.exec(notation.trim());
  if (!match) throw new Error(`Invalid dice notation: ${notation}`);
  const [, count, sides, bonus] = match;
  return { count: Number(count), sides: Number(sides), bonus: bonus ? Number(bonus) : 0 };
}
