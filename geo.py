"""Geographic helpers: distance, transit load, and cross-day route optimisation.

The AI proposes coordinates for each activity. These are approximate, so the
numbers here are a planning aid (relative comparison), not turn-by-turn routing.
"""
from __future__ import annotations

import copy
import math
from collections import Counter
from itertools import permutations
from typing import List, Optional, Tuple

from models import SLOTS, Day, Itinerary

SIGHT_SLOTS = (SLOTS[0], SLOTS[2])  # Morning Sightseeing, Afternoon Leisure


def haversine(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Great-circle distance in km."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(min(1.0, math.sqrt(h)))


def day_points(day: Day) -> List[Tuple[float, float]]:
    return [(a.lat, a.lng) for a in day.sorted_activities() if a.has_coords]


def day_km(day: Day) -> float:
    pts = day_points(day)
    return sum(haversine(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def total_km(it: Itinerary) -> float:
    return sum(day_km(d) for d in it.days)


def has_geo_data(it: Itinerary) -> bool:
    return any(len(day_points(d)) >= 2 for d in it.days)


def transit_label(km: float, n_points: int) -> str:
    if n_points < 2:
        return "Route unavailable"
    if km < 6:
        return "Light transit"
    if km < 15:
        return "Moderate transit"
    return "Heavy transit"


def _mean(points: List[Tuple[float, float]]) -> Tuple[float, float]:
    return (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))


def optimize_sightseeing(it: Itinerary) -> Tuple[Itinerary, float, float]:
    """Re-cluster sightseeing stops across days to cut total travel distance.

    1. Collect all morning/afternoon stops that have coordinates.
    2. Group them into one cluster per day (capacity-constrained k-means,
       farthest-point seeding so clusters start spread out).
    3. Give each cluster to the day whose lunch/dinner is closest to it.
    4. Order the stops inside each day to minimise that day's distance.

    Returns (itinerary, km_before, km_after). If nothing improves, the original
    itinerary is returned unchanged with before == after.
    """
    before = total_km(it)
    n = len(it.days)

    def is_pool(a) -> bool:
        return a.slot in SIGHT_SLOTS and a.has_coords

    pool = [a for d in it.days for a in d.activities if is_pool(a)]
    if n < 2 or len(pool) < n or len(pool) > 2 * n:
        return it, before, before

    pts = [(a.lat, a.lng) for a in pool]
    cap = min(2, math.ceil(len(pool) / n))
    centre = _mean(pts)

    seeds = [max(range(len(pts)), key=lambda i: haversine(pts[i], centre))]
    while len(seeds) < n:
        rest = [i for i in range(len(pts)) if i not in seeds]
        seeds.append(max(rest, key=lambda i: min(haversine(pts[i], pts[s]) for s in seeds)))
    centroids = [pts[s] for s in seeds]

    assign: List[Optional[int]] = [None] * len(pts)
    for _ in range(10):
        pairs = sorted((haversine(p, c), i, j) for i, p in enumerate(pts) for j, c in enumerate(centroids))
        counts = [0] * n
        new: List[Optional[int]] = [None] * len(pts)
        for _, i, j in pairs:
            if new[i] is None and counts[j] < cap:
                new[i] = j
                counts[j] += 1
        for j in range(n):
            members = [pts[i] for i in range(len(pts)) if new[i] == j]
            if members:
                centroids[j] = _mean(members)
        if new == assign:
            break
        assign = new

    clusters = {j: [i for i in range(len(pts)) if assign[i] == j] for j in range(n)}

    # Anchor of each day = where its non-sightseeing stops (lunch, dinner) are.
    anchors = []
    for d in it.days:
        fixed = [(a.lat, a.lng) for a in d.activities if a.has_coords and not is_pool(a)]
        current = [(a.lat, a.lng) for a in d.activities if is_pool(a)]
        anchors.append(_mean(fixed) if fixed else (_mean(current) if current else None))

    options = sorted(
        (haversine(centroids[j], anchors[d]) if anchors[d] else 0.0, j, d)
        for j in range(n) for d in range(n) if clusters[j]
    )
    day_for_cluster, used_days = {}, set()
    for _, j, d in options:
        if j not in day_for_cluster and d not in used_days:
            day_for_cluster[j] = d
            used_days.add(d)
    cluster_for_day = {d: j for j, d in day_for_cluster.items()}

    result = copy.deepcopy(it)
    for d_idx, day in enumerate(result.days):
        kept = [a for a in day.activities if not is_pool(a)]
        j = cluster_for_day.get(d_idx)
        members = [copy.deepcopy(pool[i]) for i in clusters.get(j, [])] if j is not None else []
        occupied = {a.slot for a in kept}
        free = [s for s in SIGHT_SLOTS if s not in occupied]
        if len(members) > len(free):
            return it, before, before

        best, best_km = None, float("inf")
        for perm in permutations(free, len(members)):
            trial = copy.deepcopy(day)
            trial.activities = list(kept)
            for slot, member in zip(perm, members):
                m = copy.deepcopy(member)
                m.slot = slot
                trial.activities.append(m)
            km = day_km(trial)
            if km < best_km:
                best, best_km = trial, km
        if best is None:  # no members for this day: keep it as it was
            best = copy.deepcopy(day)
            best.activities = list(kept)
        best.activities = best.sorted_activities()
        areas = Counter(a.area for a in best.activities if a.area)
        if areas and members:
            best.area_cluster = areas.most_common(1)[0][0]
            best.theme = f"Around {best.area_cluster}"
        result.days[d_idx] = best

    after = total_km(result)
    if after < before - 0.05:
        return result, before, after
    return it, before, before
