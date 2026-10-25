"""Trip persistence: a tiny SQLite database (simulated cloud DB) + JSON backup.

Trips are grouped by a "profile name" the user types in. This is a demo-grade
substitute for real login. On Streamlit Community Cloud the disk is wiped on
reboot, so the app also offers JSON export/import as a durable backup.
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import uuid
from contextlib import closing
from datetime import datetime
from typing import Any, Dict, List, Optional


def _db_path() -> str:
    override = os.environ.get("TRIPS_DB_PATH")
    if override:
        return override
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    try:
        os.makedirs(here, exist_ok=True)
        probe = os.path.join(here, ".write_test")
        with open(probe, "w") as fh:
            fh.write("ok")
        os.remove(probe)
        return os.path.join(here, "trips.db")
    except OSError:
        return os.path.join(tempfile.gettempdir(), "travel_planner_trips.db")


DB_PATH = _db_path()


def clean_owner(name: str) -> str:
    return (name or "guest").strip().lower()[:40] or "guest"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS trips (
               id TEXT PRIMARY KEY, owner TEXT NOT NULL, name TEXT NOT NULL,
               saved_at TEXT NOT NULL, prefs TEXT NOT NULL, itinerary TEXT NOT NULL)"""
    )
    return conn


def save_trip(owner: str, name: str, prefs: Dict[str, Any], itinerary: Dict[str, Any],
              trip_id: Optional[str] = None) -> str:
    trip_id = trip_id or uuid.uuid4().hex[:12]
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT OR REPLACE INTO trips VALUES (?,?,?,?,?,?)",
            (trip_id, clean_owner(owner), name.strip() or "Untitled trip",
             datetime.now().strftime("%Y-%m-%d %H:%M"), json.dumps(prefs), json.dumps(itinerary)),
        )
    return trip_id


def list_trips(owner: str) -> List[Dict[str, Any]]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT id, name, saved_at, prefs, itinerary FROM trips WHERE owner=? ORDER BY saved_at DESC",
            (clean_owner(owner),),
        ).fetchall()
    return [dict(id=r[0], name=r[1], saved_at=r[2], prefs=json.loads(r[3]), itinerary=json.loads(r[4])) for r in rows]


def get_trip(owner: str, trip_id: str) -> Optional[Dict[str, Any]]:
    return next((t for t in list_trips(owner) if t["id"] == trip_id), None)


def delete_trip(owner: str, trip_id: str) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM trips WHERE id=? AND owner=?", (trip_id, clean_owner(owner)))


def export_json(owner: str) -> str:
    return json.dumps({"app": "travel-planner", "version": 1, "trips": list_trips(owner)}, indent=2)


def import_json(owner: str, text: str) -> int:
    """Import trips from an exported file. Returns how many were added."""
    try:
        data = json.loads(text)
        trips = data["trips"]
        count = 0
        for t in trips:
            save_trip(owner, t["name"], t["prefs"], t["itinerary"])  # new id: never overwrites
            count += 1
        return count
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError("That file is not a valid trip export.") from exc
