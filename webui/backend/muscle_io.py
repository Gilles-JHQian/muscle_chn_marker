"""Contract-B muscle marking I/O: CSV + clean channels.tsv writeback.

The writeback logic is vendored from ``refs/utils_batch.py`` (``update_muscle_chs``
= ``coganlab_ieeg/utils/batch.py``) so the tool does not depend on that repo being
importable. It is **idempotent**: re-running with the same channels does not
re-pollute the tsv.

* CSV (contract B): one channel name per line, no header. Empty -> single ``nan``
  line (the ``data/eeg_chans`` convention).
* channels.tsv writeback: for every run's ``*_desc-clean_channels.tsv`` set
  ``status=bad, status_description=muscle`` on each listed channel.
"""

from __future__ import annotations

import os
import re


def read_muscle_csv(csv_path: str) -> list[str]:
    """Return the marked channel names from the CSV (``[]`` if missing / ``nan``)."""
    if not os.path.exists(csv_path):
        return []
    channels: list[str] = []
    with open(csv_path) as fh:
        for line in fh:
            name = line.strip()
            if not name or name.lower() == "nan":
                continue
            channels.append(name)
    return channels


def write_muscle_csv(csv_path: str, channels) -> list[str]:
    """Write the contract-B CSV. Dedups + sorts; empty -> single ``nan`` line."""
    cleaned = sorted({c.strip() for c in channels if c and c.strip()})
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w") as fh:
        if cleaned:
            fh.write("\n".join(cleaned) + "\n")
        else:
            fh.write("nan\n")
    return cleaned


def update_channels_tsv(subject: str, clean_ieeg_dir: str, task: str, channels) -> list[str]:
    """Set status=bad / status_description=muscle for ``channels`` in every run tsv.

    Mirrors refs/utils_batch.update_muscle_chs but takes the channel list and dirs
    explicitly (no cwd-relative ``data/muscle_chans`` lookup). Returns the list of
    run filenames touched. Idempotent.
    """
    import pandas as pd

    task_nosep = task.replace("_", "")
    pattern = (
        rf"sub-{re.escape(subject)}_task-{re.escape(task_nosep)}"
        r"_acq-.+?_run-.+?_desc-clean_channels\.tsv"
    )
    if not os.path.isdir(clean_ieeg_dir):
        raise FileNotFoundError(f"clean ieeg dir not found: {clean_ieeg_dir}")
    files = [f for f in os.listdir(clean_ieeg_dir) if re.match(pattern, f)]
    if not files:
        raise FileNotFoundError(
            f"No clean channels.tsv matching {pattern!r} in {clean_ieeg_dir}"
        )

    channels = [c for c in channels if c]
    for fname in files:
        fpath = os.path.join(clean_ieeg_dir, fname)
        data = pd.read_csv(fpath, sep="\t")
        # An all-good run has an empty (float64/NaN) status_description column;
        # cast to object so assigning the string "muscle" doesn't warn/raise.
        for col in ("status", "status_description"):
            if col in data.columns:
                data[col] = data[col].astype("object")
        for ch in channels:
            if ch in data["name"].values:
                idx = data[data["name"] == ch].index[0]
                if data.at[idx, "status"] != "bad" or data.at[idx, "status_description"] != "muscle":
                    data.at[idx, "status"] = "bad"
                    data.at[idx, "status_description"] = "muscle"
        data.to_csv(fpath, sep="\t", index=False)
    return files


def save_muscle_marks(
    subject: str,
    channels,
    *,
    csv_path: str,
    clean_ieeg_dir: str,
    task: str,
    writeback_tsv: bool = True,
) -> dict:
    """Persist marks: write contract-B CSV and (optionally) update channels.tsv."""
    cleaned = write_muscle_csv(csv_path, channels)
    touched: list[str] = []
    if writeback_tsv and cleaned:
        touched = update_channels_tsv(subject, clean_ieeg_dir, task, cleaned)
    return {"subject": subject, "channels": cleaned, "runs_updated": touched}
