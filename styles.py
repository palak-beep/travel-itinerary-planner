"""Wanderlust theme: deep lagoon, a sunset horizon stripe, one colour per time slot."""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Figtree:wght@400;500;600&display=swap');

:root {
  --deep: #0A2E36; --lagoon: #0E5A63; --coral: #E4572E; --marigold: #F5B544;
  --plum: #4B3F8F; --mist: #E9F3F1; --ink: #12303A; --muted: #4A6670; --line: #C9D9D6;
}
.stApp { font-family: 'Figtree', system-ui, sans-serif; color: var(--ink); }
.stApp h1, .stApp h2, .stApp h3 { font-family: 'Fraunces', Georgia, serif; color: var(--deep); letter-spacing: -0.01em; }
.block-container { padding-top: 1.6rem; max-width: 1180px; }

/* Hero */
.hero { position: relative; border-radius: 16px; padding: 30px 34px 38px; color: #fff; overflow: hidden;
  background: linear-gradient(180deg, #0A2E36 0%, #0E5A63 70%, #14707A 100%); margin-bottom: 18px; }
.hero:after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 10px;
  background: linear-gradient(90deg, #F5B544 0 34%, #E4572E 34% 67%, #4B3F8F 67% 100%); }
.hero h1 { color: #fff !important; font-size: 2.3rem; line-height: 1.1; margin: 0 0 8px; }
.hero p { color: #D8ECEA; margin: 0; max-width: 62ch; font-size: 1.02rem; }
.badge { display: inline-block; margin-top: 14px; padding: 4px 12px; border-radius: 999px; font-size: .82rem;
  font-weight: 600; background: var(--marigold); color: var(--deep); }
.badge.live { background: #CFEFE6; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid var(--line); }
.stTabs [data-baseweb="tab"] { font-weight: 600; padding: 10px 16px; border-radius: 10px 10px 0 0; }
.stTabs [aria-selected="true"] { color: var(--coral); }

/* Recommendation cards */
.reco { background: #fff; border: 1px solid var(--line); border-top: 5px solid var(--lagoon); border-radius: 12px;
  padding: 18px 18px 14px; min-height: 250px; }
.reco h3 { margin: 0 0 2px; font-size: 1.35rem; }
.reco .where { color: var(--muted); font-size: .9rem; margin-bottom: 10px; }
.reco p { margin: 0 0 10px; line-height: 1.45; }
.reco .facts { font-size: .88rem; color: var(--muted); line-height: 1.6; }
.tag { display: inline-block; margin: 0 6px 6px 0; padding: 3px 10px; border-radius: 999px; font-size: .8rem;
  background: var(--mist); color: var(--lagoon); font-weight: 600; }

/* Itinerary */
.summary { background: #fff; border-left: 5px solid var(--marigold); border-radius: 8px; padding: 14px 18px; margin: 6px 0 14px; }
.day-head { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 14px; margin: 4px 0 10px; }
.day-head .t { font-family: 'Fraunces', serif; font-size: 1.15rem; font-weight: 700; color: var(--deep); }
.day-head .a { color: var(--muted); font-size: .92rem; }
.pill { padding: 2px 10px; border-radius: 999px; font-size: .78rem; font-weight: 600; background: var(--mist); color: var(--lagoon); }
.pill.heavy { background: #FBE0D8; color: #A83A1B; }
.pill.mod { background: #FCEFD2; color: #8A5A00; }
.slot { background: #fff; border: 1px solid var(--line); border-left-width: 6px; border-radius: 10px; padding: 12px 16px; margin-bottom: 10px; }
.slot-0 { border-left-color: var(--marigold); } .slot-1 { border-left-color: var(--coral); }
.slot-2 { border-left-color: var(--lagoon); }  .slot-3 { border-left-color: var(--plum); }
.slot-top { display: flex; justify-content: space-between; gap: 10px; align-items: center; }
.slot-name { font-size: .85rem; font-weight: 600; color: var(--muted); }
.chip { font-weight: 600; font-size: .85rem; padding: 2px 10px; border-radius: 8px; background: var(--mist); color: var(--deep); white-space: nowrap; }
.slot-title { font-size: 1.05rem; font-weight: 600; margin: 4px 0 2px; }
.slot-desc { color: #2B4852; line-height: 1.45; }
.slot-meta { margin-top: 6px; font-size: .84rem; color: var(--muted); }
.slot-meta span + span { margin-left: 14px; }
.running { margin-top: 6px; font-size: .82rem; color: var(--lagoon); font-weight: 600; }
.note { background: var(--mist); border-radius: 8px; padding: 10px 14px; font-size: .92rem; }

/* Buttons and sidebar */
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] { font-weight: 600; border-radius: 10px; }
section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h5 { font-family: 'Fraunces', serif; }

@media (max-width: 640px) { .hero { padding: 22px 20px 30px; } .hero h1 { font-size: 1.7rem; } }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
</style>
"""
