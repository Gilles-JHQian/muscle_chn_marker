"""Central path / environment resolution shared by dataprep, export and backend.

All filesystem locations come from environment variables (with DCC defaults) so
the same code runs on a login node, a SLURM job, or a laptop tunnel. See the
README env table and ``plan_muscle_gui/PAYLOAD_SPEC.md`` for the contract paths.

    LAB_ROOT        root holding BIDS-1.0_{TASK}/BIDS
    MUSCLE_TASK     task tag (LexicalDecRepDelay / LexicalDecRepNoDelay)
    SAVE_DIR        wavelet + brain payload root ({SAVE_DIR}/{SUBJ}/...)
    RECON_DIR       ECoG Recon root (.../ECoG_Recon)
    MUSCLE_CSV_DIR  contract-B CSV output dir (default {COGANLAB_IEEG}/muscle_chans)
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from webui.preproc import config

DEFAULT_LAB_ROOT = "/cwork/jq81/cogan_lab_box/CoganLab"
DEFAULT_RECON_DIR = "/cwork/jq81/cogan_lab_box/ECoG_Recon"
DEFAULT_TASK = config.SUPPORTED_TASKS[0]

# repo root = .../muscle_chn_marker (two levels up from this file's package)
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))


def recon_subject(subject: str) -> str:
    """BIDS id -> ECoG Recon id: ``D0100`` -> ``D100`` (drop zero padding)."""
    digits = subject.lstrip("D")
    return f"D{int(digits)}"


@dataclass(frozen=True)
class Paths:
    lab_root: str
    task: str
    save_dir: str
    recon_dir: str
    muscle_csv_dir: str

    # --- construction --------------------------------------------------------
    @classmethod
    def from_env(
        cls,
        *,
        task: str | None = None,
        lab_root: str | None = None,
        save_dir: str | None = None,
        recon_dir: str | None = None,
        muscle_csv_dir: str | None = None,
    ) -> "Paths":
        task = task or os.environ.get("MUSCLE_TASK", DEFAULT_TASK)
        lab_root = lab_root or os.environ.get("LAB_ROOT", DEFAULT_LAB_ROOT)
        save_dir = (
            save_dir
            or os.environ.get("SAVE_DIR")
            or os.path.join(_REPO_ROOT, "data", "spectra")
        )
        recon_dir = recon_dir or os.environ.get("RECON_DIR", DEFAULT_RECON_DIR)
        # contract B default: {BIDS_ROOT}/coganlab_ieeg/muscle_chans
        if muscle_csv_dir is None:
            muscle_csv_dir = os.environ.get("MUSCLE_CSV_DIR")
        if muscle_csv_dir is None:
            bids_root = os.path.join(lab_root, f"BIDS-1.0_{task}", "BIDS")
            muscle_csv_dir = os.path.join(bids_root, "coganlab_ieeg", "muscle_chans")
        return cls(
            lab_root=lab_root,
            task=task,
            save_dir=save_dir,
            recon_dir=recon_dir,
            muscle_csv_dir=muscle_csv_dir,
        )

    # --- contract A (clean derivatives) --------------------------------------
    @property
    def bids_root(self) -> str:
        return os.path.join(self.lab_root, f"BIDS-1.0_{self.task}", "BIDS")

    def clean_ieeg_dir(self, subject: str) -> str:
        """Per-subject clean ieeg dir holding run channels.tsv / EDFs."""
        return os.path.join(
            self.bids_root, "derivatives", "clean", f"sub-{subject}", "ieeg"
        )

    # --- contract C (wavelet payload + brain assets) -------------------------
    # Payloads are namespaced by task: {SAVE_DIR}/{TASK}/{SUBJ}/... so several
    # tasks can coexist under one SAVE_DIR (the GUI switches between them).
    def task_dir(self) -> str:
        return os.path.join(self.save_dir, self.task)

    def subject_dir(self, subject: str) -> str:
        return os.path.join(self.task_dir(), subject)

    def wavelet_dir(self, subject: str) -> str:
        return os.path.join(self.subject_dir(subject), "wavelet")

    def manifest_path(self, subject: str) -> str:
        return os.path.join(self.wavelet_dir(subject), "manifest.json")

    def tfr_path(self, subject: str, tag: str) -> str:
        return os.path.join(self.wavelet_dir(subject), f"{tag}-tfr.h5")

    def thumb_path(self, subject: str, tag: str, channel: str) -> str:
        return os.path.join(self.wavelet_dir(subject), "thumbs", tag, f"{channel}.png")

    def brain_glb_path(self, subject: str) -> str:
        return os.path.join(self.subject_dir(subject), "brain.glb")

    def electrodes_path(self, subject: str) -> str:
        return os.path.join(self.subject_dir(subject), "electrodes.json")

    # --- contract B (muscle CSV) --------------------------------------------
    def muscle_csv_path(self, subject: str) -> str:
        return os.path.join(self.muscle_csv_dir, f"{subject}_muscle_chans.csv")

    # --- ECoG Recon ----------------------------------------------------------
    def recon_subject_dir(self, subject: str) -> str:
        return os.path.join(self.recon_dir, recon_subject(subject))

    def has_recon(self, subject: str) -> bool:
        surf = os.path.join(self.recon_subject_dir(subject), "surf")
        return os.path.isdir(surf) and (
            os.path.exists(os.path.join(surf, "lh.pial"))
            or os.path.exists(os.path.join(surf, "rh.pial"))
        )
