"""FastAPI backend for the muscle channel marker (multi-task).

Serves the wavelet payload (contract C) and brain assets to the React frontend,
and writes the muscle marks (contract B) on export. Filesystem locations come
from :class:`webui.backend.paths.Paths`; payloads are namespaced by task
(``{SAVE_DIR}/{TASK}/{SUBJ}/...``) so several tasks coexist and the GUI can
switch between them. A built frontend at ``frontend/dist`` is mounted at ``/``.

Endpoints:
    GET  /api/tasks
    GET  /api/tasks/{task}/subjects
    GET  /api/tasks/{task}/subjects/{s}/manifest
    GET  /api/tasks/{task}/subjects/{s}/thumbs/{tag}/{ch}.png
    GET  /api/tasks/{task}/subjects/{s}/spectra/{tag}/{ch}
    GET  /api/tasks/{task}/subjects/{s}/brain.glb
    GET  /api/tasks/{task}/subjects/{s}/electrodes.json
    GET  /api/tasks/{task}/subjects/{s}/muscle
    POST /api/tasks/{task}/subjects/{s}/muscle    {channels: [...]}
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from webui.backend import muscle_io, spectra_io
from webui.backend.paths import Paths
from webui.preproc import config

_SUBJECT_RE = re.compile(r"^D\d+$")
_SAFE_RE = re.compile(r"^[A-Za-z0-9_.-]+$")  # tags / channel names


@lru_cache(maxsize=len(config.KNOWN_TASKS) or 8)
def _paths(task: str) -> Paths:
    if task not in config.KNOWN_TASKS:
        raise HTTPException(status_code=404, detail=f"unknown task: {task!r}")
    return Paths.from_env(task=task)


def _safe_subject(subject: str) -> str:
    if not _SUBJECT_RE.match(subject):
        raise HTTPException(status_code=400, detail=f"bad subject id: {subject!r}")
    return subject


def _safe_token(value: str, kind: str) -> str:
    if not _SAFE_RE.match(value):
        raise HTTPException(status_code=400, detail=f"bad {kind}: {value!r}")
    return value


def _read_manifest(paths: Paths, subject: str) -> dict:
    path = paths.manifest_path(subject)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"no manifest for {subject}")
    with open(path) as fh:
        return json.load(fh)


def _list_subjects(paths: Paths) -> list[dict]:
    root = paths.task_dir()
    out: list[dict] = []
    if not os.path.isdir(root):
        return out
    for subject in sorted(os.listdir(root)):
        man_path = paths.manifest_path(subject)
        if not os.path.exists(man_path):
            continue
        try:
            with open(man_path) as fh:
                man = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        out.append({
            "subject": subject,
            "task": man.get("task", paths.task),
            "tags": man.get("tags", []),
            "n_channels": len(man.get("channels", [])),
            "has_recon": bool(man.get("has_recon"))
            and os.path.exists(paths.brain_glb_path(subject)),
        })
    return out


app = FastAPI(title="Muscle Channel Marker", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "tasks": list(config.KNOWN_TASKS)}


@app.get("/api/tasks")
def list_tasks() -> list[dict]:
    """All known tasks with whether they're configured and how much data exists."""
    out: list[dict] = []
    for task in config.KNOWN_TASKS:
        paths = _paths(task)
        out.append({
            "task": task,
            "label": config.task_label(task),
            "configured": config.is_configured(task),
            "n_subjects": len(_list_subjects(paths)),
        })
    return out


@app.get("/api/tasks/{task}/subjects")
def list_subjects(task: str) -> list[dict]:
    return _list_subjects(_paths(task))


@app.get("/api/tasks/{task}/subjects/{subject}/manifest")
def get_manifest(task: str, subject: str) -> dict:
    return _read_manifest(_paths(task), _safe_subject(subject))


@app.get("/api/tasks/{task}/subjects/{subject}/thumbs/{tag}/{channel}.png")
def get_thumb(task: str, subject: str, tag: str, channel: str):
    paths = _paths(task)
    subject = _safe_subject(subject)
    tag = _safe_token(tag, "tag")
    channel = _safe_token(channel, "channel")
    path = paths.thumb_path(subject, tag, channel)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="thumb not found")
    return FileResponse(path, media_type="image/png")


@app.get("/api/tasks/{task}/subjects/{subject}/spectra/{tag}/{channel}")
def get_spectra(task: str, subject: str, tag: str, channel: str) -> dict:
    paths = _paths(task)
    subject = _safe_subject(subject)
    tag = _safe_token(tag, "tag")
    channel = _safe_token(channel, "channel")
    h5 = paths.tfr_path(subject, tag)
    if not os.path.exists(h5):
        raise HTTPException(status_code=404, detail=f"no {tag}-tfr.h5 for {subject}")
    try:
        return spectra_io.slice_channel(h5, channel)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/tasks/{task}/subjects/{subject}/brain.glb")
def get_brain(task: str, subject: str):
    paths = _paths(task)
    subject = _safe_subject(subject)
    path = paths.brain_glb_path(subject)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="no brain.glb (no recon)")
    return FileResponse(path, media_type="model/gltf-binary")


@app.get("/api/tasks/{task}/subjects/{subject}/electrodes.json")
def get_electrodes(task: str, subject: str):
    paths = _paths(task)
    subject = _safe_subject(subject)
    path = paths.electrodes_path(subject)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="no electrodes.json (no recon)")
    return FileResponse(path, media_type="application/json")


@app.get("/api/tasks/{task}/subjects/{subject}/muscle")
def get_muscle(task: str, subject: str) -> dict:
    paths = _paths(task)
    subject = _safe_subject(subject)
    channels = muscle_io.read_muscle_csv(paths.muscle_csv_path(subject))
    return {"subject": subject, "task": task, "channels": channels}


class MuscleBody(BaseModel):
    channels: list[str] = []
    writeback_tsv: bool = True


@app.post("/api/tasks/{task}/subjects/{subject}/muscle")
def post_muscle(task: str, subject: str, body: MuscleBody):
    paths = _paths(task)
    subject = _safe_subject(subject)
    try:
        result = muscle_io.save_muscle_marks(
            subject,
            body.channels,
            csv_path=paths.muscle_csv_path(subject),
            clean_ieeg_dir=paths.clean_ieeg_dir(subject),
            task=paths.task,
            writeback_tsv=body.writeback_tsv,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result["task"] = task
    return JSONResponse(result)


# --- mount built frontend (production single-port) ---------------------------
_DIST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "frontend",
    "dist",
)
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="frontend")
