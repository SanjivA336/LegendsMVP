import math
import random
from pydantic import BaseModel, Field, field_validator, model_validator
from .shared import BaseDocument
from ..utils.biomes import BIOMES, BiomeFamily, Biome


class Tile(BaseModel):
    x: int
    y: int
    elevation: float
    is_water: bool
    biome_id: int | None = None
    biome_name: str | None = None
    tier: int | None = None       # 1, 2, or 3
    poi_candidate: bool = False
    poi_id: str | None = None     # stamped by POI Module on discovery


class WorldMapMeta(BaseModel):
    """WorldMap without tiles — used for list responses."""
    id: str
    adventure_id: str
    width: int
    height: int
    seed: int


class WorldMapGenerateRequest(BaseModel):
    adventure_id: str
    width: int = 64
    height: int = 64
    seed: int
    num_elevation_seeds: int = 2    # 1–3; each seed raises a mountain region
    percent_ocean: float = 0.30
    percent_mountain: float = 0.15
    volcano_chance: float = 0.35    # per elevation seed: probability of volcanic
    num_land_biomes: int = 6        # Voronoi seeds for Arid/Grassland/Woodland/Tropical/Wetland/Arctic
    poi_density: float = 0.04       # fraction of all tiles flagged as poi_candidate
    allowed_land_families: list[int] | None = None  # BiomeFamily.value ints; None = all families
    elevation_seed_positions: list[tuple[int, int]] | None = None  # manual placement; overrides num_elevation_seeds
    land_biome_seed_positions: list[tuple[int, int]] | None = None  # manual placement; overrides num_land_biomes

    @field_validator("width", "height")
    @classmethod
    def check_dimensions(cls, v: int) -> int:
        if not (8 <= v <= 128):
            raise ValueError("Map dimensions must be between 8 and 128")
        return v

    @field_validator("num_elevation_seeds")
    @classmethod
    def check_seeds(cls, v: int) -> int:
        if not (1 <= v <= 3):
            raise ValueError("num_elevation_seeds must be 1, 2, or 3")
        return v

    @model_validator(mode="after")
    def check_coverage(self) -> "WorldMapGenerateRequest":
        if self.percent_ocean + self.percent_mountain > 0.9:
            raise ValueError("percent_ocean + percent_mountain must be ≤ 0.9")

        if self.elevation_seed_positions is not None:
            if not (1 <= len(self.elevation_seed_positions) <= 3):
                raise ValueError("elevation_seed_positions must contain 1 to 3 coordinates")
            for x, y in self.elevation_seed_positions:
                if not (0 <= x < self.width and 0 <= y < self.height):
                    raise ValueError(f"elevation seed ({x}, {y}) is outside the map bounds")
            self.num_elevation_seeds = len(self.elevation_seed_positions)

        if self.land_biome_seed_positions is not None:
            if not (1 <= len(self.land_biome_seed_positions) <= 12):
                raise ValueError("land_biome_seed_positions must contain 1 to 12 coordinates")
            for x, y in self.land_biome_seed_positions:
                if not (0 <= x < self.width and 0 <= y < self.height):
                    raise ValueError(f"land biome seed ({x}, {y}) is outside the map bounds")
            self.num_land_biomes = len(self.land_biome_seed_positions)

        return self


class WorldMap(BaseDocument):
    width: int
    height: int
    seed: int
    tiles: list[Tile] = Field(default_factory=list)
    spawn_tile_x: int = 32
    spawn_tile_y: int = 32


# ── Generation Helpers ─────────────────────────────────────────────────────────

_LAND_FAMILIES = [
    BiomeFamily.ARID,
    BiomeFamily.GRASSLAND,
    BiomeFamily.WOODLAND,
    BiomeFamily.TROPICAL,
    BiomeFamily.WETLAND,
    BiomeFamily.ARCTIC,
]

_WARP_MAG = 8.0


def _place_elevation_seeds(
    width: int, height: int, num_seeds: int, rng: random.Random
) -> list[tuple[int, int]]:
    """Jittered strip placement: seeds stay spread across the map without looking symmetric."""
    strip_w = width / num_seeds
    return [
        (
            int((i + 0.25 + rng.random() * 0.5) * strip_w),
            int((0.2 + rng.random() * 0.6) * height),
        )
        for i in range(num_seeds)
    ]


def _build_elevation_map(
    width: int, height: int, seed: int, elevation_seeds: list[tuple[int, int]]
) -> list[list[float]]:
    """
    Layered Perlin noise base + Gaussian bumps at each elevation seed.
    Normalized to [0.0, 1.0].
    """
    from perlin_noise import PerlinNoise

    noise_fn = PerlinNoise(octaves=6, seed=seed)
    sigma = min(width, height) * 0.18
    peak = 2.0

    elev = []
    for y in range(height):
        row = []
        for x in range(width):
            e = float(noise_fn([x / width, y / height]))
            for sx, sy in elevation_seeds:
                dist_sq = (x - sx) ** 2 + (y - sy) ** 2
                e += peak * math.exp(-dist_sq / (2 * sigma ** 2))
            row.append(e)
        elev.append(row)

    flat = [v for row in elev for v in row]
    lo, hi = min(flat), max(flat)
    span = hi - lo or 1.0
    for y in range(height):
        for x in range(width):
            elev[y][x] = (elev[y][x] - lo) / span

    return elev


def _compute_warp(
    width: int, height: int, seed: int, warp_mag: float
) -> tuple[list[list[float]], list[list[float]]]:
    """
    Pre-compute Perlin domain-warp offsets for every tile.
    Uses offset coordinates (+1.0 to x or y) so wx and wy are decorrelated.
    """
    from perlin_noise import PerlinNoise

    nx = PerlinNoise(octaves=4, seed=seed + 1)
    ny = PerlinNoise(octaves=4, seed=seed + 2)

    wx = [
        [nx([x / width + 1.0, y / height]) * warp_mag for x in range(width)]
        for y in range(height)
    ]
    wy = [
        [ny([x / width, y / height + 1.0]) * warp_mag for x in range(width)]
        for y in range(height)
    ]
    return wx, wy


def _nearest_elevation_seed(x: int, y: int, seeds: list[tuple[int, int]]) -> int:
    return min(range(len(seeds)), key=lambda i: (x - seeds[i][0]) ** 2 + (y - seeds[i][1]) ** 2)


def _seed_pois(
    tiles: list[Tile], width: int, height: int, poi_density: float, rng: random.Random
) -> None:
    """Flag one random tile per jittered grid cell as poi_candidate across the whole map."""
    cell_size = max(1, int(math.sqrt(1.0 / max(poi_density, 0.001))))
    tile_by_pos = {(t.x, t.y): t for t in tiles}

    for cy in range(0, height, cell_size):
        for cx in range(0, width, cell_size):
            candidates = [
                (cx + dx, cy + dy)
                for dy in range(cell_size)
                for dx in range(cell_size)
                if (cx + dx, cy + dy) in tile_by_pos
            ]
            if candidates:
                tile_by_pos[rng.choice(candidates)].poi_candidate = True


# ── Biome Tier Assignment ──────────────────────────────────────────────────────

_DIRS4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def assign_land_biome_tiers(
    land_tiles: list[Tile],
    seed_families: dict[int, BiomeFamily],
    tile_seed_map: dict[tuple[int, int], int],
) -> None:
    """
    Assign tiers with roughly equal T1/T2/T3 distribution while preserving
    the adjacency contract: T2 and T3 tiles are NEVER adjacent to foreign
    borders (water, mountain, or a different land family).

    Algorithm:
      1. BFS from every foreign-touching tile inward, computing border_dist
         (distance from the nearest foreign border) for each land tile.
         This guarantees T2/T3 never appear at region edges.
      2. Find each connected same-family component via flood fill.
      3. Within each component split border_dist values at the 33rd and 66th
         percentile → T1 / T2 / T3 in roughly equal thirds.
    """
    from collections import deque

    # Step 1: map each land tile to its biome family
    family_of: dict[tuple[int, int], BiomeFamily] = {}
    for tile in land_tiles:
        seed_idx = tile_seed_map.get((tile.x, tile.y))
        if seed_idx is not None:
            family_of[(tile.x, tile.y)] = seed_families[seed_idx]
    if not family_of:
        return

    # Step 2: multi-source BFS — border_dist = distance from nearest foreign tile
    # (off-map / water / mountain / different family all count as "foreign")
    border_dist: dict[tuple[int, int], int] = {}
    queue: deque[tuple[int, int, int]] = deque()

    for tile in land_tiles:
        pos = (tile.x, tile.y)
        my_family = family_of.get(pos)
        if my_family is None:
            continue
        for dx, dy in _DIRS4:
            if family_of.get((tile.x + dx, tile.y + dy)) != my_family:
                if pos not in border_dist:
                    border_dist[pos] = 1
                    queue.append((tile.x, tile.y, 1))
                break

    while queue:
        x, y, d = queue.popleft()
        my_family = family_of.get((x, y))
        for dx, dy in _DIRS4:
            npos = (x + dx, y + dy)
            if npos not in border_dist and family_of.get(npos) == my_family:
                border_dist[npos] = d + 1
                queue.append((npos[0], npos[1], d + 1))

    # Step 3: flood-fill connected components within each family, then compute
    # per-component 33rd/66th percentile thresholds for a balanced tier split
    all_positions = set(family_of)
    visited: set[tuple[int, int]] = set()
    # per-position thresholds (t1_max, t2_max)
    thresholds: dict[tuple[int, int], tuple[int, int]] = {}

    for start in all_positions:
        if start in visited:
            continue
        start_family = family_of[start]
        component: list[tuple[int, int]] = []
        stack = [start]
        while stack:
            pos = stack.pop()
            if pos in visited or family_of.get(pos) != start_family:
                continue
            visited.add(pos)
            component.append(pos)
            x, y = pos
            for dx, dy in _DIRS4:
                npos = (x + dx, y + dy)
                if npos not in visited and family_of.get(npos) == start_family:
                    stack.append(npos)

        # Sort border_dist values within this component and split at ⅓ and ⅔
        dists = sorted(border_dist.get(p, 1) for p in component)
        n = len(dists)
        t1_max = dists[(n - 1) // 3]           # 33rd-percentile value
        t2_max = dists[min(n - 1, 2 * n // 3)] # 66th-percentile value
        t2_max = max(t1_max, t2_max)            # guard against ties
        for pos in component:
            thresholds[pos] = (t1_max, t2_max)

    # Step 4: stamp tier and biome onto each tile
    for tile in land_tiles:
        pos = (tile.x, tile.y)
        family = family_of.get(pos)
        if family is None:
            continue
        d = border_dist.get(pos, 1)
        t1_max, t2_max = thresholds.get(pos, (1, 2))
        tier = 1 if d <= t1_max else (2 if d <= t2_max else 3)
        biome = BIOMES.get_biome_by_id(family.value + (tier - 1) * Biome.MAGIC_NUMBER)
        tile.biome_id = biome.id if biome else None
        tile.biome_name = biome.name if biome else None
        tile.tier = tier


# ── Spawn Point Selection ──────────────────────────────────────────────────────

_SPAWN_EXCLUDED = {6, 7, 8}  # Ocean, Mountain, Volcanic — never spawn here


def _find_spawn_tile(tiles: list[Tile], width: int, height: int) -> tuple[int, int]:
    """
    Return (x, y) for the player's starting position.
    Strategy: find the largest connected region of T1 non-special land tiles,
    then pick the tile in that region with the most T1 land neighbors within
    a 2-tile radius (most sheltered / central T1 spot).
    """
    valid: set[tuple[int, int]] = {
        (t.x, t.y)
        for t in tiles
        if not t.is_water
        and t.tier == 1
        and t.biome_id is not None
        and (t.biome_id % 10) not in _SPAWN_EXCLUDED
    }

    if not valid:
        return (width // 2, height // 2)

    # BFS to find the largest connected T1 region (4-connected)
    visited: set[tuple[int, int]] = set()
    best: set[tuple[int, int]] = set()

    for start in valid:
        if start in visited:
            continue
        component: set[tuple[int, int]] = set()
        stack = [start]
        while stack:
            pos = stack.pop()
            if pos in visited or pos not in valid:
                continue
            visited.add(pos)
            component.add(pos)
            x, y = pos
            for dx, dy in _DIRS4:
                npos = (x + dx, y + dy)
                if npos not in visited and npos in valid:
                    stack.append(npos)
        if len(component) > len(best):
            best = component

    # Score each tile by T1 land neighbors in a 2-tile radius
    def score(pos: tuple[int, int]) -> int:
        x, y = pos
        return sum(
            1 for dy in range(-2, 3) for dx in range(-2, 3)
            if (dx != 0 or dy != 0) and (x + dx, y + dy) in valid
        )

    # Centroid of best component — tiebreak toward center
    cx = sum(p[0] for p in best) // len(best)
    cy = sum(p[1] for p in best) // len(best)

    return max(
        best,
        key=lambda p: (score(p), -(abs(p[0] - cx) + abs(p[1] - cy))),
    )


# ── Generation Entry Point ─────────────────────────────────────────────────────

def generate_world_map(request: WorldMapGenerateRequest) -> WorldMap:
    rng = random.Random(request.seed)
    width, height = request.width, request.height

    # Steps 1–2: elevation seeds + elevation grid
    elevation_seeds = request.elevation_seed_positions or _place_elevation_seeds(
        width, height, request.num_elevation_seeds, rng
    )
    elev = _build_elevation_map(width, height, request.seed, elevation_seeds)

    # Step 3: sea level and mountain level by percentile
    flat_sorted = sorted(elev[y][x] for y in range(height) for x in range(width))
    n = len(flat_sorted)
    if request.percent_ocean <= 0:
        sea_level = -1.0       # elevation is normalized to [0,1] -- nothing can be <= -1.0
    else:
        sea_level = flat_sorted[max(0, int(request.percent_ocean * n) - 1)]
    if request.percent_mountain <= 0:
        mountain_level = 2.0   # nothing can be >= 2.0
    else:
        mountain_level = flat_sorted[min(n - 1, int((1.0 - request.percent_mountain) * n))]

    # Step 4: volcanic seed lottery
    seed_is_volcanic = {i: rng.random() < request.volcano_chance for i in range(len(elevation_seeds))}

    # Step 7: Voronoi seeds for land biomes
    land_positions = [
        (x, y)
        for y in range(height)
        for x in range(width)
        if sea_level < elev[y][x] < mountain_level
    ]
    if request.land_biome_seed_positions:
        raw_positions = request.land_biome_seed_positions
        num_seeds = len(raw_positions)
    else:
        num_seeds = min(request.num_land_biomes, len(land_positions))
        raw_positions = rng.sample(land_positions, num_seeds) if land_positions else []
    land_seed_pos: dict[int, tuple[int, int]] = dict(enumerate(raw_positions))

    active_families = (
        [f for f in _LAND_FAMILIES if f.value in request.allowed_land_families]
        if request.allowed_land_families
        else _LAND_FAMILIES
    ) or _LAND_FAMILIES
    shuffled_families = active_families.copy()
    rng.shuffle(shuffled_families)
    seed_families: dict[int, BiomeFamily] = {
        i: shuffled_families[i % len(shuffled_families)] for i in range(num_seeds)
    }

    # Steps 7 + 9: pre-compute domain warp offsets for land Voronoi assignment
    warp_x, warp_y = _compute_warp(width, height, request.seed, _WARP_MAG)

    # Build tiles
    tiles: list[Tile] = []
    tile_seed_map: dict[tuple[int, int], int] = {}

    for y in range(height):
        for x in range(width):
            e = elev[y][x]

            if e <= sea_level:
                # Ocean: tier by depth (higher elevation = shallower = T1 Coast)
                depth_norm = (e / sea_level) if sea_level > 0 else 1.0
                tier = 1 if depth_norm >= 0.66 else (2 if depth_norm >= 0.33 else 3)
                biome = BIOMES.get_biome_by_id(BiomeFamily.OCEAN.value + (tier - 1) * Biome.MAGIC_NUMBER)
                tiles.append(Tile(
                    x=x, y=y, elevation=round(e, 4), is_water=True,
                    biome_id=biome.id if biome else None,
                    biome_name=biome.name if biome else None,
                    tier=tier,
                ))

            elif e >= mountain_level:
                # Mountain/Volcanic: tier by elevation (higher = more dangerous)
                nearest = _nearest_elevation_seed(x, y, elevation_seeds)
                family = BiomeFamily.VOLCANIC if seed_is_volcanic[nearest] else BiomeFamily.MOUNTAIN
                mtn_norm = (e - mountain_level) / ((1.0 - mountain_level) or 1.0)
                tier = 1 if mtn_norm <= 0.33 else (2 if mtn_norm <= 0.66 else 3)
                biome = BIOMES.get_biome_by_id(family.value + (tier - 1) * Biome.MAGIC_NUMBER)
                tiles.append(Tile(
                    x=x, y=y, elevation=round(e, 4), is_water=False,
                    biome_id=biome.id if biome else None,
                    biome_name=biome.name if biome else None,
                    tier=tier,
                ))

            else:
                # Land: Voronoi with pre-computed domain warp (Steps 7 + 9)
                if land_seed_pos:
                    wx = x + warp_x[y][x]
                    wy = y + warp_y[y][x]
                    nearest_seed = min(
                        land_seed_pos,
                        key=lambda i: (wx - land_seed_pos[i][0]) ** 2 + (wy - land_seed_pos[i][1]) ** 2,
                    )
                    tile_seed_map[(x, y)] = nearest_seed
                tiles.append(Tile(x=x, y=y, elevation=round(e, 4), is_water=False))

    # Step 8: land tier grading via border-distance BFS
    land_tiles = [t for t in tiles if not t.is_water and t.biome_id is None]
    assign_land_biome_tiers(land_tiles, seed_families, tile_seed_map)

    # Step 9: find safe spawn tile (largest T1 land region, most sheltered point)
    spawn_x, spawn_y = _find_spawn_tile(tiles, width, height)

    # Step 10: POI seeding across the whole map
    _seed_pois(tiles, width, height, request.poi_density, rng)

    return WorldMap(
        adventure_id=request.adventure_id,
        width=width,
        height=height,
        seed=request.seed,
        tiles=tiles,
        spawn_tile_x=spawn_x,
        spawn_tile_y=spawn_y,
    )
