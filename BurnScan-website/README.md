# BurnScan-website

Web frontend + FastAPI backend for the AIIMS Paediatric Burns Analyser.

---

## Folder structure

```
BurnScan-website/
│
├── api/                        ← Python backend (deploy to Render)
│   ├── main.py                   FastAPI app
│   └── requirements.txt          Python dependencies
│
├── frontend/                   ← Static website (deploy to Vercel)
│   └── index.html                Complete single-file app
│
├── render.yaml                 ← Render auto-deploy config
├── vercel.json                 ← Vercel routing config
└── README.md
```

---

## Before you deploy — 2 things to edit

### 1. `api/requirements.txt`
Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username:
```
git+https://github.com/YOUR_GITHUB_USERNAME/burnscan-core.git
```

### 2. `frontend/index.html`
After deploying the API, find this line near the bottom and update it:
```javascript
const API_URL = "REPLACE_WITH_RENDER_URL";
// → becomes →
const API_URL = "https://burnscan-api.onrender.com";
```

---

## Deploy to Render (API backend) — free & permanent

1. Go to **https://render.com** → sign up with GitHub
2. Click **New → Web Service**
3. Connect your `BurnScan-website` GitHub repo
4. Fill in:
   - **Root Directory:** `api`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment:** Python 3
5. Click **Deploy**
6. After ~3 minutes you get a URL like `https://burnscan-api.onrender.com`
7. Test: open `https://burnscan-api.onrender.com/api/health` → should return `{"status":"ok"}`
8. Swagger UI: `https://burnscan-api.onrender.com/api/docs`

---

## Deploy to Vercel (frontend) — free & permanent

> Do this AFTER deploying the API and updating `API_URL` in `index.html`

1. Go to **https://vercel.com** → sign up with GitHub
2. Click **Add New → Project**
3. Import your `BurnScan-website` repo
4. Vercel reads `vercel.json` automatically — no config needed
5. Click **Deploy**
6. You get a permanent URL like `https://burnscan-website.vercel.app`

---

## Run locally (no deploy needed)

**Terminal 1 — Start API:**
```bash
cd api
# Point Python to burnscan-core (sibling directory)
PYTHONPATH=../../burnscan-core pip install -r requirements.txt
PYTHONPATH=../../burnscan-core uvicorn main:app --reload --port 8000
```

**Terminal 2 — Serve frontend:**
```bash
cd frontend
python -m http.server 8080
```
Open **http://localhost:8080** — the `API_URL` placeholder auto-falls back to `localhost:8000`.

---

## API reference

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Liveness check |
| GET | `/api/docs` | Swagger UI |
| POST | `/api/analyse` | Upload image → JSON + base64 grid PNGs |

**POST `/api/analyse` — form fields**

| Field | Type | Default | Notes |
|---|---|---|---|
| `file` | File (JPG/PNG) | required | Max 20 MB |
| `k` | int | 10 | Block size 5–30 |
| `patient_id` | str | — | Optional |
| `patient_age` | int | — | Age in years |
| `burn_cause` | str | — | Flame / Scald / etc. |

**Response JSON**
```json
{
  "status": "ok",
  "classification": {
    "degree":      "2nd Degree (Partial-thickness)",
    "confidence":  0.72,
    "tbsa_pct":    14.3,
    "colour":      "#dd6b20",
    "explanation": "..."
  },
  "grids": {
    "burn_mask": "<base64 PNG>",
    "depth":     "<base64 PNG>",
    "texture":   "<base64 PNG>"
  }
}
```

---

## Demo login credentials

| Username | Password | Role |
|---|---|---|
| dr.sharma | aiims2024 | Doctor |
| dr.mehta | burns123 | Resident |
| admin | admin123 | Admin |

To add real users: edit the `USERS` dict in `frontend/index.html`.

---

## Important notes

**Render free tier:** API sleeps after 15 min inactivity.
First request after sleep takes ~30 seconds to wake up — warn users.
Upgrade to Render Starter ($7/mo) for always-on.

**Confidence & TBSA:** Both are heuristic placeholders.
Replace `classify_burn()` in `pipeline.py` with a trained model once
AIIMS provides labelled cases.

---

## Disclaimer
Research prototype only. Not validated for clinical use.
All outputs must be reviewed by a qualified paediatric burns specialist.
AIIMS New Delhi · Paediatric Surgery Department.
