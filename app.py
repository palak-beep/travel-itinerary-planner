"""Personalized Travel Itinerary Planner (Skill Wallet Capstone Project 4).

Run locally:  streamlit run app.py
"""
from __future__ import annotations

import copy
import datetime as dt
import html
import os

import streamlit as st

import demo_data
import geo
import llm
import prompts
import storage
from models import (BUDGET_LEVELS, DIETS, FALLBACK_RATES, INTERESTS, PACES, PARTIES, SLOTS, VIBES, Day,
                    Itinerary, ModelError, Preferences, RecommendationList)
from pdf_export import build_pdf
from styles import CSS

st.set_page_config(page_title="Travel Itinerary Planner", page_icon="🧭", layout="wide")

# Rough activity + food spend per person per day (USD). Excludes flights and hotels.
BENCHMARK_USD = {"Budget": 35, "Moderate": 80, "Luxury": 200}
QUICK_IDEAS = [
    "Pick an idea (optional)",
    "Swap the museum for an outdoor market",
    "Find a vegetarian lunch spot",
    "Make this evening more romantic",
    "Add a slow, relaxing afternoon",
    "Give me a livelier nightlife option",
    "Choose cheaper food options",
    "Replace this with something indoors in case of rain",
]


# ------------------------------------------------------------------ helpers
def h(text) -> str:
    return html.escape("" if text is None else str(text))


def compact(markup: str) -> str:
    """Strip indentation so Markdown does not treat HTML as a code block."""
    return "".join(line.strip() for line in markup.splitlines())


def get_secret(name: str) -> str:
    try:
        value = st.secrets.get(name)
    except Exception:  # no secrets.toml present
        value = None
    return value or os.environ.get(name, "")


def friendly(exc: Exception) -> str:
    if isinstance(exc, (llm.LLMError, ModelError, ValueError)):
        return str(exc)
    return f"Something went wrong ({type(exc).__name__}). Please try again."


class Money:
    """Converts and formats local-currency amounts for the chosen display mode."""

    def __init__(self, it: Itinerary, mode: str, inr_per_usd: float):
        self.code = it.local_currency
        rate = it.local_per_usd if it.local_per_usd > 0 else FALLBACK_RATES.get(self.code, 1.0)
        self.rate = inr_per_usd if self.code == "INR" else rate
        self.mode, self.inr = mode, inr_per_usd

    def usd(self, x: float) -> float:
        return x / self.rate

    def num(self, x: float) -> float:
        return self.usd(x) * self.inr if self.mode == "INR" else (self.usd(x) if self.mode == "USD" else x)

    @property
    def unit(self) -> str:
        return {"USD": "USD", "INR": "INR"}.get(self.mode, self.code)

    def fmt(self, x: float) -> str:
        if self.mode == "USD":
            return f"${self.usd(x):,.0f}"
        if self.mode == "INR":
            return f"₹{self.usd(x) * self.inr:,.0f}"
        return f"{self.code} {x:,.0f}"


def init_state() -> None:
    ss = st.session_state
    ss.setdefault("itinerary", None)
    ss.setdefault("trip_prefs", None)  # preferences the current itinerary was built from
    ss.setdefault("recos", None)
    ss.setdefault("undo", [])
    ss.setdefault("destination", "")
    ss.setdefault("flash", "")
    ss.setdefault("tab3_msg", "")


# ------------------------------------------------------------------ sidebar
def sidebar():
    with st.sidebar:
        st.markdown("## Trip settings")
        st.markdown("##### AI model")
        provider = st.selectbox("Mode", [llm.DEMO, "Gemini", "Groq"], key="provider")
        api_key, model = "", ""
        if provider != llm.DEMO:
            secret = get_secret(f"{provider.upper()}_API_KEY")
            api_key = st.text_input(f"{provider} API key", type="password", key=f"key_{provider}",
                                    help="Stored only in this browser session. Never saved to disk.")
            if not api_key and secret:
                api_key = secret
                st.caption("Using the key from app secrets.")
            model = st.text_input("Model name", value=llm.DEFAULT_MODELS[provider], key=f"model_{provider}")
        cfg = llm.LLMConfig(provider, api_key, model)
        if provider != llm.DEMO and not api_key:
            st.warning("No API key yet, so the app shows demo data.")

        st.markdown("##### Your trip")
        destination = st.text_input("Destination", key="destination", placeholder="Leave empty to get ideas")
        vibe = st.selectbox("Vibe (for ideas)", VIBES, index=2, key="vibe")
        days = st.slider("Days", 1, 10, 3, key="days")
        start = st.date_input("Start date", value=dt.date.today() + dt.timedelta(days=30), key="start_date")
        budget = st.select_slider("Budget level", BUDGET_LEVELS, value="Moderate", key="budget")
        party = st.selectbox("Travelling as", PARTIES, index=1, key="party")
        if party == "Solo":
            travellers = 1
        elif party == "Couple":
            travellers = 2
        else:
            travellers = st.number_input("Number of travellers", 2, 30, 4, key="travellers")
        pace = st.selectbox("Pace", PACES, index=1, key="pace")
        interests = st.multiselect("Interests", INTERESTS, default=["Food", "History"], key="interests")
        diet = st.selectbox("Food preference", DIETS, key="diet")

        st.markdown("##### Money")
        mode = st.radio("Show costs in", ["Local", "USD", "INR"], horizontal=True, key="currency_mode")
        inr = st.number_input("INR per 1 USD (approx.)", 50.0, 150.0, 88.0, step=0.5, key="inr_rate")
        custom = st.number_input("Total budget in USD (0 = automatic)", 0.0, 1_000_000.0, 0.0, step=100.0, key="custom_budget")

        st.markdown("##### Saved trips")
        owner = storage.clean_owner(st.text_input("Profile name", value="guest", key="owner",
                                                  help="Trips are saved under this name. This is a demo, not a login."))

    prefs = Preferences(
        destination=destination.strip(), vibe=vibe, days=int(days), start_date=start.isoformat(), budget_level=budget,
        party=party, travellers=int(travellers), pace=pace, interests=list(interests), diet=diet,
        inr_per_usd=float(inr), custom_budget_usd=float(custom),
    )
    return cfg, prefs, mode, owner


def hero(cfg: llm.LLMConfig) -> None:
    badge = ('<span class="badge">Demo mode: sample Jaipur data</span>' if cfg.is_demo
             else f'<span class="badge live">Live AI: {h(cfg.provider)}</span>')
    st.markdown(compact(f"""
        <div class="hero">
          <h1>Personalized Travel Itinerary Planner</h1>
          <p>Day-by-day plans that keep each day in one part of town, with a running cost you can track and a PDF you can take offline.</p>
          {badge}
        </div>"""), unsafe_allow_html=True)


# ------------------------------------------------------------------- tab 1
def use_destination(city: str) -> None:
    st.session_state["destination"] = city
    st.session_state["flash"] = f"Destination set to {city}. Open the Day-by-day itinerary tab to plan it."


def tab_recommend(cfg: llm.LLMConfig, prefs: Preferences) -> None:
    st.subheader("Not sure where to go?")
    st.caption(f"Matches the {prefs.vibe.lower()} vibe, {prefs.budget_level.lower()} budget, {prefs.month_text()} "
               f"and your interests. Change them in the sidebar.")
    if st.button("Recommend 3 destinations", type="primary", key="btn_reco"):
        with st.spinner("Matching destinations to your trip..."):
            try:
                if cfg.is_demo:
                    st.session_state.recos = demo_data.demo_recommendations(prefs)
                else:
                    st.session_state.recos = llm.generate(RecommendationList.from_dict, cfg, prompts.SYSTEM,
                                                          prompts.reco_prompt(prefs))
            except Exception as exc:  # show a readable message instead of a stack trace
                st.error(friendly(exc))
    recos = st.session_state.recos
    if not recos:
        st.info("Choose a vibe in the sidebar and press the button to see three matching cities.")
        return
    for col, r, i in zip(st.columns(3), recos.recommendations[:3], range(3)):
        with col:
            tags = "".join(f'<span class="tag">{h(t)}</span>' for t in r.tags)
            budget = f"About ${r.daily_budget_usd:,.0f} per person per day" if r.daily_budget_usd else ""
            st.markdown(compact(f"""
                <div class="reco">
                  <h3>{h(r.city)}</h3>
                  <div class="where">{h(r.country)}</div>
                  <p>{h(r.why)}</p>
                  <div>{tags}</div>
                  <div class="facts">Best time: {h(r.best_season)}<br>{h(r.weather_note)}<br>{h(budget)}</div>
                </div>"""), unsafe_allow_html=True)
            st.button(f"Plan {r.city}", key=f"plan_{i}", on_click=use_destination, args=(r.city,))


# ------------------------------------------------------------------- tab 2
def slot_html(a, running: str = "") -> str:
    idx = SLOTS.index(a.slot) if a.slot in SLOTS else 0
    meta = ""
    if a.area:
        meta += f"<span>Area: {h(a.area)}</span>"
    if a.category:
        meta += f"<span>{h(a.category.title())}</span>"
    if a.tip:
        meta += f"<span>Tip: {h(a.tip)}</span>"
    run_html = '<div class="running">' + h(running) + "</div>" if running else ""
    return compact(f"""
        <div class="slot slot-{idx}">
          <div class="slot-top"><span class="slot-name">{h(a.slot)}</span><span class="chip">{{COST}}</span></div>
          <div class="slot-title">{h(a.title)}</div>
          <div class="slot-desc">{h(a.description)}</div>
          <div class="slot-meta">{meta}</div>
          {run_html}
        </div>""")


def build_itinerary(cfg, prefs) -> Itinerary:
    if cfg.is_demo:
        return demo_data.demo_itinerary(prefs)
    it = llm.generate(Itinerary.from_dict, cfg, prompts.SYSTEM, prompts.itinerary_prompt(prefs))
    return it.normalize(prefs.days)


def tab_itinerary(cfg, prefs, mode) -> None:
    ss = st.session_state
    st.subheader("Your day-by-day plan")
    left, right = st.columns([1, 3])
    with left:
        go = st.button("Generate itinerary", type="primary", key="btn_gen")
    with right:
        target = prefs.destination or ("a sample city" if cfg.is_demo else "no destination yet")
        st.caption(f"{prefs.days} days in {target}, {prefs.travellers} traveller(s), {prefs.pace.lower()} pace.")

    if go:
        if not prefs.destination and not cfg.is_demo:
            st.warning("Enter a destination in the sidebar, or pick one from the first tab.")
        else:
            with st.spinner("Clustering nearby places and planning each day..."):
                try:
                    it = build_itinerary(cfg, prefs)
                    ss.itinerary, ss.trip_prefs, ss.undo = it, copy.deepcopy(prefs), []
                    ss.itinerary_source = "Demo sample" if cfg.is_demo else f"{cfg.provider} ({cfg.model or llm.DEFAULT_MODELS[cfg.provider]})"
                    if cfg.is_demo and prefs.days > len(it.days):
                        st.info(f"Demo mode has {len(it.days)} sample days. Add an API key for longer trips.")
                    elif len(it.days) < prefs.days:
                        st.warning(f"The AI returned {len(it.days)} of {prefs.days} days. Press Generate again for a full plan.")
                except Exception as exc:
                    st.error(friendly(exc))

    it: Itinerary = ss.itinerary
    if not it:
        st.info("Set your trip in the sidebar, then press Generate itinerary.")
        return
    tp: Preferences = ss.trip_prefs or prefs
    money = Money(it, mode, prefs.inr_per_usd)
    if it.is_demo:
        label = "Source: demo sample plan, not written by an AI model"
    else:
        label = "Source: " + (ss.get("itinerary_source") or "saved trip")
    st.markdown(compact(f'<span class="pill">{h(label)}</span>'), unsafe_allow_html=True)
    render_summary(it, tp, money)
    running = 0.0
    for day in it.days:
        running = render_day(day, running, money)
    if it.tips:
        st.markdown("**Good to know**")
        st.markdown("\n".join(f"- {t}" for t in it.tips))


def render_summary(it: Itinerary, tp: Preferences, money: Money) -> None:
    total = it.total_local()
    n_days = max(len(it.days), 1)
    usd = money.usd(total)
    cap = tp.custom_budget_usd or BENCHMARK_USD[tp.budget_level] * tp.travellers * n_days
    used = usd / cap if cap else 0
    place = f"{it.destination}, {it.country}" if it.country else it.destination
    st.markdown(compact(f"""<div class="summary"><b>{h(place)}</b><br>{h(it.summary)}</div>"""), unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Estimated total", money.fmt(total))
    c2.metric("Per person per day", money.fmt(total / max(tp.travellers, 1) / n_days))
    c3.metric("Budget used", f"{used * 100:.0f}%")
    c4.metric("Travel between stops", f"{geo.total_km(it):.0f} km" if geo.has_geo_data(it) else "n/a")
    st.progress(min(used, 1.0))
    basis = "your custom budget" if tp.custom_budget_usd else f"a typical {tp.budget_level.lower()} budget (activities and food only)"
    st.caption(f"Compared with {basis}: about ${cap:,.0f} for the trip. Flights and hotels are not included. "
               f"1 USD = {money.rate:,.2f} {money.code}" + (" (editable in sidebar)." if money.code == "INR" else ", approximate."))
    if len(it.days) > 1:
        import pandas as pd
        chart = pd.DataFrame({f"Cost ({money.unit})": [money.num(d.total_local()) for d in it.days]},
                             index=[f"Day {d.day_number}" for d in it.days])
        st.bar_chart(chart)


def render_day(day: Day, running: float, money: Money) -> float:
    pts = geo.day_points(day)
    km = geo.day_km(day)
    label = geo.transit_label(km, len(pts))
    level = "heavy" if label.startswith("Heavy") else ("mod" if label.startswith("Moderate") else "")
    km_txt = f" ({km:.1f} km)" if len(pts) >= 2 else ""
    st.markdown(compact(f"""
        <div class="day-head"><span class="t">Day {day.day_number}: {h(day.theme)}</span>
        <span class="a">{h(day.area_cluster)}</span><span class="pill {level}">{h(label)}{km_txt}</span></div>"""),
                unsafe_allow_html=True)
    col_a, col_b = st.columns([3, 2])
    with col_a:
        for a in day.sorted_activities():
            running += a.cost_local
            st.markdown(slot_html(a, f"Trip total so far: {money.fmt(running)}").replace("{COST}", h(money.fmt(a.cost_local))),
                        unsafe_allow_html=True)
        st.caption(f"Day {day.day_number} total: {money.fmt(day.total_local())}")
    with col_b:
        if pts:
            try:
                import pandas as pd
                st.map(pd.DataFrame([{"lat": p[0], "lon": p[1]} for p in pts]))
                st.caption("Pin positions are approximate.")
            except Exception:
                st.caption("Map unavailable.")
        else:
            st.caption("No map coordinates for this day.")
    st.divider()
    return running


# ------------------------------------------------------------------- tab 3
def run_change(cfg, prefs, it, day_no, slot, instruction):
    idx = next(i for i, d in enumerate(it.days) if d.day_number == day_no)
    day = it.days[idx]
    if cfg.is_demo:
        new_day = demo_data.demo_swap(day, slot, instruction, prefs)
    else:
        new_day = llm.generate(Day.from_dict, cfg, prompts.SYSTEM, prompts.swap_prompt(prefs, it, day, slot, instruction))
    return idx, day, day.merged_with(new_day, slot)


def tab_customize(cfg, prefs, mode) -> None:
    ss = st.session_state
    st.subheader("Change one slot or one day")
    st.caption("Only the part you pick changes. The rest of your plan stays exactly as it is.")
    it: Itinerary = ss.itinerary
    if not it:
        st.info("Generate an itinerary first, then come back to customize it.")
        return
    tp: Preferences = ss.trip_prefs or prefs
    money = Money(it, mode, prefs.inr_per_usd)
    if ss.tab3_msg:
        st.success(ss.tab3_msg)
        ss.tab3_msg = ""

    c1, c2 = st.columns(2)
    day_no = c1.selectbox("Day", [d.day_number for d in it.days], key="sw_day")
    scope = c2.selectbox("What to change", ["Whole day"] + SLOTS, key="sw_scope")
    quick = st.selectbox("Quick ideas", QUICK_IDEAS, key="sw_quick")
    custom = st.text_input("Or describe your own change", key="sw_text", placeholder="e.g. Swap the museum for an outdoor market")
    instruction = custom.strip() or (quick if quick != QUICK_IDEAS[0] else "")
    slot = None if scope == "Whole day" else scope
    if not instruction:
        instruction = ("Give this day a fresh set of different activities in the same area."
                       if slot is None else f"Suggest a different option for {slot}.")

    day = next(d for d in it.days if d.day_number == day_no)
    with st.expander(f"Current plan for Day {day_no}", expanded=True):
        for a in day.sorted_activities():
            st.markdown(slot_html(a).replace("{COST}", h(money.fmt(a.cost_local))), unsafe_allow_html=True)

    b1, b2, _ = st.columns([1.3, 1, 2])
    if b1.button(f"Apply to Day {day_no}", type="primary", key="btn_apply"):
        with st.spinner("Updating just that part of your trip..."):
            try:
                idx, old, merged = run_change(cfg, tp, it, day_no, slot, instruction)
                ss.undo.append(("day", idx, copy.deepcopy(old)))
                it.days[idx] = merged
                what = slot or "the whole day"
                ss.tab3_msg = f"Updated {what} on Day {day_no}. Open the itinerary tab to see it."
                st.rerun()
            except Exception as exc:
                st.error(friendly(exc))
    if b2.button("Undo last change", key="btn_undo", disabled=not ss.undo):
        kind, *payload = ss.undo.pop()
        if kind == "day":
            it.days[payload[0]] = payload[1]
        else:
            ss.itinerary = Itinerary.from_dict(payload[0])
        ss.tab3_msg = "Last change undone."
        st.rerun()

    st.divider()
    st.subheader("Route optimizer")
    if not geo.has_geo_data(it):
        st.caption("This plan has no map coordinates, so routes cannot be compared.")
        return
    st.caption(f"Right now: {geo.total_km(it):.1f} km between stops across the trip. The optimizer regroups sightseeing "
               "stops across days so nearby places share a day, and keeps your lunches and dinners.")
    if st.button("Optimize routes across days", key="btn_opt"):
        new_it, before, after = geo.optimize_sightseeing(it)
        if after < before:
            ss.undo.append(("all", copy.deepcopy(it.to_dict())))
            ss.itinerary = new_it
            ss.tab3_msg = f"Travel between stops cut from {before:.1f} km to {after:.1f} km ({(1 - after / before) * 100:.0f}% less)."
            st.rerun()
        else:
            st.info("Your days are already well grouped, so nothing needed to move.")


# ------------------------------------------------------------------- tab 4
@st.cache_data(show_spinner=False)
def cached_pdf(it_dict: dict, prefs_dict: dict, inr: float) -> bytes:
    return build_pdf(Itinerary.from_dict(it_dict), Preferences.from_dict(prefs_dict), inr)


def load_trip(owner: str, trip_id: str) -> None:
    ss = st.session_state
    trip = storage.get_trip(owner, trip_id)
    if not trip:
        return
    ss.itinerary = Itinerary.from_dict(trip["itinerary"])
    ss.trip_prefs = Preferences.from_dict(trip["prefs"])
    ss.undo = []
    ss["destination"] = ss.itinerary.destination
    ss.flash = f"Loaded '{trip['name']}'. Open the Day-by-day itinerary tab to view it."


def delete_trip(owner: str, trip_id: str) -> None:
    storage.delete_trip(owner, trip_id)


def tab_trips(prefs, owner) -> None:
    ss = st.session_state
    st.subheader("Save, export and revisit trips")
    it: Itinerary = ss.itinerary
    tp: Preferences = ss.trip_prefs or prefs
    if it:
        c1, c2 = st.columns([2, 1])
        name = c1.text_input("Trip name", value=f"{it.destination} {len(it.days)}-day trip", key="trip_name")
        c2.write("")
        if c2.button("Save trip", type="primary", key="btn_save"):
            try:
                storage.save_trip(owner, name, tp.to_dict(), it.to_dict())
                st.success(f"Saved '{name}' under profile '{owner}'.")
            except Exception as exc:
                st.error(f"Could not save the trip: {friendly(exc)}")
        try:
            pdf = cached_pdf(it.to_dict(), tp.to_dict(), prefs.inr_per_usd)
            st.download_button("Download PDF travel guide", pdf, file_name=f"{it.destination.lower().replace(' ', '-')}-itinerary.pdf",
                               mime="application/pdf", type="primary", key="dl_current")
            st.caption("Includes day-wise plan, cost summary, emergency numbers and a pre-departure checklist.")
        except Exception as exc:
            st.error(f"Could not build the PDF: {friendly(exc)}")
    else:
        st.info("Generate an itinerary to save it or export a PDF.")

    st.markdown("#### Trip history")
    try:
        trips = storage.list_trips(owner)
    except Exception as exc:
        st.error(f"Could not read saved trips: {friendly(exc)}")
        trips = []
    if not trips:
        st.caption(f"No saved trips under profile '{owner}' yet.")
    for t in trips:
        saved = Itinerary.from_dict(t["itinerary"])
        with st.expander(f"{t['name']}   |   saved {t['saved_at']}"):
            st.write(f"{saved.destination}: {len(saved.days)} days, estimated {saved.local_currency} {saved.total_local():,.0f}")
            a, b, c = st.columns(3)
            a.button("Load this trip", key=f"load_{t['id']}", on_click=load_trip, args=(owner, t["id"]))
            b.button("Delete", key=f"del_{t['id']}", on_click=delete_trip, args=(owner, t["id"]))
            try:
                c.download_button("PDF", cached_pdf(t["itinerary"], t["prefs"], prefs.inr_per_usd),
                                  file_name=f"trip-{t['id']}.pdf", mime="application/pdf", key=f"pdf_{t['id']}")
            except Exception:
                c.caption("PDF unavailable")

    st.markdown("#### Backup")
    st.caption("Streamlit Community Cloud can reset its disk when the app restarts. Export a backup to keep your trips for good.")
    e1, e2 = st.columns(2)
    e1.download_button("Export all trips (JSON)", storage.export_json(owner), file_name="my-trips.json",
                       mime="application/json", key="dl_json")
    upload = e2.file_uploader("Import trips (JSON)", type=["json"], key="up_json")
    if upload is not None and e2.button("Import file", key="btn_import"):
        try:
            n = storage.import_json(owner, upload.getvalue().decode("utf-8"))
            st.success(f"Imported {n} trip(s).")
            st.rerun()
        except (ValueError, UnicodeDecodeError) as exc:
            st.error(str(exc))


# --------------------------------------------------------------------- main
def main() -> None:
    init_state()
    st.markdown(CSS, unsafe_allow_html=True)
    cfg, prefs, mode, owner = sidebar()
    if st.session_state.flash:
        st.toast(st.session_state.flash)
        st.session_state.flash = ""
    hero(cfg)
    t1, t2, t3, t4 = st.tabs(["Find a destination", "Day-by-day itinerary", "Customize and swap", "Trips and PDF"])
    with t1:
        tab_recommend(cfg, prefs)
    with t2:
        tab_itinerary(cfg, prefs, mode)
    with t3:
        tab_customize(cfg, prefs, mode)
    with t4:
        tab_trips(prefs, owner)


if __name__ == "__main__":
    main()
