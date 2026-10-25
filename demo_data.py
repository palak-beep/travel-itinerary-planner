"""Canned data for Demo Mode, so the app works with no API key.

Costs below are per person in INR and are multiplied by the party size.
Coordinates are approximate.
"""
from __future__ import annotations

from typing import Dict, List

from models import SLOTS, Day, Itinerary, Preferences, RecommendationList

M, L, A, E = SLOTS


def _a(slot, title, desc, area, cat, cost_pp, lat, lng, tip=""):
    return dict(slot=slot, title=title, description=desc, area=area, category=cat,
                cost_pp=cost_pp, lat=lat, lng=lng, tip=tip)


JAIPUR_DAYS: List[dict] = [
    dict(theme="Pink City Classics", area="Old City", acts=[
        _a(M, "City Palace and Jantar Mantar", "Royal courtyards and the UNESCO-listed astronomical observatory, a short walk apart.",
           "Old City", "attraction", 700, 26.9258, 75.8237, "Arrive at opening time to beat tour groups."),
        _a(L, "Vegetarian thali at Laxmi Misthan Bhandar", "A Johari Bazaar institution for Rajasthani sweets and thalis.",
           "Johari Bazaar", "food", 450, 26.9187, 75.8266),
        _a(A, "Hawa Mahal and bazaar stroll", "Photograph the palace of winds, then browse bangles and textiles nearby.",
           "Old City", "leisure", 250, 26.9239, 75.8267, "Best light for the facade is early morning, so see it from a cafe."),
        _a(E, "Rooftop dinner facing Hawa Mahal", "Rajasthani dinner on a rooftop with the lit-up facade.",
           "Old City", "food", 900, 26.9235, 75.8270),
    ]),
    dict(theme="Forts of the Aravallis", area="Amer and Nahargarh", acts=[
        _a(M, "Amer Fort", "Hilltop fort with mirror palace and sweeping ramparts.", "Amer", "attraction", 600, 26.9855, 75.8513,
           "Book the jeep ride up in advance or walk up for a quieter start."),
        _a(L, "Local thali near Amer", "Simple, well-priced lunch at a family-run place close to the fort.", "Amer", "food", 350, 26.9870, 75.8520),
        _a(A, "Jaigarh Fort and cannon foundry", "Massive fort above Amer with panoramic views.", "Amer", "attraction", 400, 26.9857, 75.8238),
        _a(E, "Sunset and dinner at Nahargarh", "Watch the city light up from the ramparts, then dine at the fort restaurant.",
           "Nahargarh", "nightlife", 1100, 26.9373, 75.8153, "Carry a light jacket as it gets windy."),
    ]),
    dict(theme="Art, Gardens and Modern Jaipur", area="Central and C-Scheme", acts=[
        _a(M, "Albert Hall Museum", "Indo-Saracenic building with textiles, miniatures and a mummy.", "Ram Niwas Garden", "attraction", 400, 26.9118, 75.8195),
        _a(L, "Kachori and lassi stop", "Jaipur's famous pyaaz kachori, followed by a thick clay-cup lassi.", "Sindhi Camp", "food", 300, 26.9200, 75.7940),
        _a(A, "Birla Mandir and garden walk", "Marble temple on a hill with a calm garden, an easy low-effort afternoon.", "Moti Dungri", "leisure", 100, 26.8928, 75.8157),
        _a(E, "Patrika Gate and dinner in Jawahar Circle", "Colourful gateway and park, then dinner at a nearby restaurant.", "Jawahar Circle", "nightlife", 1000, 26.8523, 75.8082),
    ]),
    dict(theme="Crafts and Village Dinner", area="Sanganer and south", acts=[
        _a(M, "Block-printing workshop in Sanganer", "Hands-on hand-block printing session, then buy fabric direct from makers.", "Sanganer", "attraction", 800, 26.8250, 75.7960,
           "Book a slot a day ahead."),
        _a(L, "Rajasthani lunch in Sanganer", "Dal baati churma at a local eatery.", "Sanganer", "food", 350, 26.8230, 75.7980),
        _a(A, "Cafe stop and Sanganer temples", "A slow afternoon visiting Jain temples and a cafe.", "Sanganer", "leisure", 200, 26.8200, 75.7960),
        _a(E, "Chokhi Dhani folk dinner", "Rajasthani village-themed dinner with folk music and puppet shows.", "Chokhi Dhani", "nightlife", 1300, 26.7700, 75.8290),
    ]),
]

EMERGENCY_INDIA = dict(
    police="100 (or 112)", ambulance="102 (or 108)", fire="101",
    tourist_helpline="1363 (24x7 tourist helpline)",
    embassy_note="Foreign visitors: note your embassy or consulate number before you travel.",
)

RECOS: Dict[str, List[dict]] = {
    "Beach": [
        dict(city="Goa", country="India", why="Easy beaches, cafes and nightlife, with options for every budget.", best_season="Nov to Feb",
             weather_note="Dry and breezy, around 28 C.", daily_budget_usd=70, tags=["Beaches", "Nightlife", "Seafood"]),
        dict(city="Gokarna", country="India", why="Quieter cliffside beaches and a relaxed backpacker feel.", best_season="Oct to Mar",
             weather_note="Warm and dry, little rain.", daily_budget_usd=45, tags=["Quiet beaches", "Trekking", "Budget"]),
        dict(city="Havelock Island (Andamans)", country="India", why="Clear water, diving and some of India's best beaches.", best_season="Nov to Apr",
             weather_note="Calm seas and sunny.", daily_budget_usd=110, tags=["Diving", "Clear water", "Romantic"]),
    ],
    "Mountains": [
        dict(city="Manali", country="India", why="Snow peaks, river valleys and adventure sports within easy reach.", best_season="Mar to Jun, Dec to Feb for snow",
             weather_note="Cool to cold, snow in winter.", daily_budget_usd=60, tags=["Adventure", "Snow", "Treks"]),
        dict(city="Munnar", country="India", why="Rolling tea estates and misty viewpoints for slow travel.", best_season="Sep to Mar",
             weather_note="Mild and green, mist in the mornings.", daily_budget_usd=55, tags=["Tea gardens", "Relaxed", "Scenic"]),
        dict(city="Gangtok", country="India", why="Himalayan views, monasteries and nearby high-altitude lakes.", best_season="Mar to May, Oct to Dec",
             weather_note="Cool, with clear mountain views in autumn.", daily_budget_usd=65, tags=["Monasteries", "Views", "Culture"]),
    ],
    "Cultural": [
        dict(city="Jaipur", country="India", why="Forts, palaces, bazaars and food packed into a compact city.", best_season="Oct to Mar",
             weather_note="Pleasant days, cool evenings.", daily_budget_usd=60, tags=["Forts", "Crafts", "Food"]),
        dict(city="Varanasi", country="India", why="Ancient ghats, evening aarti and a deep spiritual atmosphere.", best_season="Oct to Mar",
             weather_note="Cool and dry.", daily_budget_usd=45, tags=["Spiritual", "History", "Street food"]),
        dict(city="Udaipur", country="India", why="Lakeside palaces and a romantic old town.", best_season="Sep to Mar",
             weather_note="Mild and sunny.", daily_budget_usd=75, tags=["Lakes", "Romantic", "Palaces"]),
    ],
    "Urban": [
        dict(city="Mumbai", country="India", why="Food, nightlife, art deco streets and the sea promenade.", best_season="Nov to Feb",
             weather_note="Warm and dry.", daily_budget_usd=80, tags=["Nightlife", "Food", "Art deco"]),
        dict(city="Delhi", country="India", why="Mughal monuments next to restaurants and markets.", best_season="Oct to Mar",
             weather_note="Cool and clear.", daily_budget_usd=65, tags=["History", "Street food", "Shopping"]),
        dict(city="Bengaluru", country="India", why="Craft breweries, gardens and a strong cafe culture.", best_season="Oct to Feb",
             weather_note="Mild year-round.", daily_budget_usd=60, tags=["Cafes", "Breweries", "Gardens"]),
    ],
}

# Keyword -> replacement activity (used by demo-mode swaps).
SWAP_POOL = [
    (("vegetarian", "vegan", "veg ", "jain"), _a(L, "Pure-veg thali at Rawat-style sweet shop", "Fully vegetarian Rajasthani thali with local sweets.",
                                                "Nearby", "food", 400, None, None)),
    (("market", "outdoor", "street", "bazaar"), _a(A, "Johari and Bapu bazaar walk", "Open-air bazaars for jewellery, textiles and snacks.",
                                                  "Old City", "leisure", 250, 26.9186, 75.8278)),
    (("museum", "indoor", "gallery"), _a(M, "Albert Hall Museum", "Indoor collection of textiles, miniatures and artefacts.",
                                         "Ram Niwas Garden", "attraction", 400, 26.9118, 75.8195)),
    (("spa", "relax", "rest", "slow"), _a(A, "Ayurvedic spa session", "Massage and tea in a quiet spa, an easy recovery afternoon.",
                                          "Central", "leisure", 1500, None, None)),
    (("night", "bar", "club", "music"), _a(E, "Live music evening at a rooftop lounge", "Cocktails and live music with city views.",
                                           "C-Scheme", "nightlife", 1600, None, None)),
    (("romantic", "sunset", "couple"), _a(E, "Sunset at Nahargarh with candle-lit dinner", "Golden-hour views followed by a private table.",
                                          "Nahargarh", "nightlife", 2200, 26.9373, 75.8153)),
]
DEFAULT_SWAP = _a(A, "Cooking class with a local family", "Learn three Rajasthani dishes and eat what you cook.",
                  "Central", "leisure", 1200, None, None)


def _activity(raw: dict, travellers: int) -> dict:
    out = {k: v for k, v in raw.items() if k != "cost_pp"}
    out["cost_local"] = raw["cost_pp"] * travellers
    out["lat"], out["lng"] = raw.get("lat"), raw.get("lng")
    return out


def demo_itinerary(prefs: Preferences) -> Itinerary:
    n = max(1, min(prefs.days, len(JAIPUR_DAYS)))
    days = []
    for i in range(n):
        src = JAIPUR_DAYS[i]
        days.append(dict(
            day_number=i + 1, theme=src["theme"], area_cluster=src["area"],
            activities=[_activity(a, prefs.travellers) for a in src["acts"]],
        ))
    data = dict(
        destination="Jaipur", country="India",
        summary="Sample plan: each day stays in one part of Jaipur, so you spend time at places instead of in traffic.",
        local_currency="INR", local_per_usd=prefs.inr_per_usd, emergency=EMERGENCY_INDIA,
        tips=["Carry small change for autos and street food.", "Dress modestly in temples and forts.",
              "Hydrate and use sunscreen as palace courtyards have little shade."],
        days=days, is_demo=True,
    )
    return Itinerary.from_dict(data)


def demo_recommendations(prefs: Preferences) -> RecommendationList:
    return RecommendationList.from_dict(RECOS.get(prefs.vibe, RECOS["Cultural"]))


def demo_swap(day: Day, slot, instruction: str, prefs: Preferences) -> Day:
    """Return a Day with one activity swapped, picked by keyword."""
    text = (instruction or "").lower()
    chosen = next((act for keys, act in SWAP_POOL if any(k in text for k in keys)), DEFAULT_SWAP)
    act = _activity(chosen, prefs.travellers)
    act["slot"] = slot or chosen["slot"]
    if not chosen["lat"]:  # keep the day's cluster: reuse a neighbour's coordinates
        anchor = next((a for a in day.activities if a.has_coords), None)
        if anchor:
            act["lat"], act["lng"] = anchor.lat, anchor.lng
    new = Day.from_dict(dict(day_number=day.day_number, theme=day.theme, area_cluster=day.area_cluster,
                             activities=[act]))
    # Day.merged_with only needs the replacement activity for slot swaps; for
    # whole-day regeneration in demo mode we swap that single slot too.
    target = act["slot"]
    return day.merged_with(new, target)
