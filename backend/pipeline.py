"""
burnscan-core / pipeline.py
============================
Exact replication of the Colab notebook pipeline.
Accepts numpy arrays (not file paths) so it works both in Colab
and when called from the web API.

Functions
---------
block_average(img, k)              — identical to Colab version
extract_features(img_bgr)          — identical logic, array-in instead of path-in
run_full_pipeline(img_bgr, k)      — runs block_average on all 3 channels
overlay_grid_figure(img, values,   — identical rendering to Colab overlay_grid,
                    title, k)        returns a matplotlib Figure instead of plt.show()
classify_burn(burn_r, depth_r,     — heuristic degree classifier
              texture_r)
fig_to_png_bytes(fig)              — serialise figure → PNG bytes for the API
"""

import io
import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")                          # non-interactive backend
import matplotlib.pyplot as plt
from skimage.feature import local_binary_pattern


# ─────────────────────────────────────────────────────────────────────────────
# 1.  block_average  (verbatim from Colab)
# ─────────────────────────────────────────────────────────────────────────────
def block_average(img: np.ndarray, k: int) -> np.ndarray:
    """
    Downsample a 2-D image by averaging non-overlapping k×k blocks.
    Identical to the loop version in the Colab notebook.
    """
    h, w = img.shape
    h2, w2 = h // k, w // k
    reduced = np.zeros((h2, w2), dtype=np.float64)
    for i in range(h2):
        for j in range(w2):
            block = img[i*k:(i+1)*k, j*k:(j+1)*k]
            reduced[i, j] = np.mean(block)
    return reduced


# ─────────────────────────────────────────────────────────────────────────────
# 2.  extract_features  (verbatim from Colab, path → array)
# ─────────────────────────────────────────────────────────────────────────────
def extract_features(img_bgr: np.ndarray):
    """
    Accepts a BGR numpy array (as returned by cv2.imdecode / cv2.imread).
    Returns (rgb, burn_mask, depth, texture) — identical to Colab version.

    Steps
    -----
    1. Resize to 256×256
    2. Convert BGR → RGB, HSV, LAB
    3. Build burn mask: A > mean_A + 0.8·σ_A  AND  S > mean_S
    4. Morphological close (7×7) to fill holes in mask
    5. Depth  = L channel masked to burn region
    6. Texture = LBP(P=8, R=1, uniform) on grayscale masked to burn region,
                 normalised to [0, 255]
    """
    img  = cv2.resize(img_bgr, (256, 256))
    rgb  = cv2.cvtColor(img,  cv2.COLOR_BGR2RGB)
    hsv  = cv2.cvtColor(rgb,  cv2.COLOR_RGB2HSV)
    lab  = cv2.cvtColor(rgb,  cv2.COLOR_RGB2LAB)

    H, S, V = cv2.split(hsv)
    L, A, B = cv2.split(lab)
    gray    = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    meanA, stdA = float(np.mean(A)), float(np.std(A))
    meanS       = float(np.mean(S))

    # ── Burn mask (same threshold logic as Colab) ──────────────────────────
    burn_mask = (
        (A > meanA + 0.8 * stdA) & (S > meanS)
    ).astype(np.uint8) * 255

    burn_mask = cv2.morphologyEx(
        burn_mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8)
    )

    # ── Depth channel (luminance inside burn region) ───────────────────────
    depth = cv2.bitwise_and(L, L, mask=burn_mask)

    # ── Texture via LBP (identical params to Colab) ────────────────────────
    burn_gray = cv2.bitwise_and(gray, gray, mask=burn_mask)
    lbp       = local_binary_pattern(burn_gray, 8, 1, "uniform")
    texture   = cv2.normalize(
        lbp, None, 0, 255, cv2.NORM_MINMAX
    ).astype(np.uint8)

    return rgb, burn_mask, depth, texture


# ─────────────────────────────────────────────────────────────────────────────
# 3.  run_full_pipeline  (last Colab cell logic)
# ─────────────────────────────────────────────────────────────────────────────
def run_full_pipeline(img_bgr: np.ndarray, k: int = 10):
    """
    Runs the complete pipeline matching the last Colab cell.

    Returns
    -------
    rgb          : (256,256,3) uint8 — original resized image in RGB
    burn_r       : (h2,w2)    uint8 — block-averaged burn mask, binarised to 0/1
    depth_r      : (h2,w2)  float64 — block-averaged depth values
    texture_r    : (h2,w2)  float64 — block-averaged texture values
    """
    rgb, burn_mask, depth, texture = extract_features(img_bgr)

    burn_r    = block_average(burn_mask, k)
    depth_r   = block_average(depth,     k)
    texture_r = block_average(texture,   k)

    burn_r = (burn_r > 0).astype(np.uint8)   # binarise (exact Colab step)

    return rgb, burn_r, depth_r, texture_r


# ─────────────────────────────────────────────────────────────────────────────
# 4.  overlay_grid_figure  (identical rendering to Colab overlay_grid)
# ─────────────────────────────────────────────────────────────────────────────
def overlay_grid_figure(
    img: np.ndarray,
    values: np.ndarray,
    title: str,
    k: int,
) -> plt.Figure:
    """
    Exact visual replica of the Colab overlay_grid() function.
    Returns a matplotlib Figure instead of calling plt.show().

    - Yellow text labels at each block centre (same fontsize=6)
    - Handles both 2-D (grayscale) and 3-D (RGB) images
    """
    fig, ax = plt.subplots(figsize=(5, 5))

    if img.ndim == 2:
        ax.imshow(img, cmap="gray")
    else:
        ax.imshow(img)

    h, w = values.shape
    for i in range(h):
        for j in range(w):
            y = i * k + k // 2
            x = j * k + k // 2
            ax.text(
                x, y,
                f"{int(values[i, j])}",
                color="yellow",
                fontsize=6,
                ha="center",
                va="center",
            )

    ax.set_title(title)
    ax.axis("off")
    plt.tight_layout()
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 5.  classify_burn  — heuristic degree estimator
# ─────────────────────────────────────────────────────────────────────────────
def classify_burn(
    burn_r: np.ndarray,
    depth_r: np.ndarray,
    texture_r: np.ndarray,
) -> dict:
    """
    Heuristic rule-based classifier.
    Replace body with a trained model once labelled data is available.

    Returns a dict with keys:
        degree      : str
        confidence  : float  (0–1)  — rule-based, NOT a statistical probability
        tbsa_pct    : float          — placeholder, needs body-map for real value
        colour      : str   hex      — for UI badge
        explanation : str
    """
    active = burn_r > 0
    n_active = active.sum()

    if n_active == 0:
        return {
            "degree": "No burn detected",
            "confidence": 0.0,
            "tbsa_pct": 0.0,
            "colour": "#6b7280",
            "explanation": "Burn mask is empty — no region matched the colour/saturation thresholds.",
        }

    mean_d = float(depth_r[active].mean())
    mean_t = float(texture_r[active].mean())
    coverage = float(active.mean())

    score = 0
    notes = []

    # Depth scoring (L channel in burn zone)
    if mean_d < 70:
        score += 2
        notes.append(f"dark/charred region (L={mean_d:.0f}<70)")
    elif mean_d < 120:
        score += 1
        notes.append(f"medium luminance (L={mean_d:.0f})")
    else:
        notes.append(f"bright/superficial region (L={mean_d:.0f})")

    # Texture scoring (LBP complexity)
    if mean_t > 160:
        score += 2
        notes.append(f"high texture complexity (LBP={mean_t:.0f}>160)")
    elif mean_t > 110:
        score += 1
        notes.append(f"moderate texture (LBP={mean_t:.0f})")
    else:
        notes.append(f"smooth texture (LBP={mean_t:.0f}) — likely superficial")

    if score >= 4:
        degree  = "3rd Degree (Full-thickness)"
        colour  = "#e53e3e"
        conf    = min(0.55 + coverage * 0.2, 0.85)
    elif score >= 2:
        degree  = "2nd Degree (Partial-thickness)"
        colour  = "#dd6b20"
        conf    = min(0.50 + coverage * 0.2, 0.80)
    else:
        degree  = "1st Degree (Superficial)"
        colour  = "#38a169"
        conf    = min(0.60 + coverage * 0.15, 0.80)

    tbsa_pct = round(coverage * 100 * 0.9, 1)   # placeholder scaling

    explanation = (
        f"Burn coverage: {coverage*100:.1f}% of image. "
        f"Mean depth (L): {mean_d:.1f}. "
        f"Mean texture (LBP): {mean_t:.1f}. "
        f"Score: {score}/4. "
        f"Indicators: {'; '.join(notes)}."
    )

    return {
        "degree":      degree,
        "confidence":  round(conf, 3),
        "tbsa_pct":    tbsa_pct,
        "colour":      colour,
        "explanation": explanation,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6.  Utility
# ─────────────────────────────────────────────────────────────────────────────
def fig_to_png_bytes(fig: plt.Figure) -> bytes:
    """Serialise a matplotlib Figure to PNG bytes and close it."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def decode_image(file_bytes: bytes) -> np.ndarray:
    """Decode raw uploaded bytes → BGR numpy array."""
    arr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image. Ensure it is a valid JPG or PNG.")
    return img
