"""Export a subject's pial surface + electrodes for the 3D brain panel.

Produces the contract-C brain assets in ``{SAVE_DIR}/{SUBJ}/``:

    brain.glb        merged lh+rh pial mesh, surfaceRAS (tkrRAS) frame
    electrodes.json  [{channel, x, y, z, hemi}] in the same surfaceRAS frame

Coordinate alignment (the crux, see plan_muscle_gui/PLAN.md):
  * ``mne.read_surface(lh/rh.pial)`` is in **surfaceRAS / tkrRAS**.
  * ``D{N}_elec_locations_RAS_brainshifted.txt`` is in **scanner RAS (mm)**.
  * The two differ by a pure translation ``c_ras``, read from ``orig.mgz``:
        c_ras = (vox2ras @ inv(vox2ras_tkr))[:3, 3]
  * ``elec_surf = elec_scanner - c_ras`` lands the electrodes in the mesh frame,
    so three.js can render both directly with no further transform.

We use the ``_brainshifted`` file (same one ``ieeg.viz.mri.plot_subj`` uses --
touch contacts snapped toward the surface). Channel name = ``NAME + IDX``
(``LTMM`` + ``15`` -> ``LTMM15``), matching the clean EDF channel names.

CLI:
    python -m webui.export.export_subject_brain --subject D0100
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

from webui.backend.paths import Paths, recon_subject
from webui.export import glb


def compute_c_ras(recon_subject_dir: str) -> np.ndarray:
    """c_ras translation (scannerRAS - surfaceRAS) from the subject's MRI header.

    Tries orig.mgz, then T1.mgz / brainmask.mgz as fallbacks.
    """
    import nibabel as nib

    mri_dir = os.path.join(recon_subject_dir, "mri")
    for name in ("orig.mgz", "T1.mgz", "brainmask.mgz"):
        path = os.path.join(mri_dir, name)
        if os.path.exists(path):
            mgz = nib.load(path)
            vox2ras = mgz.header.get_vox2ras()
            vox2ras_tkr = mgz.header.get_vox2ras_tkr()
            return (vox2ras @ np.linalg.inv(vox2ras_tkr))[:3, 3]
    raise FileNotFoundError(f"No orig/T1/brainmask .mgz found under {mri_dir}")


def read_pial(recon_subject_dir: str):
    """Merge lh.pial + rh.pial into one (vertices, faces) mesh (surfaceRAS mm)."""
    import mne

    surf_dir = os.path.join(recon_subject_dir, "surf")
    parts = []
    for hemi in ("lh", "rh"):
        path = os.path.join(surf_dir, f"{hemi}.pial")
        if os.path.exists(path):
            coords, tris = mne.read_surface(path)
            parts.append((np.asarray(coords, dtype=np.float64), np.asarray(tris, dtype=np.int64)))
    if not parts:
        raise FileNotFoundError(f"No lh.pial / rh.pial under {surf_dir}")
    return glb.merge_meshes(parts)


def read_brainshifted_electrodes(recon_subject_dir: str, recon_id: str):
    """Parse ``{recon_id}_elec_locations_RAS_brainshifted.txt`` (scanner RAS mm).

    Each line: ``NAME IDX x y z HEMI [TYPE]``. Returns a list of
    ``(channel, np.array([x, y, z]), hemi)``.
    """
    path = os.path.join(
        recon_subject_dir, "elec_recon", f"{recon_id}_elec_locations_RAS_brainshifted.txt"
    )
    if not os.path.exists(path):
        raise FileNotFoundError(f"brainshifted electrode file not found: {path}")

    electrodes = []
    with open(path) as fh:
        for line in fh:
            parts = line.split()
            if len(parts) < 5:
                continue
            name, idx, x, y, z = parts[0], parts[1], parts[2], parts[3], parts[4]
            try:
                coord = np.array([float(x), float(y), float(z)], dtype=np.float64)
            except ValueError:
                continue  # header / non-data line
            channel = f"{name}{idx}"
            hemi = parts[5].upper() if len(parts) >= 6 and parts[5].upper() in ("L", "R") \
                else ("L" if coord[0] < 0 else "R")
            electrodes.append((channel, coord, hemi))
    if not electrodes:
        raise ValueError(f"No electrode rows parsed from {path}")
    return electrodes


def export_subject_brain(subject: str, paths: Paths) -> dict:
    """Write brain.glb + electrodes.json for one subject. Returns a small summary."""
    recon_dir = paths.recon_subject_dir(subject)
    recon_id = recon_subject(subject)
    if not os.path.isdir(recon_dir):
        raise FileNotFoundError(
            f"No ECoG Recon for {subject} ({recon_id}) at {recon_dir}; "
            "brain panel will be degraded -- spectra marking still works."
        )

    out_dir = paths.subject_dir(subject)
    os.makedirs(out_dir, exist_ok=True)

    # --- mesh ---------------------------------------------------------------
    print(f"[export_brain] {subject} ({recon_id}): reading pial surfaces ...", flush=True)
    vertices, faces = read_pial(recon_dir)
    glb_info = glb.write_glb(paths.brain_glb_path(subject), vertices, faces)
    print(f"[export_brain]   brain.glb: {glb_info['n_vertices']} verts / "
          f"{glb_info['n_faces']} faces", flush=True)

    # --- electrodes (scannerRAS - c_ras -> surfaceRAS) ----------------------
    c_ras = compute_c_ras(recon_dir)
    print(f"[export_brain]   c_ras = {c_ras.round(3).tolist()} mm", flush=True)
    raw_elecs = read_brainshifted_electrodes(recon_dir, recon_id)
    electrodes = []
    for channel, scanner_xyz, hemi in raw_elecs:
        surf = scanner_xyz - c_ras
        electrodes.append({
            "channel": channel,
            "x": float(surf[0]),
            "y": float(surf[1]),
            "z": float(surf[2]),
            "hemi": hemi,
        })
    with open(paths.electrodes_path(subject), "w") as fh:
        json.dump(electrodes, fh)
    print(f"[export_brain]   electrodes.json: {len(electrodes)} contacts", flush=True)

    return {
        "subject": subject,
        "recon_id": recon_id,
        "glb": glb_info,
        "n_electrodes": len(electrodes),
        "c_ras": c_ras.tolist(),
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Export pial brain.glb + electrodes.json for one subject.")
    p.add_argument("--subject", required=True, help="BIDS subject id, e.g. D0100")
    p.add_argument("--task", default=None, help="task tag (only affects default paths)")
    p.add_argument("--save-dir", default=None, help="payload output root ({SAVE_DIR}/{SUBJ})")
    p.add_argument("--recon-dir", default=None, help="ECoG Recon root")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    paths = Paths.from_env(task=args.task, save_dir=args.save_dir, recon_dir=args.recon_dir)
    summary = export_subject_brain(args.subject, paths)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
