"""Generate the wavelet payload (contract C) for one subject + task.

This is the *sbatch-heavy* data-prep step. It reproduces the wavelet block of
``plan_muscle_gui/refs/batch_preproc.py`` (L234-322) so the spectra match the
old ``Baishen_Figs/{SUBJ}/wavelet`` grids, then emits the GUI payload:

    {SAVE_DIR}/{SUBJ}/wavelet/
        {tag}-tfr.h5            MNE AverageTFR (n_chan, n_freq, n_time), dB
        thumbs/{tag}/{ch}.png   ~140x90 parula preview per channel
        manifest.json           {subject, task, tags, channels, vlim, cmap, has_recon}

Pipeline (per refs/batch_preproc.py):
    1. raw_from_layout(derivatives/clean, desc='clean', preload=False)
       -> drop_channels(info['bads']) -> load_data() -> CAR (average reference)
    2. for each (epoch, window, tag): trial_ieeg on the padded window ->
       outliers_to_nan(10) -> wavelet_scaleogram(decim=sfreq/200) ->
       crop_pad('0.5s'); the Cue epoch's (-0.5, 0) crop is the ratio baseline;
       average over trials (nanmean) -> rescale ratio vs baseline -> log10*20.
    3. write {tag}-tfr.h5 + per-channel thumbnails; write manifest.json.

CLI:
    python -m webui.dataprep.make_spectra --subject D0100 --task LexicalDecRepDelay
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback

import numpy as np

from webui.backend.paths import Paths
from webui.preproc import config


def _nanmean_avg(x):
    """Trial-averaging callable used by AverageTFR.average (matches refs)."""
    return np.nanmean(x, axis=0)


def _load_car_raw(paths: Paths, subject: str):
    """Load clean EDF, drop bad channels, load data, average-reference (CAR).

    Mirrors refs/batch_preproc.py L246-259.
    """
    from ieeg.io import get_data, raw_from_layout

    layout = get_data(paths.task, root=paths.lab_root)
    raw1 = raw_from_layout(
        layout.derivatives["derivatives/clean"],
        subject=subject,
        desc="clean",
        extension=".edf",
        preload=False,
    )
    # bads come from channels.tsv status=bad (outlier/muscle/...); CAR is
    # computed on the surviving good channels only, exactly like the pipeline.
    raw = raw1.copy().drop_channels(raw1.info["bads"])
    del raw1
    raw.load_data()
    ch_type = raw.get_channel_types(only_data_chs=True)[0]
    raw.set_eeg_reference(ref_channels="average", ch_type=ch_type)
    return raw


def _wavelet_for_event(raw, ev: config.EventSpec, decim: int):
    """Trial -> wavelet -> crop_pad for a single event window.

    Returns the per-trial scaleogram (before averaging) so the caller can crop
    the baseline from the Cue event.
    """
    from ieeg.navigate import trial_ieeg, outliers_to_nan
    from ieeg.timefreq.utils import crop_pad, wavelet_scaleogram

    t0, t1 = ev.window
    # epoch on the padded window then crop the pad back off (refs L292-300).
    times = (t0 - 0.5, t1 + 0.5)
    trials = trial_ieeg(raw, ev.epoch, times, preload=True)
    outliers_to_nan(trials, outliers=config.OUTLIER_SD)
    spectra = wavelet_scaleogram(trials, n_jobs=-1, decim=decim)
    crop_pad(spectra, config.CROP_PAD)
    return spectra


def _save_thumbnails(spectra, tag: str, thumbs_root: str) -> None:
    """One ~140x90 parula PNG per channel for the GUI grid (contract C)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ieeg.viz.parula import parula_map

    tag_dir = os.path.join(thumbs_root, tag)
    os.makedirs(tag_dir, exist_ok=True)
    data = spectra.data  # (n_chan, n_freq, n_time)
    vmin, vmax = config.WAVELET_VLIM
    for idx, ch in enumerate(spectra.ch_names):
        fig = plt.figure(figsize=(1.4, 0.9), dpi=100)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.imshow(
            data[idx],
            aspect="auto",
            origin="lower",
            cmap=parula_map,
            vmin=vmin,
            vmax=vmax,
        )
        ax.axis("off")
        fig.savefig(os.path.join(tag_dir, f"{ch}.png"))
        plt.close(fig)


def make_spectra(
    subject: str,
    paths: Paths,
    *,
    overwrite: bool = True,
    thumbnails: bool = True,
) -> dict:
    """Run the wavelet payload generation for one subject. Returns the manifest."""
    import mne

    events = config.events_for_task(paths.task)
    out_dir = paths.wavelet_dir(subject)
    os.makedirs(out_dir, exist_ok=True)
    thumbs_root = os.path.join(out_dir, "thumbs")

    print(f"[make_spectra] {subject} / {paths.task}: loading clean EDF + CAR ...", flush=True)
    raw = _load_car_raw(paths, subject)
    decim = int(raw.info["sfreq"] / config.WAVELET_DECIM_HZ)
    print(f"[make_spectra]   sfreq={raw.info['sfreq']} decim={decim} "
          f"n_good_chans={len(raw.ch_names)}", flush=True)

    base_wavelet = None
    written_tags: list[str] = []
    channels: list[str] = []
    failures: dict[str, str] = {}

    for ev in events:
        try:
            print(f"[make_spectra]   wavelet {ev.tag} ({ev.epoch}) ...", flush=True)
            spectra = _wavelet_for_event(raw, ev, decim)

            if ev.baseline:
                base = spectra.copy().crop(*config.BASELINE_WIN)
                base_wavelet = base.average(_nanmean_avg, copy=True)

            if base_wavelet is None:
                raise RuntimeError(
                    f"baseline not available before tag {ev.tag}; "
                    "the baseline event must run first"
                )

            from ieeg.calc.scaling import rescale

            spectra = spectra.average(_nanmean_avg, copy=True)
            spectra = rescale(spectra, base_wavelet, copy=True, mode="ratio")
            spectra._data = np.log10(spectra._data) * 20

            fname = os.path.join(out_dir, f"{ev.tag}-tfr.h5")
            mne.time_frequency.write_tfrs(fname, spectra, overwrite=overwrite)

            if thumbnails:
                _save_thumbnails(spectra, ev.tag, thumbs_root)

            if not channels:
                channels = list(spectra.ch_names)
            written_tags.append(ev.tag)
            del spectra
        except Exception as exc:  # noqa: BLE001 -- record and continue
            if ev.baseline:
                raise  # cannot proceed without the baseline
            failures[ev.tag] = f"{type(exc).__name__}: {exc}"
            print(f"[make_spectra]   !! tag {ev.tag} failed: {exc}", flush=True)
            traceback.print_exc()

    manifest = {
        "subject": subject,
        "task": paths.task,
        "tags": written_tags,
        "channels": channels,
        "vlim": list(config.WAVELET_VLIM),
        "cmap": config.CMAP,
        "has_recon": paths.has_recon(subject),
    }
    if failures:
        manifest["failed_tags"] = failures
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)

    print(f"[make_spectra] done: {out_dir} (tags={written_tags})", flush=True)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate wavelet payload (contract C) for one subject.")
    p.add_argument("--subject", required=True, help="BIDS subject id, e.g. D0100")
    p.add_argument("--task", default=None, help=f"task tag (default from env / {config.SUPPORTED_TASKS[0]})")
    p.add_argument("--lab-root", default=None, help="root containing BIDS-1.0_{TASK}/BIDS")
    p.add_argument("--save-dir", default=None, help="wavelet payload output root ({SAVE_DIR}/{SUBJ}/wavelet)")
    p.add_argument("--recon-dir", default=None, help="ECoG Recon root (for has_recon)")
    p.add_argument("--no-thumbs", action="store_true", help="skip per-channel thumbnail PNGs")
    p.add_argument("--no-overwrite", action="store_true", help="do not overwrite existing tfr.h5")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    paths = Paths.from_env(
        task=args.task,
        lab_root=args.lab_root,
        save_dir=args.save_dir,
        recon_dir=args.recon_dir,
    )
    make_spectra(
        args.subject,
        paths,
        overwrite=not args.no_overwrite,
        thumbnails=not args.no_thumbs,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
