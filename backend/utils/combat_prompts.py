"""
Pure prompt-building functions for combat-related DM calls.

Injection order mirrors the design doc:
  1. DM persona + output format
  2. World Bible (always_inject ContextCards)
  3. World State facts
  4. Combat / location context
  5. Task block with mechanical facts
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.context import ContextCard, WorldState
    from ..models.combat import ArenaCombatant


# ── Shared Helpers ─────────────────────────────────────────────────────────────

_DM_SYSTEM_BLOCK = (
    "You are a dungeon master (DM) for a tabletop RPG. "
    "You generate rich, world-consistent narrative content. "
    "Always respond with valid JSON exactly matching the required schema — "
    "no extra keys, no markdown fences."
)


# Combat narration is the highest-frequency AI call in the app (fires every non-end_turn
# action, every turn, every combatant) -- cap what's injected instead of sending the
# adventure's entire card/fact library on every single call.
_MAX_CARDS_IN_PROMPT = 4
_MAX_FACTS_IN_PROMPT = 4


def _format_cards(cards: list["ContextCard"]) -> str:
    if not cards:
        return "(none)"
    return "\n".join(f"[{c.label}]\n{c.content}" for c in cards[:_MAX_CARDS_IN_PROMPT])


def _format_world_state(world_state: "WorldState | None") -> str:
    if not world_state or not world_state.facts:
        return "(no facts recorded yet)"
    # facts are append-only (oldest first) -- the most recent ones are the relevant ones.
    recent_facts = world_state.facts[-_MAX_FACTS_IN_PROMPT:]
    return "\n".join(f"- {f}" for f in recent_facts)


# ── Arena Generation Prompt ───────────────────────────────────────────────────

_ARENA_SCHEMA_DOCS = """
TILE SCHEMA (only specify non-default tiles):
  x, y: int                     — grid position (0,0 = top-left)
  terrain_tag: str              — "floor" (default), "water", "lava", "mud", "grass", etc.
  passable: bool                — false for impassable ground (default: true)
  movement_cost: int            — 1 (default/normal), 2 (difficult terrain like mud)
  aura: str | null              — status tag applied every round to any unit standing here
                                   e.g. "burning", "blessed", "poisoned"
  hazard: int                   — HP damage dealt when a unit enters this tile (default 0)

EDGE SCHEMA (barriers between adjacent tiles; only specify non-zero):
  x, y: int                     — the source tile
  direction: "north"|"east"|"south"|"west"
  level: 1|2|3
    1 = cover     — passable at +1 move cost; reduces incoming damage by 1
    2 = barrier   — blocks ground/sea; air passes freely (except in indoor arenas)
    3 = sealed    — blocks ALL movement including air (use for solid underground walls)
  Important: set both sides of a wall (e.g. tile A east=2 AND tile B west=2).

OBJECT SCHEMA:
  x, y: int
  type: "bulwark" | "cache"
    bulwark — full-tile obstacle (pillar, boulder, castle wall). Blocks ALL units.
               Automatically makes the tile impassable. Provides cover to adjacent tiles.
    cache   — lootable container (chest, barrel). Does not block movement.
              item_ids: list[str]  — optional pre-seeded item instance IDs
"""


def build_arena_generation_prompt(
    location_type: str,
    width: int,
    height: int,
    indoor: bool,
    world_bible_cards: list["ContextCard"],
    world_state: "WorldState | None",
) -> str:
    indoor_note = (
        "This arena is INDOORS — level-2 barrier edges block air units as well as ground units."
        if indoor else
        "This arena is OUTDOORS — level-2 barrier edges only block ground/sea units, not air."
    )

    return f"""{_DM_SYSTEM_BLOCK}

=== WORLD BIBLE ===
{_format_cards(world_bible_cards)}

=== WORLD STATE ===
{_format_world_state(world_state)}

=== ARENA CONTEXT ===
Location type: {location_type}
Grid size: {width} × {height} (width × height)
{indoor_note}

Only specify tiles, edges, and objects that differ from the defaults (open passable floor).
The engine fills all unspecified positions with open floor.

{_ARENA_SCHEMA_DOCS}

=== TASK ===
Generate a tactically interesting arena for this {location_type} encounter.
Requirements:
- The arena must be fully traversable — ensure ground units can reach any part of the map.
- Place 1–3 bulwarks for terrain variety (pillars, boulders).
- Use edges (cover and barriers) to create chokepoints or cover positions.
- If location_type is "encampment", include at least one cache for looting.
- Terrain tags and aura/hazard values should fit the world's aesthetic from the World Bible.
- Do NOT place obstacles that completely isolate sections of the map.

Respond with exactly this JSON:
{{
  "narrative": "One evocative sentence describing the arena.",
  "updates": {{
    "arena": {{
      "tiles": [],
      "edges": [],
      "objects": []
    }}
  }}
}}"""


# ── Action Narration Prompt ───────────────────────────────────────────────────

def build_action_narration_prompt(
    action_type: str,
    actor_name: str,
    target_name: str | None,
    outcome_summary: str,
    world_bible_cards: list["ContextCard"],
    world_state: "WorldState | None",
) -> str:
    target_line = f"Target: {target_name}" if target_name else ""

    return f"""{_DM_SYSTEM_BLOCK}

=== WORLD BIBLE ===
{_format_cards(world_bible_cards)}

=== WORLD STATE ===
{_format_world_state(world_state)}

=== TASK ===
Narrate the following combat action in 1–2 vivid sentences.
Do NOT include dice numbers, stat values, or HP totals in your prose — narrate the outcome
in purely in-world terms (hits, misses, impacts, movement, effects).

Actor: {actor_name}
Action: {action_type}
{target_line}
Mechanical outcome: {outcome_summary}

Respond with exactly this JSON:
{{
  "narrative": "..."
}}"""


# ── Combat End Prompt ─────────────────────────────────────────────────────────

def build_combat_end_prompt(
    outcome: str,
    combatant_summaries: list[str],
    world_bible_cards: list["ContextCard"],
    world_state: "WorldState | None",
) -> str:
    survivors_text = "\n".join(f"  - {s}" for s in combatant_summaries) or "  (none)"

    outcome_label = {
        "completed": "VICTORY — the party prevailed",
        "fled": "FLED — the party escaped combat",
        "defeat": "DEFEAT — the party was overcome",
    }.get(outcome, outcome.upper())

    return f"""{_DM_SYSTEM_BLOCK}

=== WORLD BIBLE ===
{_format_cards(world_bible_cards)}

=== WORLD STATE ===
{_format_world_state(world_state)}

=== TASK ===
Write 2–3 sentences narrating the resolution of a combat encounter.
Outcome: {outcome_label}

Surviving combatants:
{survivors_text}

Focus on the atmosphere, the immediate aftermath, and what the world feels like
now that the fight is over. Do not list HP values or mechanical results.

Respond with exactly this JSON:
{{
  "narrative": "..."
}}"""
