"""Shared preprocessing config for the muscle-marker data prep.

Every value here is transcribed **verbatim** from the reference pipeline
``plan_muscle_gui/refs/batch_preproc.py`` (the wavelet block, L268-322) so the
spectra this tool generates are numerically identical to Baishen's grid figures.
Do not "tidy" these numbers without re-checking that file.

Event windows are expressed as ``EventSpec`` entries:

* ``epoch``      -- the ``trial_ieeg`` event query string.
* ``window``     -- ``(t0, t1)`` analysis window, seconds, relative to event onset.
* ``tag``        -- short label used for filenames / GUI tabs (``Cue`` etc.).
* ``baseline``   -- True for the single event whose ``BASELINE_WIN`` crop is used
                    as the ratio baseline for *all* tags of the task.

In ``batch_preproc.py`` the trial is actually epoched on a padded window
``(t0 - 0.5, t1 + 0.5)`` and then ``crop_pad("0.5s")`` trims the padding back to
``(t0, t1)``; ``make_spectra`` reproduces that exactly.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EventSpec:
    epoch: str
    window: tuple[float, float]
    tag: str
    baseline: bool = False


# --- wavelet / display parameters (refs/batch_preproc.py L298-322) -----------
WAVELET_DECIM_HZ = 200          # decim = int(sfreq / 200)  -> ~1/10 timepoints
WAVELET_VLIM = (-2.0, 2.0)      # chan_grid(..., vlim=(-2, 2)); dB display range
BASELINE_WIN = (-0.5, 0.0)      # spectra.copy().crop(-0.5, 0) for the baseline
CROP_PAD = "0.5s"               # crop_pad(spectra, "0.5s")
OUTLIER_SD = 10                 # outliers_to_nan(trials, outliers=10)
CMAP = "parula"                 # ieeg.viz.parula.parula_map

# --- per-task event windows (refs/batch_preproc.py L268-287) -----------------
# CORRECT trials only; the Cue epoch supplies the baseline for the whole task.
TASK_EVENTS: dict[str, list[EventSpec]] = {
    "LexicalDecRepDelay": [
        EventSpec("Cue/CORRECT", (-0.5, 3.0), "Cue", baseline=True),
        EventSpec("Auditory_stim/CORRECT", (-0.5, 3.0), "Auditory"),
        EventSpec("Go/CORRECT", (-0.5, 1.0), "Go"),
        EventSpec("Resp/CORRECT", (-0.5, 1.0), "Resp"),
    ],
    "LexicalDecRepNoDelay": [
        EventSpec("Cue/Repeat/CORRECT", (-0.5, 3.0), "Cue", baseline=True),
        EventSpec("Auditory_stim/Repeat/CORRECT", (-0.5, 1.0), "Auditory"),
        EventSpec("Resp/Repeat/CORRECT", (-0.5, 1.0), "Resp"),
    ],
    # UniquenessPoint: reserved -- event queries / windows / baseline still TBD
    # (see plan_muscle_gui/PLAN.md "Uniqueness point 待补信息").
}

SUPPORTED_TASKS = tuple(TASK_EVENTS.keys())


def tags_for_task(task: str) -> list[str]:
    """Ordered tag list for a task (``["Cue", "Auditory", "Go", "Resp"]``)."""
    return [ev.tag for ev in events_for_task(task)]


def events_for_task(task: str) -> list[EventSpec]:
    try:
        events = TASK_EVENTS[task]
    except KeyError as exc:
        raise KeyError(
            f"Unsupported task {task!r}; known tasks: {SUPPORTED_TASKS}"
        ) from exc
    # The baseline event must come first so make_spectra has the baseline ready
    # before any later tag needs it (Cue is first in both task lists).
    if not events[0].baseline:
        raise ValueError(
            f"First event for {task!r} must be the baseline event (got {events[0].tag})"
        )
    return events


def task_nosep(task: str) -> str:
    """``LexicalDecRepDelay`` -> same; BIDS filenames drop underscores."""
    return task.replace("_", "")
