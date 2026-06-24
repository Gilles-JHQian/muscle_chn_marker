# Muscle Channel Marker — Web GUI

A standalone tool to accelerate manual marking of **muscle-artifact channels** in
the Cogan Lab Lexical Decision Repeat tasks. It replaces the old workflow of
hand-scrolling `Baishen_Figs/{SUBJ}/wavelet/*.jpg` grids and hand-writing a CSV
(see `plan_muscle_gui/refs/readme.md` Step 5).

- **Left** — the subject's 3D cortical (pial) surface with electrodes; the
  currently selected channel is highlighted, already-marked muscle channels are
  shown in a distinct colour.
- **Right** — a tiled grid of every channel's wavelet spectrogram for the current
  event tag; click one to see its 4-stage zoomable/pannable heatmaps, tick
  *muscle yes/no*, and export.
- **Export** — writes the contract-B CSV to `muscle_chans/` and writes
  `status=bad, status_description=muscle` back into every run's clean
  `channels.tsv`.

The full design lives in [`plan_muscle_gui/PLAN.md`](plan_muscle_gui/PLAN.md);
the data contracts (A consumed / B produced / C internal) live in
[`plan_muscle_gui/PAYLOAD_SPEC.md`](plan_muscle_gui/PAYLOAD_SPEC.md).

## Layout

```
webui/
  preproc/config.py            # TASK_EVENTS, wavelet params (verbatim from refs/batch_preproc.py)
  dataprep/make_spectra.py     # clean -> CAR + wavelet -> {tag}-tfr.h5 + thumbs + manifest (sbatch-heavy)
  export/glb.py                # dependency-free numpy glTF (.glb) writer + mesh merge
  export/export_subject_brain.py  # ECoG Recon pial -> brain.glb + electrodes.json (surfaceRAS)
  backend/app.py               # FastAPI: serves spectra / brain / electrodes + writes muscle
  backend/{paths,spectra_io,muscle_io}.py
frontend/                      # React 18 + Vite 5 + three.js (R3F/drei) + react-plotly
scripts/{serve.sh, dev.sh}     # production (single-port) / dev (two-process) launchers
sbatch/sbatch_spectra.sh       # make_spectra SLURM array
```

## Environment

- **Python**: conda env `Lexical_NoDelay` (has `ieeg`, `mne 1.10`, `nibabel`,
  `h5py`, `numpy`, `matplotlib`). Install the web deps once:
  ```bash
  conda run -n Lexical_NoDelay pip install fastapi "uvicorn[standard]"
  ```
- **Node**: `module load Node.js/18.14.2`
  (or `/opt/apps/rhel8/node-v18.14.2-linux-x64/bin` on PATH).

Paths are resolved from environment variables (with DCC defaults):

| Env | Meaning | Default |
|---|---|---|
| `LAB_ROOT` | root holding `BIDS-1.0_{TASK}/BIDS` | `/cwork/jq81/cogan_lab_box/CoganLab` |
| `MUSCLE_TASK` | task tag (data-prep default; the backend serves *all* tasks) | `LexicalDecRepDelay` |
| `SAVE_DIR` | wavelet / brain payload root, namespaced by task (`{SAVE_DIR}/{TASK}/{SUBJ}/...`) | `<repo>/data/spectra` |
| `RECON_DIR` | ECoG Recon root | `/cwork/jq81/cogan_lab_box/ECoG_Recon` |
| `MUSCLE_CSV_DIR` | contract-B CSV output dir (per task; leave unset for multi-task) | `{BIDS_ROOT}/coganlab_ieeg/muscle_chans` |

### Tasks

The GUI has a task selector; the backend serves every task that has data under
`{SAVE_DIR}/{TASK}/`. Known tasks (`webui/preproc/config.py`):

| Task | Status | Tags |
|---|---|---|
| `LexicalDecRepDelay` | ready | Cue / Auditory / Go / Resp |
| `LexicalDecRepNoDelay` | ready | Cue / Auditory / Resp |
| `UniquenessPoint` | known, **event windows not yet configured** | — |

To enable `UniquenessPoint`, fill in its `TASK_EVENTS[...]` entry (epoch query,
window, tag, baseline) in `webui/preproc/config.py`, then run data-prep for it.

## Quick start

```bash
# 1. Data prep (sbatch-heavy) — one subject, per task:
conda run -n Lexical_NoDelay python -m webui.dataprep.make_spectra \
    --subject D0100 --task LexicalDecRepDelay
conda run -n Lexical_NoDelay python -m webui.dataprep.make_spectra \
    --subject D0100 --task LexicalDecRepNoDelay

# 2. Brain assets (fast; subjects with ECoG Recon only) — per task:
conda run -n Lexical_NoDelay python -m webui.export.export_subject_brain \
    --subject D0100 --task LexicalDecRepDelay

# 3. Launch (dev, two-process):
bash scripts/dev.sh
# ...then tunnel :5173 from your laptop and switch tasks in the top bar.
```

See [`plan_muscle_gui/PLAN.md`](plan_muscle_gui/PLAN.md) §验证 for the end-to-end
verification checklist.
