#!/usr/bin/env bash
#SBATCH --job-name=muscle_spectra
#SBATCH --output=logs/muscle_spectra_%A_%a.out
#SBATCH --error=logs/muscle_spectra_%A_%a.err
#SBATCH --partition=common
#SBATCH --time=08:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --nodes=1
#SBATCH --ntasks=1
# Submit a subject range as an array, e.g.:
#   sbatch --array=100,121,128,133,134 sbatch/sbatch_spectra.sh
#   sbatch --array=23-143 sbatch/sbatch_spectra.sh
# Each array index N maps to subject D{N:04} (100 -> D0100).
set -eo pipefail

REPO_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$REPO_DIR"
mkdir -p logs

CONDA_ENV="${CONDA_ENV:-Lexical_NoDelay}"
export MUSCLE_TASK="${MUSCLE_TASK:-LexicalDecRepNoDelay}"
export LAB_ROOT="${LAB_ROOT:-/cwork/jq81/cogan_lab_box/CoganLab}"
export RECON_DIR="${RECON_DIR:-/cwork/jq81/cogan_lab_box/ECoG_Recon}"
export SAVE_DIR="${SAVE_DIR:-$REPO_DIR/data/spectra}"

# shellcheck disable=SC1091
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$CONDA_ENV"

SUBJ="$(printf 'D%04d' "${SLURM_ARRAY_TASK_ID:?set --array}")"
echo "=== muscle spectra: $SUBJ / $MUSCLE_TASK (SAVE_DIR=$SAVE_DIR) ==="

# Heavy: clean -> CAR -> wavelet -> tfr.h5 + thumbs + manifest (contract C).
python -m webui.dataprep.make_spectra --subject "$SUBJ" --task "$MUSCLE_TASK"

# Brain assets (fast); only subjects with an ECoG Recon produce output.
python -m webui.export.export_subject_brain --subject "$SUBJ" \
  || echo "[sbatch] no recon for $SUBJ — brain panel will be degraded (spectra OK)."

echo "=== done: $SUBJ ==="
