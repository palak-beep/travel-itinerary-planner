"""Data models and validation for the Travel Itinerary Planner.

Plain dataclasses with strict `from_dict` validators. Everything the LLM returns
is parsed through these, so malformed AI output is rejected (and retried)
instead of crashing the UI.
"""
from __future__ import annotations

import copy
import datetime as dt
import re
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, List, Optional

SLOTS = [
    "Morning Sightseeing",
    "Lunch",
    "Afternoon Leisure",
    "Evening Dining & Entertainment",
]

BUDGET_LEVELS = ["Budget", "Moderate", "Luxury"]
PARTIES = ["Solo", "Couple", "Family", "Friends"]
PACES = ["Relaxed", "Moderate", "Fast-Paced"]
VIBES = ["Beach", "Mountains", "Cultural", "Urban"]
INTERESTS = ["Food", "Adventure", "History", "Nightlife", "Nature", "Shopping", "Wellness", "Art"]
DIETS = ["No restriction", "Vegetarian", "Vegan", "Halal", "Jain"]

# Rough fallback rates (local currency per 1 USD) used only if the AI omits one.
FALLBACK_RATES = {
    "USD": 1.0, "INR": 88.0, "EUR": 0.92, "GBP": 0.78, "JPY": 150.0, "THB": 35.0,
    "IDR": 16000.0, "AED": 3.67, "SGD": 1.34, "AUD": 1.52, "CAD": 1.37, "VND": 25000.0,
    "MYR": 4.4, "LKR": 300.0, "NPR": 140.0, "TRY": 40.0, "CHF": 0.88,
}


class ModelError(ValueError):
    """Raised when data does not match the expected structure."""


# ----------------------------------------------------------------- helpers
def _num(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    found = re.findall(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
    return float(found[0]) if found else default


def _str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _coord(value: Any, limit: float) -> Optional[float]:
    if value is None or value == "":
        return None
    n = _num(value, float("nan"))
    if n != n or abs(n) > limit:  # NaN or out of range
        return None
    return n


def normalize_slot(value: Any) -> str:
    t = _str(value).lower()
    if "morning" in t:
        return SLOTS[0]
    if "lunch" in t:
        return SLOTS[1]
    if "afternoon" in t:
        return SLOTS[2]
    if "evening" in t or "dinner" in t or "night" in t:
        return SLOTS[3]
    return _str(value) or SLOTS[0]


def _slot_rank(slot: str) -> int:
    return SLOTS.index(slot) if slot in SLOTS else 99


# ------------------------------------------------------------------ models
@dataclass
class Activity:
    slot: str
    title: str
    description: str = ""
    area: str = ""
    category: str = "attraction"  # attraction | food | leisure | nightlife | transport
    cost_local: float = 0.0       # total for the whole travel party, local currency
    lat: Optional[float] = None
    lng: Optional[float] = None
    tip: str = ""

    @classmethod
    def from_dict(cls, d: Any) -> "Activity":
        if not isinstance(d, dict):
            raise ModelError("Each activity must be an object.")
        title = _str(d.get("title") or d.get("name"))
        if not title:
            raise ModelError("An activity is missing its title.")
        lat = _coord(d.get("lat", d.get("latitude")), 90)
        lng = _coord(d.get("lng", d.get("lon", d.get("longitude"))), 180)
        if lat is None or lng is None:
            lat = lng = None
        return cls(
            slot=normalize_slot(d.get("slot")),
            title=title,
            description=_str(d.get("description")),
            area=_str(d.get("area")),
            category=_str(d.get("category"), "attraction").lower() or "attraction",
            cost_local=max(_num(d.get("cost_local", d.get("cost"))), 0.0),
            lat=lat,
            lng=lng,
            tip=_str(d.get("tip")),
        )

    @property
    def has_coords(self) -> bool:
        return self.lat is not None and self.lng is not None


@dataclass
class Day:
    day_number: int
    theme: str
    activities: List[Activity]
    area_cluster: str = ""

    @classmethod
    def from_dict(cls, d: Any) -> "Day":
        if not isinstance(d, dict):
            raise ModelError("Each day must be an object.")
        acts = d.get("activities")
        if not isinstance(acts, list) or not acts:
            raise ModelError("A day has no activities.")
        return cls(
            day_number=int(_num(d.get("day_number"), 1)),
            theme=_str(d.get("theme"), "Explore"),
            area_cluster=_str(d.get("area_cluster")),
            activities=[Activity.from_dict(a) for a in acts],
        )

    def sorted_activities(self) -> List[Activity]:
        return sorted(self.activities, key=lambda a: _slot_rank(a.slot))

    def total_local(self) -> float:
        return sum(a.cost_local for a in self.activities)

    def merged_with(self, new_day: "Day", slot: Optional[str]) -> "Day":
        """Return this day with only `slot` replaced from `new_day`.

        If slot is None the whole day is replaced. This guarantees a single-slot
        swap can never wipe the rest of the day, even if the AI over-edits.
        """
        if not slot:
            out = copy.deepcopy(new_day)
            out.day_number = self.day_number
            return out
        replacement = next((a for a in new_day.activities if a.slot == slot), None)
        if replacement is None:
            raise ModelError(f"The AI reply did not include a '{slot}' activity.")
        out = copy.deepcopy(self)
        out.activities = [a for a in out.activities if a.slot != slot] + [copy.deepcopy(replacement)]
        out.activities = out.sorted_activities()
        return out


@dataclass
class Emergency:
    police: str = "Verify locally"
    ambulance: str = "Verify locally"
    fire: str = "Verify locally"
    tourist_helpline: str = "Verify locally"
    embassy_note: str = "Note your embassy or consulate contact before you travel."

    @classmethod
    def from_dict(cls, d: Any) -> "Emergency":
        if not isinstance(d, dict):
            return cls()
        base = cls()
        return cls(**{f.name: (_str(d.get(f.name)) or getattr(base, f.name)) for f in fields(cls)})


@dataclass
class Itinerary:
    destination: str
    days: List[Day]
    country: str = ""
    summary: str = ""
    local_currency: str = "USD"
    local_per_usd: float = 1.0
    emergency: Emergency = field(default_factory=Emergency)
    tips: List[str] = field(default_factory=list)
    is_demo: bool = False

    @classmethod
    def from_dict(cls, d: Any) -> "Itinerary":
        if not isinstance(d, dict):
            raise ModelError("The itinerary must be a JSON object.")
        days = d.get("days")
        if not isinstance(days, list) or not days:
            raise ModelError("The itinerary has no days.")
        code = (_str(d.get("local_currency"), "USD").upper() or "USD")[:5]
        rate = _num(d.get("local_per_usd"), 0.0)
        if rate <= 0:
            rate = FALLBACK_RATES.get(code, 1.0)
        tips = d.get("tips")
        return cls(
            destination=_str(d.get("destination"), "Your destination"),
            country=_str(d.get("country")),
            summary=_str(d.get("summary")),
            local_currency=code,
            local_per_usd=rate,
            emergency=Emergency.from_dict(d.get("emergency")),
            tips=[_str(t) for t in tips if _str(t)] if isinstance(tips, list) else [],
            days=[Day.from_dict(x) for x in days],
            is_demo=bool(d.get("is_demo", False)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def total_local(self) -> float:
        return sum(d.total_local() for d in self.days)

    def normalize(self, n_days: int) -> "Itinerary":
        """Sort, renumber 1..n and trim extra days the AI may have added."""
        self.days.sort(key=lambda d: d.day_number)
        self.days = self.days[: max(n_days, 1)]
        for i, d in enumerate(self.days, start=1):
            d.day_number = i
            d.activities = d.sorted_activities()
        return self


@dataclass
class Preferences:
    destination: str = ""
    vibe: str = "Cultural"
    days: int = 3
    start_date: str = ""  # ISO date
    budget_level: str = "Moderate"
    party: str = "Couple"
    travellers: int = 2
    pace: str = "Moderate"
    interests: List[str] = field(default_factory=lambda: ["Food", "History"])
    diet: str = "No restriction"
    home_country: str = "India"
    inr_per_usd: float = 88.0
    custom_budget_usd: float = 0.0  # 0 = use the budget-level benchmark

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Any) -> "Preferences":
        if not isinstance(d, dict):
            return cls()
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in names})

    def month_text(self) -> str:
        try:
            return dt.date.fromisoformat(self.start_date).strftime("%B %Y")
        except (ValueError, TypeError):
            return "an unspecified month"

    def interests_text(self) -> str:
        return ", ".join(self.interests) if self.interests else "general sightseeing"


@dataclass
class Recommendation:
    city: str
    country: str = ""
    why: str = ""
    best_season: str = ""
    weather_note: str = ""
    daily_budget_usd: float = 0.0
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Any) -> "Recommendation":
        if not isinstance(d, dict):
            raise ModelError("Each recommendation must be an object.")
        city = _str(d.get("city"))
        if not city:
            raise ModelError("A recommendation is missing its city.")
        tags = d.get("tags")
        return cls(
            city=city,
            country=_str(d.get("country")),
            why=_str(d.get("why")),
            best_season=_str(d.get("best_season")),
            weather_note=_str(d.get("weather_note")),
            daily_budget_usd=_num(d.get("daily_budget_usd")),
            tags=[_str(t) for t in tags if _str(t)][:5] if isinstance(tags, list) else [],
        )


@dataclass
class RecommendationList:
    recommendations: List[Recommendation]

    @classmethod
    def from_dict(cls, d: Any) -> "RecommendationList":
        items = d.get("recommendations") if isinstance(d, dict) else d
        if not isinstance(items, list) or not items:
            raise ModelError("No destination recommendations were returned.")
        return cls([Recommendation.from_dict(x) for x in items])
