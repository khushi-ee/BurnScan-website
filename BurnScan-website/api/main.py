"""
BurnScan-website / api / main.py
FastAPI backend — deploy to Render.com (free, permanent URL).
"""

import base64
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# ── Import pipeline ───────────────────────────────────────────────────────────
# On Render: installed from requirements.txt via GitHub
# Locally / Colab: sibling burnscan-core directory
try:
    from pipeline import (
        decode_image, run_full_pipeline,
        overlay_grid_figure, classify_burn, fig_to_png_bytes,
    )
except ModuleNotFoundError:
    _core = Path(__file__).resolve().parent.parent.parent / "burnscan-core"
    sys.path.insert(0, str(_core))
    from pipeline import (
        decode_image, run_full_pipeline,
        overlay_grid_figure, classify_burn, fig_to_png_bytes,
    )

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="BurnScan API",
    description="AIIMS Paediatric Burns Analysis — Research Prototype",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/analyse")
async def analyse(
    file:        UploadFile    = File(...),
    k:           int           = Form(10),
    patient_id:  Optional[str] = Form(None),
    patient_age: Optional[int] = Form(None),
    burn_cause:  Optional[str] = Form(None),
):
    if file.content_type not in ("image/jpeg", "image/png", "image/jpg"):
        raise HTTPException(400, detail="Only JPG and PNG images are accepted.")
    if not (5 <= k <= 30):
        raise HTTPException(400, detail="Block size k must be between 5 and 30.")

    raw = await file.read()
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(413, detail="Image too large. Max 20 MB.")

    try:
        img_bgr = decode_image(raw)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))

    rgb, burn_r, depth_r, texture_r = run_full_pipeline(img_bgr, k=k)
    result = classify_burn(burn_r, depth_r, texture_r)

    name        = patient_id or "case"
    fig_burn    = overlay_grid_figure(rgb, burn_r,    f"{name} – Burn Mask Grid", k)
    fig_depth   = overlay_grid_figure(rgb, depth_r,   f"{name} – Depth Values",   k)
    fig_texture = overlay_grid_figure(rgb, texture_r, f"{name} – Texture Values", k)

    def b64(data: bytes) -> str:
        return base64.b64encode(data).decode()

    return JSONResponse({
        "status":        "ok",
        "timestamp":     datetime.utcnow().isoformat(),
        "patient_id":    patient_id,
        "patient_age":   patient_age,
        "burn_cause":    burn_cause,
        "block_size_k":  k,
        "classification": {
            "degree":      result["degree"],
            "confidence":  result["confidence"],
            "tbsa_pct":    result["tbsa_pct"],
            "colour":      result["colour"],
            "explanation": result["explanation"],
        },
        "grids": {
            "burn_mask": b64(fig_to_png_bytes(fig_burn)),
            "depth":     b64(fig_to_png_bytes(fig_depth)),
            "texture":   b64(fig_to_png_bytes(fig_texture)),
        },
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
