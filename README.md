# Personalized Travel Itinerary Planner

Streamlit app (Skill Wallet Capstone Project 4). Generates day-by-day itineraries that keep each day in one
neighbourhood cluster, tracks costs in local currency / USD / INR, lets you swap single slots, and exports an
offline PDF guide with an emergency checklist.

## Run locally
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
Pick **Demo (no key needed)** in the sidebar to try everything without an API key.

## Use a real AI model
Get a free key from Google AI Studio (Gemini) or console.groq.com (Groq), choose it in the sidebar and paste the key.
For deployment, put it in Streamlit **Secrets** as `GEMINI_API_KEY` or `GROQ_API_KEY` (see `.streamlit/secrets.toml.example`).
If a model name stops working, change it in the sidebar "Model name" box.

## Deploy (Streamlit Community Cloud)
1. Push this folder to a GitHub repo (the `.gitignore` already excludes keys and the local DB).
2. share.streamlit.io > New app > pick the repo, main file `app.py`.
3. App settings > Secrets > paste your key(s). Deploy.

## Project layout
| File | Role |
|---|---|
| `app.py` | UI: sidebar + 4 tabs |
| `prompts.py` | All prompt engineering (clustering, pacing, budget, diet rules) |
| `llm.py` | Gemini / Groq REST client, JSON extraction, retry-once on bad output |
| `models.py` | Dataclasses + strict validation of AI output |
| `geo.py` | Distance, transit load per day, cross-day route optimizer |
| `storage.py` | SQLite trip history + JSON export/import |
| `pdf_export.py` | ReportLab PDF guide |
| `demo_data.py` | Canned Jaipur plan and recommendations for demo mode |
| `tests/test_core.py` | Logic tests: `python tests/test_core.py` |

## Known limits (mention in your report)
- Coordinates and prices come from the AI and are approximate. Verify before travelling.
- Costs exclude flights and hotels.
- Saved trips use SQLite on the server disk, which Streamlit Cloud can reset. Use Export JSON for backups.
- The profile name is a demo stand-in for real login: anyone typing the same name sees the same trips.
