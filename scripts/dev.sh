#!/usr/bin/env bash
# Two-process dev: FastAPI (uvicorn --reload :8001) + Vite (:5173, proxies /api).
# Open an SSH tunnel to the Vite port from your laptop, then browse it.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$REPO_DIR/frontend"

API_PORT="${API_PORT:-8001}"
WEB_PORT="${PORT:-5173}"
CONDA_ENV="${CONDA_ENV:-Lexical_NoDelay}"

# --- data/env defaults (override by exporting before running) ----------------
export LAB_ROOT="${LAB_ROOT:-/cwork/jq81/cogan_lab_box/CoganLab}"
export RECON_DIR="${RECON_DIR:-/cwork/jq81/cogan_lab_box/ECoG_Recon}"
export SAVE_DIR="${SAVE_DIR:-$REPO_DIR/data/spectra}"
export MUSCLE_TASK="${MUSCLE_TASK:-LexicalDecRepDelay}"

# --- node on PATH -----------------------------------------------------------
NODE_BIN="${NODE_BIN:-/opt/apps/rhel8/node-v18.14.2-linux-x64/bin}"
if [ -x "$NODE_BIN/node" ]; then
  export PATH="$NODE_BIN:$PATH"
elif command -v module >/dev/null 2>&1; then
  module load Node.js/18.14.2 || true
fi
command -v npm >/dev/null 2>&1 || { echo "ERROR: node/npm not found (set NODE_BIN)"; exit 1; }

# --- python (conda) for uvicorn --------------------------------------------
if command -v conda >/dev/null 2>&1; then
  # shellcheck disable=SC1091
  source "$(conda info --base)/etc/profile.d/conda.sh"
  conda activate "$CONDA_ENV"
fi
python -c "import uvicorn, fastapi" 2>/dev/null || {
  echo "ERROR: fastapi/uvicorn missing in env '$CONDA_ENV'."
  echo "  conda run -n $CONDA_ENV pip install fastapi 'uvicorn[standard]'"
  exit 1
}

# --- frontend deps ----------------------------------------------------------
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "Installing frontend deps (first run)…"
  (cd "$FRONTEND_DIR" && npm ci)
fi

HOST="$(hostname -f 2>/dev/null || hostname)"
cat <<EOF
──────────────────────────────────────────────────────────────
 Muscle marker DEV
   API   : http://localhost:$API_PORT  (uvicorn --reload)
   Web   : http://localhost:$WEB_PORT  (vite, proxies /api -> :$API_PORT)
   Task  : $MUSCLE_TASK    SAVE_DIR=$SAVE_DIR

 From your laptop:
   ssh -N -L $WEB_PORT:$HOST:$WEB_PORT <you>@dcc-login.oit.duke.edu
 then open http://localhost:$WEB_PORT/
──────────────────────────────────────────────────────────────
EOF

# --- launch both; clean up the backend on exit ------------------------------
cd "$REPO_DIR"
python -m uvicorn webui.backend.app:app --reload --host 0.0.0.0 --port "$API_PORT" &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT INT TERM

cd "$FRONTEND_DIR"
exec npm run dev -- --port "$WEB_PORT" --strictPort
