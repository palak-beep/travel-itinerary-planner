"""Run with:  python tests/test_core.py   (or: pytest)"""
import copy
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["TRIPS_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "t.db")

import demo_data, geo, llm, storage  # noqa: E402
from models import SLOTS, Day, Itinerary, ModelError, Preferences, RecommendationList  # noqa: E402
from pdf_export import build_pdf, safe  # noqa: E402

PREFS = Preferences(destination="Jaipur", days=4, travellers=2, start_date="2026-12-01")


def test_demo_itinerary_shape():
    it = demo_data.demo_itinerary(PREFS)
    assert len(it.days) == 4
    for d in it.days:
        assert [a.slot for a in d.sorted_activities()] == SLOTS
    assert it.total_local() > 0
    # costs scale with party size
    solo = demo_data.demo_itinerary(Preferences(days=4, travellers=1))
    assert abs(it.total_local() - 2 * solo.total_local()) < 1e-6


def test_roundtrip_dict():
    it = demo_data.demo_itinerary(PREFS)
    again = Itinerary.from_dict(it.to_dict())
    assert again.to_dict() == it.to_dict()


def test_validation_rejects_bad_data():
    for bad in ({}, {"days": []}, {"days": [{"activities": []}]}, {"days": [{"activities": [{"title": ""}]}]}, []):
        try:
            Itinerary.from_dict(bad)
        except ModelError:
            continue
        raise AssertionError(f"accepted bad data: {bad}")


def test_coercion_of_messy_ai_output():
    it = Itinerary.from_dict({
        "destination": "X", "local_currency": "eur", "local_per_usd": "0",
        "days": [{"day_number": "2", "activities": [
            {"slot": "morning", "title": "A", "cost": "EUR 1,200-1,500", "latitude": "95", "longitude": 10},
            {"slot": "Dinner time", "name": "B", "cost_local": None, "lat": 1, "lng": 2}]}]})
    a, b = it.days[0].activities
    assert a.slot == SLOTS[0] and a.cost_local == 1200.0 and not a.has_coords  # lat 95 is invalid
    assert b.slot == SLOTS[3] and b.has_coords
    assert it.local_currency == "EUR" and 0.5 < it.local_per_usd < 1.5  # fallback rate


def test_normalize_trims_and_renumbers():
    it = demo_data.demo_itinerary(PREFS)
    it.days[0].day_number, it.days[3].day_number = 9, 0
    it.normalize(3)
    assert [d.day_number for d in it.days] == [1, 2, 3]


def test_extract_json_variants():
    assert llm.extract_json('{"a": 1}') == {"a": 1}
    assert llm.extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert llm.extract_json('Sure! Here it is: {"a": [1, 2]} hope it helps') == {"a": [1, 2]}


def test_generate_retries_once(monkeypatch=None):
    replies = ["not json at all", '{"recommendations": [{"city": "Goa"}]}']
    original = llm.call_llm
    llm.call_llm = lambda cfg, system, prompt, temperature=0.7: replies.pop(0)
    try:
        out = llm.generate(RecommendationList.from_dict, llm.LLMConfig("Groq", "k", "m"), "s", "p")
        assert out.recommendations[0].city == "Goa" and not replies
    finally:
        llm.call_llm = original


def test_single_slot_swap_keeps_rest_of_day():
    it = demo_data.demo_itinerary(PREFS)
    day = it.days[0]
    new = demo_data.demo_swap(day, SLOTS[1], "find a vegetarian lunch spot", PREFS)
    merged = day.merged_with(new, SLOTS[1])
    before = {a.slot: a.title for a in day.activities}
    after = {a.slot: a.title for a in merged.activities}
    assert after[SLOTS[1]] != before[SLOTS[1]]
    for s in (SLOTS[0], SLOTS[2], SLOTS[3]):
        assert after[s] == before[s]
    assert len(merged.activities) == 4


def test_whole_day_replace_keeps_day_number():
    it = demo_data.demo_itinerary(PREFS)
    other = copy.deepcopy(it.days[1])
    other.day_number = 77
    assert it.days[0].merged_with(other, None).day_number == 1


def test_route_optimizer_reduces_distance():
    it = demo_data.demo_itinerary(PREFS)
    base = geo.total_km(it)
    # Scramble: swap the morning sights of day 1 (Old City) and day 4 (Sanganer)
    scrambled = copy.deepcopy(it)
    a, b = scrambled.days[0], scrambled.days[3]
    ia = next(i for i, x in enumerate(a.activities) if x.slot == SLOTS[0])
    ib = next(i for i, x in enumerate(b.activities) if x.slot == SLOTS[0])
    a.activities[ia], b.activities[ib] = b.activities[ib], a.activities[ia]
    a.activities[ia].slot = b.activities[ib].slot = SLOTS[0]
    bad = geo.total_km(scrambled)
    assert bad > base
    fixed, before, after = geo.optimize_sightseeing(scrambled)
    assert before == bad and after < before
    assert sum(len(d.activities) for d in fixed.days) == sum(len(d.activities) for d in scrambled.days)
    assert abs(fixed.total_local() - scrambled.total_local()) < 1e-6


def test_optimizer_noop_without_coords():
    it = demo_data.demo_itinerary(PREFS)
    for d in it.days:
        for a in d.activities:
            a.lat = a.lng = None
    same, before, after = geo.optimize_sightseeing(it)
    assert same is it and before == after == 0


def test_storage_roundtrip_and_isolation():
    it = demo_data.demo_itinerary(PREFS)
    tid = storage.save_trip("Asha", "Jaipur trip", PREFS.to_dict(), it.to_dict())
    assert [t["id"] for t in storage.list_trips("asha ")] == [tid]
    assert storage.list_trips("someone else") == []
    blob = storage.export_json("asha")
    assert storage.import_json("ravi", blob) == 1
    assert len(storage.list_trips("ravi")) == 1
    storage.delete_trip("asha", tid)
    assert storage.list_trips("asha") == []
    try:
        storage.import_json("ravi", "{bad")
    except ValueError:
        pass
    else:
        raise AssertionError("bad import accepted")


def test_pdf_builds_with_awkward_text():
    it = demo_data.demo_itinerary(PREFS)
    it.destination = "São Paulo & <Rio> ₹ 日本"
    it.days[0].activities[0].description = "Fish & chips — “quoted” <b>tag</b> ₹500"
    pdf = build_pdf(it, PREFS, 88.0)
    assert pdf[:5] == b"%PDF-" and len(pdf) > 5000
    assert "?" in safe("日本") and "Rs " in safe("₹5")


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for name, fn in tests:
        fn()
        print("ok  ", name)
    print(f"\n{len(tests)} tests passed")
