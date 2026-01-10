# Emoji Art Generator (v5) — Python Implementation Instructions (Codex-Optimized)

These instructions revise the project to a **Python-first implementation**. The conversion and export pipeline runs **server-side in Python** (FastAPI), using standardized emoji image assets for consistent output across platforms.

---

## 0) Objective

Build a mobile-first web app that converts an uploaded image into **emoji mosaic art**:

**Upload → Crop → Convert → Export**

Primary goals:
- High-quality emoji matching using perceptual features (Lab + edge density)
- Consistent output across platforms (use standardized emoji assets, not OS emoji fonts)
- Deterministic output option (stable for same inputs/settings)
- Strong caching and predictable performance
- Minimal persistence (no stored user images by default)

Non-goals:
- No manual per-cell editor
- No accounts/auth
- No long-running background job system (unless later needed)

---

## 1) Hard Constraints (MUST)

1. **Max grid size:** output grid must be `<= 120` emojis in **either** dimension. Clamp early.
2. **Standardized emoji assets:** use one emoji asset set everywhere (recommended: Twemoji PNGs).
3. **Export rules:**
   - **PNG** supports transparency (required for transparent background).
   - **JPG** does **not** support transparency; requires solid background.
4. **No user image persistence by default:**
   - process uploads in memory
   - do not write uploads to disk unless explicitly enabled
5. **Versioned dataset:** emoji feature dataset files are versioned and immutable.

---

## 2) High-Level Architecture

### 2.1 Backend (Python)
- **FastAPI** server
- Serves:
  - API endpoints for conversion and exports
  - Static frontend files
  - Versioned emoji dataset assets (optional; usually loaded server-side)

### 2.2 Frontend (minimal JS)
Mobile-first UI with:
- Image upload
- Crop UI (client-side crop selection)
- Settings controls
- Preview display
- Export buttons

Frontend submits:
- image file
- crop rectangle (x, y, w, h) in **image pixel coordinates**
- settings (grid size, deterministic, dithering, background, etc.)

> The actual conversion is performed in Python.

---

## 3) Tech Stack (Recommended)

### Backend
- Python 3.11+
- FastAPI + Uvicorn
- Pillow (PIL) for image IO and composition
- NumPy for fast feature computation
- Optional:
  - scikit-image (for Sobel/edges + robust Lab conversion)
  - or implement RGB→Lab conversion locally to avoid heavier deps
- Disk cache (optional): `diskcache` or simple file cache

### Frontend
- Vanilla + a small cropper library (e.g., Cropper.js), or React if preferred
- Mobile-first CSS (MUI/Tailwind optional)

---

## 4) Repository Structure (suggested)

```
/app
  main.py
  /api
    routes.py
    schemas.py
  /core
    dataset.py
    preprocess.py
    features.py
    matcher.py
    dithering.py
    render.py
    hashing.py
    cache.py
  /assets
    /twemoji_png/              # standardized emoji images (source of truth)
  /data
    emoji_features_vX.json
    emoji_features_vX.npy      # feature vectors (float32) or .npz
    emoji_index_vX.json        # emoji list and metadata
/web
  index.html
  app.js
  styles.css
/scripts
  build_emoji_dataset.py
/tests
  unit/
  golden/
```

---

## 5) API Contract (MUST)

### 5.1 POST `/api/convert`
**Purpose:** Convert image to emoji grid (and optionally return a preview image).

Request:
- `multipart/form-data`
  - `file`: image (JPG/PNG)
  - `crop`: JSON string: `{ "x": int, "y": int, "w": int, "h": int }` in original image pixels
  - `settings`: JSON string:
    - `max_dim`: int (default 120; must clamp to <=120)
    - `grid_w`: optional int
    - `grid_h`: optional int
    - `lock_aspect`: bool
    - `dithering`: bool
    - `deterministic`: bool (default true)
    - `emoji_set`: "full" | other subsets (optional)
    - `bg_mode`: "transparent" | "solid"
    - `bg_color`: "#RRGGBB" (required when bg_mode="solid")
    - `weights`: optional tuning (color/edge/alpha)

Response (JSON):
- `grid_w`, `grid_h`
- `grid`: list of strings (each row is a string of emojis, compact)
- `grid_spaced`: optional (space-separated)
- `preview_png_base64`: optional for immediate preview (OK up to ~120x120)
- `hash`: output hash for caching/repeatability
- `warnings`: list of strings

> If payload size is a concern, return `preview_url` instead of base64.

### 5.2 GET `/api/export/text?hash=...&spaced=0|1`
Returns a `.txt` file derived from cached conversion result.

### 5.3 GET `/api/export/png?hash=...&bg=transparent|solid&color=#RRGGBB`
Returns PNG mosaic.

### 5.4 GET `/api/export/jpg?hash=...&color=#RRGGBB`
Returns JPG mosaic (solid background only).

Caching model:
- The server caches conversion outputs by `hash` (see §8).

---

## 6) Conversion Pipeline (Python) — MUST implement

### 6.1 Steps
1. **Decode** upload via Pillow
2. **Apply crop** rectangle
3. **Compute grid size** with clamp (<=120 in max dimension)
4. **Resample** cropped image to `grid_w x grid_h` (or a higher sample per cell if needed)
5. For each cell:
   - compute feature vector (Lab mean + edge density [+ alpha coverage])
   - find nearest emoji feature vector
6. Produce emoji grid
7. Optionally render preview mosaic as PNG for immediate display

### 6.2 Grid sizing rules
- Default: keep crop aspect ratio and set the longest side to `max_dim` (<=120)
- If user provides `grid_w` or `grid_h`:
  - clamp to <=120
  - preserve aspect ratio if `lock_aspect` true
- Emit warnings if clamped.

---

## 7) Emoji Dataset and Pre-Indexing (Python)

### 7.1 Source of truth
Use standardized emoji assets (recommended: **Twemoji PNG 72x72**).
Store them in `/app/assets/twemoji_png/` with predictable filenames (codepoint-based).

### 7.2 Pre-indexing script: `/scripts/build_emoji_dataset.py`
**Input:**
- emoji list (Unicode sequences) + asset directory

**For each emoji PNG:**
- Load RGBA
- Compute features:
  - Mean Lab: (L*, a*, b*)  — use `skimage.color.rgb2lab` or a local converter
  - Edge density: Sobel magnitude mean on luminance
  - Alpha coverage: mean(alpha > threshold) (optional but recommended)

**Output:**
- `emoji_index_vX.json`:
  - `version`, `emoji_list`, `asset_paths`, optional categories
- `emoji_features_vX.npy` or `.npz`:
  - float32 array shape `(N, D)` aligned with emoji_list

**Versioning:**
- bump `vX` when emoji list or feature definition changes

### 7.3 Runtime loading
Load dataset once at process startup:
- features: `numpy.ndarray` float32 (C-contiguous)
- emojis: list[str]
- optionally precompute:
  - norms for faster distance calc
  - per-emoji small metadata

---

## 8) Matching Algorithm (Python)

### 8.1 Distance function (recommended)
Weighted distance for feature vectors:
- `d = w_color * ||Lab_cell - Lab_emoji||2 + w_edge * (edge_cell - edge_emoji)^2 + w_alpha * (alpha_cell - alpha_emoji)^2`

Use squared distance to avoid sqrt.

Default weights:
- color dominates (e.g., `w_color=1.0`, `w_edge=0.2`, `w_alpha=0.1`)
Allow tuning via settings.

### 8.2 Search strategy
Start with brute force over numpy arrays:
- For each cell feature `f`:
  - compute `(features - f)` efficiently
  - reduce to distances
  - argmin

This is fast enough for N≈3k–5k emojis and grids <= 14,400 cells.

Optional optimization (only if needed):
- KDTree / BallTree from scikit-learn
- HNSW (not required initially)

### 8.3 Tie-breaking and determinism
If top-k within epsilon:
- Deterministic mode:
  - seed = `blake2b(image_bytes + crop + settings + dataset_version)`
  - select among candidates with seeded PRNG
- Non-deterministic mode:
  - random selection

---

## 9) Rendering Mosaic (Python)

### 9.1 Render rules
To export PNG/JPG, compose a mosaic by pasting emoji PNGs into a canvas:
- cell size: configurable (default 24–32 px for preview; 48+ px for export)
- for each grid cell:
  - open emoji PNG (cache these images in-memory!)
  - resize to cell size (use Pillow `Resampling.LANCZOS`)
  - paste onto output canvas

Background:
- PNG transparent: keep alpha, no fill
- PNG solid or JPG: fill with bg color before pasting

### 9.2 Emoji PNG caching
Implement an LRU cache for decoded emoji images:
- key: emoji asset path + cell_size
- value: resized RGBA image

This cache is critical for export speed.

---

## 10) Caching (MUST)

### 10.1 Dataset caching
- Dataset is loaded at process startup (memory resident)
- Assets are local files in the container/app (immutable)

### 10.2 Conversion result caching
Cache by conversion hash:
- key: `hash(image_bytes + crop + settings + dataset_version)`
- value:
  - `grid` (list[str])
  - `grid_w`, `grid_h`
  - optional preview bytes
  - timestamps

Use:
- in-memory LRU for most recent (fast)
- optional disk cache for resilience across restarts (nice-to-have)

### 10.3 Cell-level memoization (optional)
Quantize cell features (Lab bins + edge bin) and memoize nearest emoji index:
- improves speed for repeated similar colors

---

## 11) Frontend Requirements (minimal)

- Use a cropper UI that provides crop rectangle in original image pixel coords.
- Submit crop + settings + file to `/api/convert`.
- Display:
  - preview image (PNG returned base64 or URL)
  - resulting grid dimension
  - warnings
- Export buttons call `/api/export/...` with `hash`.

---

## 12) Testing (MUST)

### 12.1 Unit tests
- Grid sizing + clamping logic
- Feature extraction:
  - RGB→Lab conversion (spot check)
  - edge metric stability
- Deterministic tie-breaking is stable
- Export rendering:
  - PNG transparency preserved
  - JPG forces background

### 12.2 Golden tests
Fixture images (small) produce stable outputs:
- Store expected hash of emoji grid for deterministic mode
- Validate no regressions after refactors

---

## 13) Deployment (Heroku-friendly)

- Use Uvicorn for FastAPI:
  - `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Include emoji assets and dataset files in slug (repo)
- Do not generate dataset at runtime on Heroku filesystem (ephemeral)
- Set reasonable memory usage (emoji asset cache bounded)

---

## 14) Codex Tasking Checklist (execution order)

1. Scaffold FastAPI app + static web serving
2. Add `/scripts/build_emoji_dataset.py` and generate dataset v1
3. Implement dataset loader (`dataset.py`)
4. Implement feature extraction (`features.py`)
5. Implement matcher (`matcher.py`)
6. Implement conversion endpoint (`/api/convert`) with caching
7. Implement render/export endpoints (`/api/export/*`) with emoji image cache
8. Implement minimal frontend upload/crop/preview/export UI
9. Add unit + golden tests
10. Package for deployment (Procfile, requirements, static assets)

---

## 15) Notes for Codex

- Keep conversion logic independent of FastAPI (pure functions) to maximize testability.
- Use NumPy for vector operations; avoid Python loops in inner matching loop if possible.
- Cache emoji images aggressively during export.
- Prefer PNG exports for transparency; enforce JPG background color constraint.
- Use versioned dataset filenames; include dataset version in conversion hash.
