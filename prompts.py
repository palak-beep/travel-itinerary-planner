"""All prompt engineering lives here, so it is easy to explain and tune."""
from __future__ import annotations

import json

from models import SLOTS, Day, Itinerary, Preferences

SYSTEM = (
    "You are a senior travel-planning engine for a SaaS product. "
    "Reply with ONE valid JSON object and nothing else: no markdown fences, no commentary. "
    "Only suggest real, well-known places and businesses. "
    "If you are unsure of a fact (a phone number, an exact price), say 'Verify locally' or give a cautious estimate."
)

ACTIVITY_SHAPE = (
    '{"slot": "<one of the four slot names>", "title": "place or activity", "description": "1-2 sentences", '
    '"area": "neighbourhood", "category": "attraction|food|leisure|nightlife|transport", '
    '"cost_local": 0, "lat": 0.0, "lng": 0.0, "tip": "short practical tip"}'
)

ITINERARY_SHAPE = (
    '{"destination": "City", "country": "Country", "summary": "2 sentences", '
    '"local_currency": "ISO code such as INR", "local_per_usd": 88.0, '
    '"emergency": {"police": "", "ambulance": "", "fire": "", "tourist_helpline": "", "embassy_note": ""}, '
    '"tips": ["3 to 5 short tips"], '
    '"days": [{"day_number": 1, "theme": "short theme", "area_cluster": "main zone of the day", '
    '"activities": [' + ACTIVITY_SHAPE + ', ...exactly four per day]}]}'
)

PACE_RULES = {
    "Relaxed": "ONE major attraction per day. Afternoon Leisure must be restful (cafe, park, spa). Avoid early starts.",
    "Moderate": "Up to two attractions per day with a calm afternoon. Balanced start times.",
    "Fast-Paced": "Two attractions per day plus a lively evening. Make full use of the day.",
}

BUDGET_RULES = {
    "Budget": "Budget travel: street food, local eateries, free or low-cost sights, public transport.",
    "Moderate": "Mid-range: good local restaurants, paid attractions are fine, occasional cab.",
    "Luxury": "Premium: fine dining, private experiences, signature venues, comfort first.",
}


def _slot_list() -> str:
    return "; ".join(f'"{s}"' for s in SLOTS)


def itinerary_prompt(p: Preferences) -> str:
    dest = p.destination.strip() or f"a top {p.vibe.lower()} destination"
    return f"""Create a {p.days}-day itinerary for {dest}.
Travel dates start: {p.month_text()} (account for weather, festivals and opening hours).
Travellers: {p.travellers} ({p.party}). Traveller's home country: {p.home_country}.
Budget level: {p.budget_level}. {BUDGET_RULES[p.budget_level]}
Pace: {p.pace}. {PACE_RULES[p.pace]}
Interests: {p.interests_text()}. Dietary needs: {p.diet}. Every food suggestion must respect them.

HARD RULES
1. Output exactly {p.days} days. Each day has exactly four activities, one per slot, in this order: {_slot_list()}.
2. GEOGRAPHIC CLUSTERING: keep all four activities of a day inside one neighbourhood or zone (roughly 5 km, unless a day trip is the point). Set "area_cluster" to that zone. Order the days so consecutive zones are near each other and the traveller never crosses the city back and forth.
3. Give realistic lat and lng for every activity (decimal degrees), so distances can be checked.
4. "cost_local" is the TOTAL estimated cost for all {p.travellers} traveller(s) for that activity, in the destination's local currency. Use 0 for free items. Exclude flights and hotels.
5. Do not repeat a place on different days. Match the interests.
6. Give "local_currency" (ISO code) and "local_per_usd" (approximate units of local currency per 1 USD).
7. Fill "emergency" with the destination country's real emergency numbers.

Return JSON in exactly this shape:
{ITINERARY_SHAPE}"""


def reco_prompt(p: Preferences) -> str:
    return f"""Recommend the 3 best destinations for this traveller.
Mood / vibe: {p.vibe}. Budget level: {p.budget_level}. Party: {p.party} ({p.travellers} people).
Trip length: {p.days} days, starting {p.month_text()}. Interests: {p.interests_text()}.
Traveller's home country: {p.home_country} (prefer destinations that are practical to reach).

Rules: pick destinations that are at their best in the travel month, fit the budget level, and genuinely match the vibe. Make the three options different from each other.
Return JSON in exactly this shape:
{{"recommendations": [{{"city": "", "country": "", "why": "one sentence", "best_season": "", "weather_note": "weather in the travel month", "daily_budget_usd": 0, "tags": ["3 short highlight tags"]}}, ...3 items]}}"""


def swap_prompt(p: Preferences, it: Itinerary, day: Day, slot: str | None, instruction: str) -> str:
    other_days = [f"Day {d.day_number}: " + ", ".join(a.title for a in d.activities)
                  for d in it.days if d.day_number != day.day_number]
    scope = (f'Change ONLY the "{slot}" activity. Keep the other three activities exactly as they are.'
             if slot else "Rebuild the whole day with new activities.")
    return f"""You are editing ONE day of an existing {len(it.days)}-day itinerary for {it.destination}.
Traveller details: {p.travellers} ({p.party}), {p.budget_level} budget, {p.pace} pace, interests {p.interests_text()}, diet {p.diet}.

Current Day {day.day_number} (JSON):
{json.dumps(day_to_plain(day))}

User request: "{instruction}"
{scope}

Rules:
- Stay inside the same area ("{day.area_cluster}") so the day does not need extra travel.
- Do not reuse places already in other days. Other days: {' | '.join(other_days) or 'none'}.
- Keep costs in {it.local_currency} for all {p.travellers} traveller(s) and keep lat/lng realistic.
- Return the COMPLETE day as JSON (day_number, theme, area_cluster, four activities), in this shape:
{{"day_number": {day.day_number}, "theme": "", "area_cluster": "", "activities": [{ACTIVITY_SHAPE}, ...]}}"""


def day_to_plain(day: Day) -> dict:
    from dataclasses import asdict
    return asdict(day)
