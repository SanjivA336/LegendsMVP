"""
Pure prompt-building for the World Creation Wizard's theme-expand call.

Free of I/O and side effects, matching the convention in quest_prompts.py. Unlike the
DM narrative prompts elsewhere in the app, this call isn't narrating anything in-world --
it just expands a one-line pitch into a starter bundle of world-naming choices the wizard
pre-fills (all editable afterward), so its JSON contract skips the narrative/updates
wrapper and returns the bundle directly.
"""

from ..models.worldbible import DEFAULT_ATTRIBUTE_NAMES
from ..utils.biomes import BiomeFamily

_BIOME_FAMILY_KEYS = [f.name.lower() for f in BiomeFamily]
_ATTRIBUTE_KEYS = list(DEFAULT_ATTRIBUTE_NAMES.keys())


def build_theme_expand_prompt(pitch: str) -> str:
    attr_lines = "\n".join(f'    "{k}": "..."' for k in _ATTRIBUTE_KEYS)
    biome_lines = "\n".join(f'    "{k}": "..."' for k in _BIOME_FAMILY_KEYS)

    return f"""You are helping a tabletop RPG creator flesh out a new campaign world from a
short pitch. Do not narrate a story -- generate flavorful naming choices only.

=== PITCH ===
{pitch}

=== TASK ===
Given the pitch above, suggest:
- world_name: a short evocative name for this world/setting
- attribute_names: a re-themed display name for each of these character attribute keys
  (e.g. "strength" might become "Might" in a wild-west setting) -- every key below must
  appear, unchanged if no re-theming fits
- currency_name: what money is called in this setting (e.g. "Gold", "Credits", "Caps")
- biome_family_names: a re-themed display name for each of these terrain family keys --
  every key below must appear

Respond with exactly this JSON (no extra keys, no markdown fences):
{{
  "world_name": "...",
  "attribute_names": {{
{attr_lines}
  }},
  "currency_name": "...",
  "biome_family_names": {{
{biome_lines}
  }}
}}"""
