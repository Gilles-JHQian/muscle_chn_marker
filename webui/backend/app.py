"""FastAPI backend for the muscle channel marker.

Serves the wavelet payload (contract C) and brain assets to the React frontend,
and writes the muscle marks (contract B) on export. All filesystem locations come
from :class:`webui.backend.paths.Paths` (env-driven). When a built frontend
exists at ``frontend/dist`` it is mounted at ``/`` on the same port.

Endpoints (see plan_muscle_gui/PLAN.md):
    GET  /api/subjects
    GET  /api/subjects/{s}/manifest
    GET  /api/subjects/{s}/thumbs/{tag}/{ch}.png
    GET  /api/subjects/{s}/spectra/{tag}/{ch}
    GET  /api/subjects/{s}/brain.glb
    GET  /api/subjects/{s}/electrodes.json
    GET  /api/subjects/{s}/muscle
    POST /api/subjects/{s}/muscle    {channels: [...]}
"""

from __future__ import annotations

import json
import os
import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from webui.backend import muscle_io, spectra_io
from webui.backend.paths import Paths

PATHS = Paths.from_env()

_SUBJECT_RE = re.compile(r"^D\d+$")
_SAFE_RE = re.compile(r"^[A-Za-z0-9_.-]+$")  # tags / channel names


def _safe_subject(subject: str) -> str:
    if not _SUBJECT_RE.match(subject):
        raise HTTPException(status_code=400, detail=f"bad subject id: {subject!r}")
    return subject


def _safe_token(value: str, kind: str) -> str:
    if not _SAFE_RE.match(value):
        raise HTTPException(status_code=400, detail=f"bad {kind}: {value!r}")
    return value


def _read_manifest(subject: str) -> dict:
    path = PATHS.manifest_path(subject)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"no manifest for {subject}")
    with open(path) as fh:
        return json.load(fh)


app = FastAPI(title="Muscle Channel Marker", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "task": PATHS.task,
        "save_dir": PATHS.save_dir,
        "recon_dir": PATHS.recon_dir,
    }


@app.get("/api/subjects")
def list_subjects() -> list[dict]:
    """Every subject under SAVE_DIR that has a wavelet manifest."""
    root = PATHS.save_dir
    out: list[dict] = []
    if not os.path.isdir(root):
        return out
    for subject in sorted(os.listdir(root)):
        man_path = PATHS.manifest_path(subject)
        if not os.path.exists(man_path):
            continue
        try:
            with open(man_path) as fh:
                man = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        out.append({
            "subject": subject,
            "task": man.get("task", PATHS.task),
            "tags": man.get("tags", []),
            "n_channels": len(man.get("channels", [])),
            "has_recon": bool(man.get("has_recon"))
            and os.path.exists(PATHS.brain_glb_path(subject)),
        })
    return out


@app.get("/api/subjects/{subject}/manifest")
def get_manifest(subject: str) -> dict:
    return _read_manifest(_safe_subject(subject))


@app.get("/api/subjects/{subject}/thumbs/{tag}/{channel}.png")
def get_thumb(subject: str, tag: str, channel: str):
    subject = _safe_subject(subject)
    tag = _safe_token(tag, "tag")
    channel = _safe_token(channel, "channel")
    path = PATHS.thumb_path(subject, tag, channel)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="thumb not found")
    return FileResponse(path, media_type="image/png")


@app.get("/api/subjects/{subject}/spectra/{tag}/{channel}")
def get_spectra(subject: str, tag: str, channel: str) -> dict:
    subject = _safe_subject(subject)
    tag = _safe_token(tag, "tag")
    channel = _safe_token(channel, "channel")
    h5 = PATHS.tfr_path(subject, tag)
    if not os.path.exists(h5):
        raise HTTPException(status_code=404, detail=f"no {tag}-tfr.h5 for {subject}")
    try:
        return spectra_io.slice_channel(h5, channel)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/subjects/{subject}/brain.glb")
def get_brain(subject: str):
    subject = _safe_subject(subject)
    path = PATHS.brain_glb_path(subject)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="no brain.glb (no recon)")
    return FileResponse(path, media_type="model/gltf-binary")


@app.get("/api/subjects/{subject}/electrodes.json")
def get_electrodes(subject: str):
    subject = _safe_subject(subject)
    path = PATHS.electrodes_path(subject)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="no electrodes.json (no recon)")
    return FileResponse(path, media_type="application/json")


@app.get("/api/subjects/{subject}/muscle")
def get_muscle(subject: str) -> dict:
    subject = _safe_subject(subject)
    channels = muscle_io.read_muscle_csv(PATHS.muscle_csv_path(subject))
    return {"subject": subject, "channels": channels}


class MuscleBody(BaseModel):
    channels: list[str] = []
    writeback_tsv: bool = True


@app.post("/api/subjects/{subject}/muscle")
def post_muscle(subject: str, body: MuscleBody):
    subject = _safe_subject(subject)
    try:
        result = muscle_io.save_muscle_marks(
            subject,
            body.channels,
            csv_path=PATHS.muscle_csv_path(subject),
            clean_ieeg_dir=PATHS.clean_ieeg_dir(subject),
            task=PATHS.task,
            writeback_tsv=body.writeback_tsv,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return JSONResponse(result)


# --- mount built frontend (production single-port) ---------------------------
_DIST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "frontend",
    "dist",
)
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="frontend")
