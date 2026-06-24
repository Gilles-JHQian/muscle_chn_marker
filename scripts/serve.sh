#!/usr/bin/env bash
# Single-port production serve: build frontend if needed, then uvicorn serves
# both the built dist/ and the /api endpoints on one port (default 8082).
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$REPO_DIR/frontend"
DIST_DIR="$FRONTEND_DIR/dist"

PORT="${PORT:-8082}"
CONDA_ENV="${CONDA_ENV:-Lexical_NoDelay}"

export LAB_ROOT="${LAB_ROOT:-/cwork/jq81/cogan_lab_box/CoganLab}"
export RECON_DIR="${RECON_DIR:-/cwork/jq81/cogan_lab_box/ECoG_Recon}"
export SAVE_DIR="${SAVE_DIR:-$REPO_DIR/data/spectra}"
export MUSCLE_TASK="${MUSCLE_TASK:-LexicalDecRepDelay}"

# --- python (conda) ---------------------------------------------------------
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

# --- build frontend if dist missing ----------------------------------------
if [ ! -f "$DIST_DIR/index.html" ]; then
  echo "dist/ missing — building frontend…"
  NODE_BIN="${NODE_BIN:-/opt/apps/rhel8/node-v18.14.2-linux-x64/bin}"
  [ -x "$NODE_BIN/node" ] && export PATH="$NODE_BIN:$PATH"
  command -v module >/dev/null 2>&1 && module load Node.js/18.14.2 2>/dev/null || true
  command -v npm >/dev/null 2>&1 || { echo "ERROR: node/npm not found (set NODE_BIN)"; exit 1; }
  (cd "$FRONTEND_DIR" && { [ -d node_modules ] || npm ci; } && npm run build)
fi
[ -f "$DIST_DIR/index.html" ] || { echo "ERROR: $DIST_DIR/index.html missing after build"; exit 1; }

NODE="$(hostname -s)"
cat <<EOF
──────────────────────────────────────────────────────────────
 Muscle marker SERVE (single port)
   URL  : http://localhost:$PORT/
   Node : $NODE     Task: $MUSCLE_TASK     SAVE_DIR=$SAVE_DIR

 From your laptop:
   ssh -L $PORT:$NODE:$PORT jq81@dcc-login.oit.duke.edu
 then open http://localhost:$PORT/
──────────────────────────────────────────────────────────────
EOF

cd "$REPO_DIR"
exec python -m uvicorn webui.backend.app:app --host 0.0.0.0 --port "$PORT"
