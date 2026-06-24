"""Read wavelet ``{tag}-tfr.h5`` and slice a single channel for the GUI.

The AverageTFR (n_chan, n_freq, n_time) is loaded once per (subject, tag) and
held in a small LRU cache (the GUI hits the same h5 repeatedly while the user
clicks through channels). Slicing returns the JSON the frontend plots:

    {"freqs": [...], "times": [...], "data": [[...]], "vlim": [-2, 2], "channel": ...}
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from webui.preproc import config


class _LoadedTFR:
    """Lightweight container so the cache holds plain arrays, not MNE objects."""

    __slots__ = ("freqs", "times", "ch_names", "ch_index", "data")

    def __init__(self, tfr):
        self.freqs = np.asarray(tfr.freqs, dtype=float)
        self.times = np.asarray(tfr.times, dtype=float)
        self.ch_names = list(tfr.ch_names)
        self.ch_index = {name: i for i, name in enumerate(self.ch_names)}
        self.data = np.asarray(tfr.data, dtype=float)  # (n_chan, n_freq, n_time)


@lru_cache(maxsize=16)
def _load_tfr(h5_path: str) -> _LoadedTFR:
    import mne

    tfrs = mne.time_frequency.read_tfrs(h5_path)
    tfr = tfrs[0] if isinstance(tfrs, (list, tuple)) else tfrs
    return _LoadedTFR(tfr)


def clear_cache() -> None:
    _load_tfr.cache_clear()


def channel_names(h5_path: str) -> list[str]:
    return list(_load_tfr(h5_path).ch_names)


def slice_channel(h5_path: str, channel: str, vlim=config.WAVELET_VLIM) -> dict:
    """Return the spectrogram of one channel as JSON-able dict.

    NaNs (padded / outlier-masked bins) are converted to ``None`` so the payload
    is valid JSON and plotly renders them as gaps.
    """
    tfr = _load_tfr(h5_path)
    if channel not in tfr.ch_index:
        raise KeyError(f"channel {channel!r} not in {h5_path}")
    matrix = tfr.data[tfr.ch_index[channel]]  # (n_freq, n_time)
    data = [[None if not np.isfinite(v) else float(v) for v in row] for row in matrix]
    return {
        "channel": channel,
        "freqs": tfr.freqs.tolist(),
        "times": tfr.times.tolist(),
        "data": data,
        "vlim": list(vlim),
    }
