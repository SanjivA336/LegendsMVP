"""
Pure prompt-building functions for quest-related DM calls.

All functions are free of I/O and side effects. Each returns a JSON-structured
prompt string ready for `provider.generate()`.

Injection order mirrors the design doc (page 12):
  1. DM persona + output format
  2. World Bible (always_inject ContextCards)
  3. World State facts
  4. Quest context
  5. Task block
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.context import ContextCard, WorldState
    from ..models.quest import Quest, QuestStep
    from ..models.event import EventCondition, FireEventRequest


# ── Event Matching ────────────────────────────────────────────────────────────

def event_matches_condition(req: "FireEventRequest", cond: "EventCondition") -> bool:
    """Return True if a fired event satisfies a step's EventCondition.

    Rule: type must match exactly; every non-None field on cond must equal the
    corresponding field on req. None fields are wildcards.
    """
    if req.type != cond.type:
        return False
    for field in ("entity_id", "item_id", "item_type", "poi_id",
                  "tile_x", "tile_y", "encounter_id"):
        cond_val = getattr(cond, field)
        if cond_val is not None and getattr(req, field) != cond_val:
            return False
    return True


# ── Internal Helpers ──────────────────────────────────────────────────────────

_DM_SYSTEM_BLOCK = (
    "You are a dungeon master (DM) for a tabletop RPG. "
    "You generate rich, world-consistent narrative content. "
    "Always respond with valid JSON exactly matching the required schema — "
    "no extra keys, no markdown fences."
)

_STEP_COUNT_HINTS = {
    "short":  "short quest (3–4 total steps)",
    "medium": "medium quest (5–7 total steps)",
    "long":   "long quest (8–12 total steps)",
}

_EVENT_TYPE_LIST = "killed | acquired | delivered | reached | talked_to | survived"


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


def _format_step(step: "QuestStep", label: str) -> str:
    return f"{label}: {step.description}\n  Condition: {step.completion_condition}"


# ── Quest Creation Prompt ─────────────────────────────────────────────────────

def build_quest_creation_prompt(
    length: str,
    context_hint: str,
    world_bible_cards: list["ContextCard"],
    world_state: "WorldState | None",
) -> str:
    hint_line = f"\nTheme hint: {context_hint}" if context_hint else ""

    return f"""{_DM_SYSTEM_BLOCK}

=== WORLD BIBLE ===
{_format_cards(world_bible_cards)}

=== WORLD STATE ===
{_format_world_state(world_state)}

=== TASK ===
Create a {_STEP_COUNT_HINTS[length]}.{hint_line}

You must generate a quest title, an opening step (first_step), and a climactic final step (last_step).
Middle steps will be generated lazily as the party progresses — do not generate them now.

For each step, provide:
- description: what the party must do
- completion_condition: a plain-language statement of what "done" looks like
- completion_event: the discrete engine event that triggers completion (or omit if purely narrative)
  - type must be one of: {_EVENT_TYPE_LIST}
  - include only the fields relevant to the event type (entity_id, item_id, item_type, poi_id, tile_x, tile_y, encounter_id)

If the quest involves specific NPCs or items that must exist in the world (e.g., a target to kill,
a contact to meet), list them in entities_to_create. Use suggested_id values that match the
entity_id values in completion_event fields so the engine can link them.

Respond with exactly this JSON:
{{
  "narrative": "A short evocative paragraph introducing this quest to the party.",
  "updates": {{
    "new_quest": {{
      "title": "...",
      "first_step": {{
        "description": "...",
        "completion_condition": "...",
        "completion_event": {{"type": "...", "entity_id": "..."}}
      }},
      "last_step": {{
        "description": "...",
        "completion_condition": "...",
        "completion_event": {{"type": "...", "entity_id": "..."}}
      }},
      "entities_to_create": [
        {{"name": "...", "suggested_id": "...", "role": "quest_target"}}
      ]
    }}
  }}
}}"""


# ── Next Step Generation Prompt ───────────────────────────────────────────────

def build_next_step_prompt(
    quest: "Quest",
    completed_steps: list["QuestStep"],
    event_type: str,
    world_bible_cards: list["ContextCard"],
    world_state: "WorldState | None",
) -> str:
    completed_text = "\n".join(
        f"  {i+1}. {_format_step(s, 'DONE')}" for i, s in enumerate(completed_steps)
    ) or "  (none yet)"

    remaining = quest.target_middle_count - len([
        s for s in quest.middle_steps if s.status == "completed"
    ])

    return f"""{_DM_SYSTEM_BLOCK}

=== WORLD BIBLE ===
{_format_cards(world_bible_cards)}

=== WORLD STATE ===
{_format_world_state(world_state)}

=== ACTIVE QUEST ===
Title: {quest.title}
{_format_step(quest.last_step, "FINAL GOAL")}

Progress:
{completed_text}

=== TASK ===
A quest step just completed (triggered by a "{event_type}" event).
Generate the next middle step. Approximately {max(remaining - 1, 0)} more middle steps
will follow after this one before the final goal.

The new step should logically follow the completed steps and move toward the final goal.
If a new NPC or item must exist for this step, list it in entities_to_create.

Respond with exactly this JSON:
{{
  "narrative": "A short paragraph describing what the party learns or is tasked with next.",
  "updates": {{
    "new_quest_step": {{
      "description": "...",
      "completion_condition": "...",
      "completion_event": {{"type": "...", "entity_id": "..."}}
    }},
    "entities_to_create": []
  }}
}}"""


# ── Step Resolution Prompt (LLM Fallback) ────────────────────────────────────

def build_step_resolution_prompt(
    active_step: "QuestStep",
    quest: "Quest",
    recent_context: str,
    world_bible_cards: list["ContextCard"],
    world_state: "WorldState | None",
) -> str:
    return f"""{_DM_SYSTEM_BLOCK}

=== WORLD BIBLE ===
{_format_cards(world_bible_cards)}

=== WORLD STATE ===
{_format_world_state(world_state)}

=== ACTIVE QUEST ===
Title: {quest.title}
{_format_step(active_step, "ACTIVE STEP")}

=== RECENT EVENTS ===
{recent_context}

=== TASK ===
Based solely on the recent events above, determine whether the active step's completion
condition has been met. Do not invent outcomes; only confirm what the recent events show.

Respond with exactly this JSON:
{{
  "narrative": "One or two sentences narrating the outcome.",
  "updates": {{
    "quest_step_complete": true,
    "narrative_on_complete": "Brief prose describing how this step was completed."
  }}
}}

If the condition was NOT met, respond with:
{{
  "narrative": "One sentence noting what still needs to happen.",
  "updates": {{
    "quest_step_complete": false
  }}
}}"""


# ── Recovery Steps Prompt ─────────────────────────────────────────────────────

def build_recovery_steps_prompt(
    failed_step: "QuestStep",
    quest: "Quest",
    buffer_needed: int,
    world_bible_cards: list["ContextCard"],
    world_state: "WorldState | None",
) -> str:
    completed_text = "\n".join(
        f"  {i+1}. {s.description}" for i, s in enumerate(
            [quest.first_step] + quest.middle_steps
        ) if s.status == "completed"
    ) or "  (none)"

    return f"""{_DM_SYSTEM_BLOCK}

=== WORLD BIBLE ===
{_format_cards(world_bible_cards)}

=== WORLD STATE ===
{_format_world_state(world_state)}

=== ACTIVE QUEST ===
Title: {quest.title}
{_format_step(quest.last_step, "ULTIMATE GOAL")}

Completed so far:
{completed_text}

Failed step: "{failed_step.description}"
This step has become impossible or was not completed.

=== TASK ===
The party has hit a setback. Generate {buffer_needed} alternative middle step(s) that
create a new path toward the ultimate goal despite this failure. The steps should
acknowledge the setback implicitly — e.g., find an alternative method, seek a different
ally, take an indirect route — while still making narrative sense.

Respond with exactly this JSON:
{{
  "narrative": "A short paragraph describing how the party finds a new approach.",
  "updates": {{
    "recovery_steps": [
      {{
        "description": "...",
        "completion_condition": "...",
        "completion_event": {{"type": "...", "entity_id": "..."}}
      }}
    ],
    "entities_to_create": []
  }}
}}

The recovery_steps array must contain exactly {buffer_needed} step object(s).
completion_event may be omitted on any step that requires narrative judgment."""
