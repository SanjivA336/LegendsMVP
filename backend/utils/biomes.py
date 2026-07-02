from enum import Enum


class BiomeFamily(Enum):
    ARID     = 0
    GRASSLAND = 1
    WOODLAND  = 2
    TROPICAL  = 3
    WETLAND   = 4
    ARCTIC    = 5
    OCEAN     = 6
    MOUNTAIN  = 7
    VOLCANIC  = 8


class Biome:
    MAGIC_NUMBER = 10

    def __init__(self, id: int, name: str, tier: int, family: BiomeFamily):
        self.id: int = id
        self.name: str = name
        self.tier: int = tier
        self.family: BiomeFamily = family


class BiomeGraph:
    def __init__(self):
        self.biomes: dict[int, Biome] = {}
        self.transitions: dict[int, list[int]] = {}

    def add_biome(self, biome: Biome):
        self.biomes[biome.id] = biome
        if biome.id not in self.transitions:
            self.transitions[biome.id] = []

    def add_family(self, family: BiomeFamily, names: list[str]):
        for tier, name in enumerate(names, start=1):
            biome = Biome(
                id=family.value + (tier - 1) * Biome.MAGIC_NUMBER,
                name=name,
                tier=tier,
                family=family,
            )
            self.add_biome(biome)
            if tier > 1:
                # Bug fix from original sketch: only call once — method already adds both directions
                self.add_transition_dual_direction(biome.id - Biome.MAGIC_NUMBER, biome.id)

    def get_biome_by_id(self, biome_id: int) -> Biome | None:
        return self.biomes.get(biome_id)

    def get_biome_by_name(self, name: str) -> Biome | None:
        for biome in self.biomes.values():
            if biome.name == name:
                return biome
        return None

    def get_family(self, family: BiomeFamily) -> list[Biome]:
        return [b for b in self.biomes.values() if b.family == family]

    def get_tier(self, tier: int) -> list[Biome]:
        return [b for b in self.biomes.values() if b.tier == tier]

    def add_transition_dual_direction(self, from_id: int, to_id: int):
        if from_id not in self.transitions:
            self.transitions[from_id] = []
        self.transitions[from_id].append(to_id)

        if to_id not in self.transitions:
            self.transitions[to_id] = []
        self.transitions[to_id].append(from_id)

    def get_promotion(self, biome_id: int) -> Biome | None:
        biome = self.biomes.get(biome_id)
        if biome is None:
            raise ValueError(f"Biome ID {biome_id} not found.")
        if biome.tier >= 3:
            return None
        for neighbor_id in self.transitions.get(biome_id, []):
            neighbor = self.biomes.get(neighbor_id)
            if neighbor and neighbor.tier == biome.tier + 1 and neighbor.family == biome.family:
                return neighbor
        return None

    def get_demotion(self, biome_id: int) -> Biome | None:
        biome = self.biomes.get(biome_id)
        if biome is None:
            raise ValueError(f"Biome ID {biome_id} not found.")
        if biome.tier <= 1:
            return None
        for neighbor_id in self.transitions.get(biome_id, []):
            neighbor = self.biomes.get(neighbor_id)
            if neighbor and neighbor.tier == biome.tier - 1 and neighbor.family == biome.family:
                return neighbor
        return None

    def get_adjacent_families(self, biome_id: int) -> list[Biome]:
        """Returns T1 biomes of neighbouring families (only meaningful for T1 tiles)."""
        biome = self.biomes.get(biome_id)
        if biome is None:
            raise ValueError(f"Biome ID {biome_id} not found.")
        if biome.tier >= 3:
            return []
        return [
            self.biomes[n] for n in self.transitions.get(biome_id, [])
            if n in self.biomes
            and self.biomes[n].tier == biome.tier
            and self.biomes[n].family != biome.family
        ]

    def get_all_biomes(self) -> list[Biome]:
        return list(self.biomes.values())


# ── Global biome registry ──────────────────────────────────────────────────────

BIOMES = BiomeGraph()

BIOMES.add_family(BiomeFamily.ARID,      ["Savannah",     "Desert",           "Scorched Earth"   ])
BIOMES.add_family(BiomeFamily.GRASSLAND, ["Plains",       "Steppe",           "Barren Fields"    ])
BIOMES.add_family(BiomeFamily.WOODLAND,  ["Forest",       "Wild Forest",      "Ancient Forest"   ])
BIOMES.add_family(BiomeFamily.TROPICAL,  ["Rainforest",   "Jungle",           "Overgrown Jungle" ])
BIOMES.add_family(BiomeFamily.WETLAND,   ["Floodplains",  "Swamp",            "Blighted Swamp"   ])
BIOMES.add_family(BiomeFamily.ARCTIC,    ["Taiga",        "Frozen Tundra",    "Frozen Wastes"    ])
BIOMES.add_family(BiomeFamily.OCEAN,     ["Coast",        "Storm Sea",        "Abyssal Depths"   ])
BIOMES.add_family(BiomeFamily.MOUNTAIN,  ["Foothills",    "Broken Mountains", "Jagged Peaks"     ])
BIOMES.add_family(BiomeFamily.VOLCANIC,  ["Ash Foothills","Cinder Mountains", "Infernal Cauldron"])

# Cross-family adjacency (connects T1 biomes of ecologically neighbouring families)
_T = BiomeFamily
BIOMES.add_transition_dual_direction(_T.ARID.value,      _T.GRASSLAND.value)
BIOMES.add_transition_dual_direction(_T.ARID.value,      _T.VOLCANIC.value )
BIOMES.add_transition_dual_direction(_T.GRASSLAND.value, _T.WOODLAND.value )
BIOMES.add_transition_dual_direction(_T.GRASSLAND.value, _T.WETLAND.value  )
BIOMES.add_transition_dual_direction(_T.WOODLAND.value,  _T.TROPICAL.value )
BIOMES.add_transition_dual_direction(_T.WOODLAND.value,  _T.ARCTIC.value   )
BIOMES.add_transition_dual_direction(_T.TROPICAL.value,  _T.WETLAND.value  )
BIOMES.add_transition_dual_direction(_T.ARCTIC.value,    _T.MOUNTAIN.value )
BIOMES.add_transition_dual_direction(_T.MOUNTAIN.value,  _T.ARID.value     )
BIOMES.add_transition_dual_direction(_T.MOUNTAIN.value,  _T.VOLCANIC.value )

# Ocean T1 borders all other T1 biomes (coastlines can touch any terrain type)
for _f in [_T.ARID, _T.GRASSLAND, _T.WOODLAND, _T.TROPICAL,
           _T.WETLAND, _T.ARCTIC, _T.MOUNTAIN, _T.VOLCANIC]:
    BIOMES.add_transition_dual_direction(_T.OCEAN.value, _f.value)
