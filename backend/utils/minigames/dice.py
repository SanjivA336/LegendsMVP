import random

# Six symmetric tiers, in order from worst to best.
TIER_LABELS = ["Critical Failure", "Major Failure", "Failure", "Success", "Major Success", "Critical Success"]

# Matches the color sequence the tiers are meant to render as: red, orange, yellow, green, blue, purple.
TIER_COLORS = {
    "Critical Failure": "#E63946",
    "Major Failure": "#F8961E",
    "Failure": "#F5D547",
    "Success": "#4CAF50",
    "Major Success": "#4CC9F0",
    "Critical Success": "#9B5DE5",
}


def _effective_roll(rolls: list[int], adv_disadv: int) -> int:
    if not rolls:
        return 1
    if adv_disadv > 0:
        return max(rolls)
    if adv_disadv < 0:
        return min(rolls)
    return rolls[0]


def _score_from_roll(roll: int, target: float, die_size: int) -> float:
    if roll <= 1:
        return -1.0
    if roll >= die_size:
        return 1.0
    if roll < target:
        denom = max(target - 1, 1)
        return -1.0 + (roll - 1) / denom
    denom = max(die_size - target, 1)
    return (roll - target) / denom


def tier_label_for_roll(roll: int, target: float, die_size: int) -> str:
    if roll <= 1:
        return "Critical Failure"
    if roll >= die_size:
        return "Critical Success"
    if roll < target:
        mid = (1 + target) / 2
        return "Major Failure" if roll <= mid else "Failure"
    mid = (target + die_size) / 2
    return "Major Success" if roll >= mid else "Success"


def roll_and_score(die_size: int, target: float, adv_disadv: int = 0) -> tuple[dict, float]:
    """Roll server-side (used for Actor auto-rolls) and return (raw_result, score)."""
    num_rolls = 2 if adv_disadv != 0 else 1
    rolls = [random.randint(1, die_size) for _ in range(num_rolls)]
    effective = _effective_roll(rolls, adv_disadv)
    score = _score_from_roll(effective, target, die_size)
    raw_result = {"rolls": rolls, "die": die_size, "effective": effective}
    return raw_result, score


def score_from_raw(raw_result: dict, target: float) -> float:
    """Compute the authoritative score from a client-submitted raw roll."""
    die_size = raw_result.get("die", 20)
    rolls = raw_result.get("rolls", [])
    effective = raw_result.get("effective")
    if effective is None:
        effective = max(rolls) if rolls else 1
    return _score_from_roll(effective, target, die_size)


def tier_label(raw_result: dict, target: float) -> str:
    die_size = raw_result.get("die", 20)
    rolls = raw_result.get("rolls", [])
    effective = raw_result.get("effective")
    if effective is None:
        effective = max(rolls) if rolls else 1
    return tier_label_for_roll(effective, target, die_size)


def roll_sum(count: int, sides: int, bonus: int = 0) -> int:
    """Roll `count` dice of `sides` sides, sum them, add a flat bonus. Used for weapon
    damage/hit rolls (a plain rolled total) -- distinct from roll_and_score's skill-check
    math (a -1..1 outcome against a target), since damage isn't a success/fail score.
    """
    return sum(random.randint(1, sides) for _ in range(count)) + bonus
