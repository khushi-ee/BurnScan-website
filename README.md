# burnscan-website

Web frontend + FastAPI backend for the AIIMS Paediatric Burns Analyser.

```
burnscan-website/
├── api/
│   ├── main.py          FastAPI app — calls burnscan-core pipeline
│   └── requirements.txt
└── frontend/
    └── index.html       Single-file HTML/CSS/JS frontend
```

## Run locally

```bash
# 1. Clone core alongside this repo
git clone https://github.com/YOUR_USERNAME/burnscan-core ../burnscan-core

# 2. Install API deps
pip install -r api/requirements.txt

# 3. Start API (must be run from repo root so PYTHONPATH includes burnscan-core)
PYTHONPATH=../burnscan-core uvicorn api.main:app --reload --port 8000

# 4. Open frontend/index.html in your browser
#    (or serve it: python -m http.server 8080 --directory frontend)
```

## Run on Colab

Use `BurnScan_Launcher.ipynb` — it clones both repos, starts everything,
and gives you a public ngrok URL.

## Deploy (production)

**Backend** — deploy `api/` to any Python host:
- Railway / Render / Fly.io (free tiers available)
- Set `PYTHONPATH` to point at burnscan-core
- The API is fully stateless — no DB needed for the prototype

**Frontend** — deploy `frontend/index.html` to:
- GitHub Pages (free, 1 file, just push)
- Netlify / Vercel (drag-and-drop)
- Update `API_BASE` in `index.html` to point at your deployed API URL

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Liveness check |
| POST | `/api/analyse` | Upload image, returns JSON + base64 grid PNGs |

### POST /api/analyse

Form fields:
- `file` — image file (JPG / PNG, max 20 MB)
- `k` — block size (int, 5–30, default 10)
- `patient_id` — optional string
- `patient_age` — optional int

Response:
```json
{
  "status": "ok",
  "classification": {
    "degree": "2nd Degree (Partial-thickness)",
    "confidence": 0.72,
    "tbsa_pct": 14.3,
    "colour": "#dd6b20",
    "explanation": "..."
  },
  "grids": {
    "burn_mask": "<base64 PNG>",
    "depth":     "<base64 PNG>",
    "texture":   "<base64 PNG>"
  }
}
```

## Licence
Research prototype. Not validated for clinical use.
