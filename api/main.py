"""
burnscan-website / api / main.py
=================================
FastAPI backend.  Exposes the pipeline from burnscan-core as HTTP endpoints.

Endpoints
---------
POST /api/analyse          — upload image, returns JSON + base64 grid PNGs
GET  /api/health           — liveness probe
"""

import base64
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# ── Make burnscan-core importable ──────────────────────────────────────────
# Adjust this path if your repo layout differs
sys.path.insert(0, str(CORE_PATH))

from pipeline import (
    decode_image,
    run_full_pipeline,
    overlay_grid_figure,
    classify_burn,
    fig_to_png_bytes,
)

# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="BurnScan API",
    description="AIIMS Paediatric Burns Analysis API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # tighten to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/analyse")
async def analyse(
    file: UploadFile = File(...),
    k: int = Form(10),
    patient_id: Optional[str] = Form(None),
    patient_age: Optional[int] = Form(None),
    burn_cause: Optional[str] = Form(None),
):
    # ── Validate ────────────────────────────────────────────────────────────
    if file.content_type not in ("image/jpeg", "image/png", "image/jpg"):
        raise HTTPException(400, "Only JPG and PNG images are accepted.")
    if not (5 <= k <= 30):
        raise HTTPException(400, "Block size k must be between 5 and 30.")

    raw = await file.read()
    if len(raw) > 20 * 1024 * 1024:      # 20 MB cap
        raise HTTPException(413, "Image too large. Maximum size is 20 MB.")

    # ── Run pipeline ────────────────────────────────────────────────────────
    try:
        img_bgr = decode_image(raw)
    except ValueError as e:
        raise HTTPException(400, str(e))

    rgb, burn_r, depth_r, texture_r = run_full_pipeline(img_bgr, k=k)
    result = classify_burn(burn_r, depth_r, texture_r)

    # ── Generate grid figures (exact Colab overlay_grid output) ─────────────
    name = patient_id or "case"

    fig_burn    = overlay_grid_figure(rgb, burn_r,    f"{name} – Burn Mask Grid",  k)
    fig_depth   = overlay_grid_figure(rgb, depth_r,   f"{name} – Depth Values",    k)
    fig_texture = overlay_grid_figure(rgb, texture_r, f"{name} – Texture Values",  k)

    png_burn    = fig_to_png_bytes(fig_burn)
    png_depth   = fig_to_png_bytes(fig_depth)
    png_texture = fig_to_png_bytes(fig_texture)

    def b64(data: bytes) -> str:
        return base64.b64encode(data).decode()

    return JSONResponse({
        "status":       "ok",
        "timestamp":    datetime.utcnow().isoformat(),
        "patient_id":   patient_id,
        "patient_age":  patient_age,
        "burn_cause":   burn_cause,
        "block_size_k": k,
        "classification": {
            "degree":      result["degree"],
            "confidence":  result["confidence"],
            "tbsa_pct":    result["tbsa_pct"],
            "colour":      result["colour"],
            "explanation": result["explanation"],
        },
        "grids": {
            "burn_mask": b64(png_burn),
            "depth":     b64(png_depth),
            "texture":   b64(png_texture),
        },
    })


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
