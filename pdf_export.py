"""Offline PDF travel guide built with ReportLab.

Uses the built-in Helvetica font, which has no glyphs for symbols like the rupee
sign or for non-Latin scripts. `safe()` converts those to plain-text equivalents
so the PDF never shows black boxes.
"""
from __future__ import annotations

import io
from collections import defaultdict
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

from models import FALLBACK_RATES, SLOTS, Itinerary, Preferences

LAGOON = colors.HexColor("#0E5A63")
DEEP = colors.HexColor("#0A2E36")
CORAL = colors.HexColor("#E4572E")
MARIGOLD = colors.HexColor("#F5B544")
MIST = colors.HexColor("#E9F3F1")
INK = colors.HexColor("#12303A")
SLOT_COLORS = [MARIGOLD, CORAL, LAGOON, colors.HexColor("#4B3F8F")]

_REPLACE = {"₹": "Rs ", "–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"',
            "…": "...", "•": "-", "→": "->", "\u00a0": " ", "\u2009": " "}


def safe(value) -> str:
    text = "" if value is None else str(value)
    for k, v in _REPLACE.items():
        text = text.replace(k, v)
    text = text.encode("latin-1", "replace").decode("latin-1")
    return escape(text)


def _styles():
    base = getSampleStyleSheet()
    def mk(name, **kw):
        kw.setdefault("textColor", INK)
        return ParagraphStyle(name, parent=base["Normal"], **kw)
    return {
        "title": mk("T", fontName="Helvetica-Bold", fontSize=30, leading=34, textColor=colors.white),
        "subtitle": mk("S", fontSize=13, leading=18, textColor=colors.white),
        "h1": mk("H1", fontName="Helvetica-Bold", fontSize=16, leading=20, spaceBefore=6, spaceAfter=6, textColor=DEEP),
        "dayhead": mk("DH", fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=colors.white),
        "body": mk("B", fontSize=10, leading=14, alignment=TA_LEFT),
        "small": mk("SM", fontSize=8.5, leading=11, textColor=colors.HexColor("#4A6670")),
        "cell": mk("C", fontSize=9, leading=12),
        "cellb": mk("CB", fontName="Helvetica-Bold", fontSize=9, leading=12),
        "th": mk("TH", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.white),
    }


def make_formatter(it: Itinerary, inr_per_usd: float):
    rate = it.local_per_usd if it.local_per_usd > 0 else FALLBACK_RATES.get(it.local_currency, 1.0)
    if it.local_currency == "INR":
        rate = inr_per_usd

    def local(x): return f"{safe(it.local_currency)} {x:,.0f}"
    def usd(x): return f"USD {x / rate:,.0f}"
    def inr(x): return f"INR {x / rate * inr_per_usd:,.0f}"
    return local, usd, inr


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#4A6670"))
    canvas.drawString(18 * mm, 10 * mm, "Personalized Travel Itinerary Planner - estimates only, verify prices and hours before you go")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf(it: Itinerary, prefs: Preferences, inr_per_usd: float = 88.0) -> bytes:
    st = _styles()
    local, usd, inr = make_formatter(it, inr_per_usd)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=18 * mm, title=f"{it.destination} itinerary", author="Travel Itinerary Planner")
    width = A4[0] - 36 * mm
    story = []

    # ---- cover
    n_days = len(it.days)
    cover = Table([[Paragraph(safe(it.destination), st["title"])],
                   [Paragraph(safe(f"{n_days}-day itinerary" + (f" in {it.country}" if it.country else "")), st["subtitle"])],
                   [Paragraph(safe(f"{prefs.travellers} traveller(s) ({prefs.party}), {prefs.pace} pace, "
                                   f"{prefs.budget_level} budget. Starts {prefs.start_date or 'TBD'}"), st["subtitle"])]],
                  colWidths=[width])
    cover.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), DEEP), ("LEFTPADDING", (0, 0), (-1, -1), 16),
                               ("TOPPADDING", (0, 0), (0, 0), 40), ("BOTTOMPADDING", (0, -1), (-1, -1), 36),
                               ("LINEBELOW", (0, -1), (-1, -1), 6, MARIGOLD)]))
    story += [cover, Spacer(1, 14)]
    if it.summary:
        story += [Paragraph(safe(it.summary), st["body"]), Spacer(1, 8)]
    total = it.total_local()
    stats = Table([[Paragraph("<b>Estimated activity + food cost</b>", st["cell"]),
                    Paragraph(f"{local(total)} / {usd(total)} / {inr(total)}", st["cell"])],
                   [Paragraph("<b>Generated on</b>", st["cell"]), Paragraph(date.today().strftime("%d %B %Y"), st["cell"])],
                   [Paragraph("<b>Not included</b>", st["cell"]), Paragraph("Flights, hotels and local transfers", st["cell"])]],
                  colWidths=[55 * mm, width - 55 * mm])
    stats.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), MIST), ("BOX", (0, 0), (-1, -1), 0.5, LAGOON),
                               ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.white), ("TOPPADDING", (0, 0), (-1, -1), 5),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.append(stats)
    if it.tips:
        story += [Spacer(1, 10), Paragraph("Good to know", st["h1"])]
        story += [Paragraph("- " + safe(t), st["body"]) for t in it.tips]
    story.append(PageBreak())

    # ---- days
    running = 0.0
    for day in it.days:
        head = Table([[Paragraph(safe(f"Day {day.day_number}: {day.theme}"), st["dayhead"]),
                       Paragraph(safe(day.area_cluster), st["th"])]], colWidths=[width * 0.68, width * 0.32])
        head.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LAGOON), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                  ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 7),
                                  ("BOTTOMPADDING", (0, 0), (-1, -1), 7), ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
        rows = [[Paragraph("Time slot", st["th"]), Paragraph("Plan", st["th"]), Paragraph("Est. cost", st["th"]),
                 Paragraph("Running total", st["th"])]]
        style = [("BACKGROUND", (0, 0), (-1, 0), DEEP), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                 ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#C9D9D6")),
                 ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]
        for i, a in enumerate(day.sorted_activities(), start=1):
            running += a.cost_local
            detail = f"<b>{safe(a.title)}</b>"
            if a.description:
                detail += f"<br/>{safe(a.description)}"
            if a.area:
                detail += f"<br/><font size=8 color='#4A6670'>Area: {safe(a.area)}</font>"
            if a.tip:
                detail += f"<br/><font size=8 color='#4A6670'>Tip: {safe(a.tip)}</font>"
            rows.append([Paragraph(safe(a.slot), st["cellb"]), Paragraph(detail, st["cell"]),
                         Paragraph(local(a.cost_local), st["cell"]), Paragraph(local(running), st["cell"])])
            idx = SLOTS.index(a.slot) if a.slot in SLOTS else 0
            style.append(("LINEBEFORE", (0, i), (0, i), 3, SLOT_COLORS[idx]))
        rows.append([Paragraph("", st["cell"]), Paragraph("<b>Day total</b>", st["cell"]),
                     Paragraph(f"<b>{local(day.total_local())}</b>", st["cell"]), Paragraph("", st["cell"])])
        style.append(("BACKGROUND", (0, -1), (-1, -1), MIST))
        table = Table(rows, colWidths=[width * 0.20, width * 0.46, width * 0.17, width * 0.17], repeatRows=1)
        table.setStyle(TableStyle(style))
        story += [KeepTogether([head, table]), Spacer(1, 14)]

    # ---- cost summary
    story += [PageBreak(), Paragraph("Cost summary", st["h1"])]
    rows = [[Paragraph(h, st["th"]) for h in ("Day", "Theme", "Local", "USD", "INR")]]
    for d in it.days:
        t = d.total_local()
        rows.append([Paragraph(str(d.day_number), st["cell"]), Paragraph(safe(d.theme), st["cell"]),
                     Paragraph(local(t), st["cell"]), Paragraph(usd(t), st["cell"]), Paragraph(inr(t), st["cell"])])
    rows.append([Paragraph("", st["cell"]), Paragraph("<b>Total</b>", st["cell"]), Paragraph(f"<b>{local(total)}</b>", st["cell"]),
                 Paragraph(f"<b>{usd(total)}</b>", st["cell"]), Paragraph(f"<b>{inr(total)}</b>", st["cell"])])
    ct = Table(rows, colWidths=[width * 0.08, width * 0.38, width * 0.18, width * 0.18, width * 0.18], repeatRows=1)
    ct.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), DEEP), ("BACKGROUND", (0, -1), (-1, -1), MIST),
                            ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#C9D9D6")),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story += [ct, Spacer(1, 10)]

    by_cat = defaultdict(float)
    for d in it.days:
        for a in d.activities:
            by_cat[a.category.title()] += a.cost_local
    rows = [[Paragraph("Category", st["th"]), Paragraph("Local", st["th"]), Paragraph("Share", st["th"])]]
    for cat, val in sorted(by_cat.items(), key=lambda kv: -kv[1]):
        share = f"{val / total * 100:.0f}%" if total else "0%"
        rows.append([Paragraph(safe(cat), st["cell"]), Paragraph(local(val), st["cell"]), Paragraph(share, st["cell"])])
    cat_t = Table(rows, colWidths=[width * 0.4, width * 0.3, width * 0.3], repeatRows=1)
    cat_t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), LAGOON),
                               ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#C9D9D6"))]))
    story += [Paragraph("By category", st["h1"]), cat_t,
              Spacer(1, 6), Paragraph(safe(f"Exchange rate used: 1 USD = {it.local_per_usd:,.2f} {it.local_currency}; "
                                           f"1 USD = {inr_per_usd:,.2f} INR. Rates are approximate."), st["small"])]

    # ---- emergency page
    story += [PageBreak(), Paragraph("Emergency contacts", st["h1"])]
    em = it.emergency
    rows = [[Paragraph("Service", st["th"]), Paragraph("Number", st["th"])]]
    for label, val in (("Police", em.police), ("Ambulance", em.ambulance), ("Fire", em.fire),
                       ("Tourist helpline", em.tourist_helpline)):
        rows.append([Paragraph(label, st["cellb"]), Paragraph(safe(val), st["cell"])])
    et = Table(rows, colWidths=[width * 0.4, width * 0.6])
    et.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), CORAL),
                            ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#C9D9D6")),
                            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story += [et, Spacer(1, 4), Paragraph(safe(em.embassy_note + " Numbers are AI-supplied, so verify them before you travel."), st["small"]),
              Spacer(1, 12), Paragraph("Fill in before you leave", st["h1"])]
    blanks = ["Hotel name, address and phone", "Nearest embassy / consulate and phone", "Emergency contact back home",
              "Travel insurance provider and policy no.", "Bank / card lost-card hotline", "Blood group and allergies"]
    rows = [[Paragraph(safe(b), st["cell"]), Paragraph("_" * 46, st["cell"])] for b in blanks]
    bt = Table(rows, colWidths=[width * 0.42, width * 0.58])
    bt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("TOPPADDING", (0, 0), (-1, -1), 7)]))
    story += [bt, Spacer(1, 12), Paragraph("Pre-departure checklist", st["h1"])]

    checks = ["Passport / ID valid and copies saved offline", "Visas or entry permits confirmed",
              "Travel insurance bought, policy number saved", "Tickets and hotel bookings downloaded",
              "Cards and some local cash arranged", "Phone data / SIM / offline maps ready",
              "Medicines and prescriptions packed", "Home contact has a copy of this itinerary"]
    rows = [["", Paragraph(safe(c), st["body"])] for c in checks]
    ck = Table(rows, colWidths=[8 * mm, width - 8 * mm], rowHeights=[8 * mm] * len(rows))
    cmds = [("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    for i in range(len(rows)):
        cmds.append(("BOX", (0, i), (0, i), 0.9, INK))
    ck.setStyle(TableStyle(cmds))
    story.append(ck)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
