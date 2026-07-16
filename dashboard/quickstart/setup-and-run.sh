#!/usr/bin/env bash
#
# setup-and-run.sh — One script to set up and launch the SSL Certificate
# Analytics Dashboard on macOS / Linux.
#
# Usage:
#   ./setup-and-run.sh
#
# What it does (see README.md "Prerequisites" and "Preparing the dataset"
# sections for the full explanation of each step):
#   1. Checks python3, node, npm, mongod, mongorestore are installed
#   2. Makes sure MongoDB is actually running
#   3. Creates/activates a Python venv and installs backend requirements
#   4. Checks whether the required MongoDB databases already exist
#   5. If not, downloads the dataset from Hugging Face and restores it
#   6. Installs frontend dependencies
#   7. Starts backend (Django) and frontend (Next.js) together
#
# Press Ctrl+C at any time while both servers are running to stop them.

set -uo pipefail

# ----------------------------------------------------------------------
# Config — adjust these if your project layout / ports differ
# ----------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"   # dashboard/scripts -> dashboard -> project root
cd "$PROJECT_ROOT"

BACKEND_DIR="$PROJECT_ROOT/dashboard/backend"
FRONTEND_DIR="$PROJECT_ROOT/dashboard/frontend"
CONFIG_FILE="$PROJECT_ROOT/project-config.json"
DATASET_DIR="$PROJECT_ROOT/dataset"

BACKEND_PORT=8000
FRONTEND_PORT=3000

MAIN_ARCHIVE="hugging-face-700k.archive.gz"
RESULTS_ARCHIVE="hugging-face-700k-results.archive.gz"
HF_BASE_URL="https://huggingface.co/datasets/EbadJunaid/hugging-face-700k-ssl-certificates-data/resolve/main"

DEFAULT_MONGO_URI="mongodb://localhost:27017"
DEFAULT_MAIN_DB="hugging-face-700k"
DEFAULT_RESULTS_DB="hugging-face-700k-results"

BACKEND_PID=""
FRONTEND_PID=""

# ----------------------------------------------------------------------
# Pretty printing helpers
# ----------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}➜${NC} $1"; }
success() { echo -e "${GREEN}✔${NC} $1"; }
warn()    { echo -e "${YELLOW}⚠${NC} $1"; }
error()   { echo -e "${RED}✘${NC} $1"; }
phase()   { echo -e "\n${BOLD}== $1 ==${NC}"; }

# ----------------------------------------------------------------------
# OS detection — used only to print the right install command
# ----------------------------------------------------------------------
detect_os() {
    case "$OSTYPE" in
        linux-gnu*)
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                echo "$ID"
            else
                echo "linux-unknown"
            fi
            ;;
        darwin*) echo "macos" ;;
        *)       echo "unknown" ;;
    esac
}
OS_ID="$(detect_os)"

install_hint() {
    local tool="$1"
    case "$OS_ID" in
        ubuntu|debian)
            case "$tool" in
                python)  echo "sudo apt update && sudo apt install -y python3 python3-venv python3-pip" ;;
                node)    echo "curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - && sudo apt install -y nodejs" ;;
                mongodb) echo "See https://www.mongodb.com/docs/manual/administration/install-on-linux/ (apt repo setup required)" ;;
            esac ;;
        fedora|rhel|centos)
            case "$tool" in
                python)  echo "sudo dnf install -y python3 python3-pip" ;;
                node)    echo "sudo dnf install -y nodejs" ;;
                mongodb) echo "See https://www.mongodb.com/docs/manual/administration/install-on-red-hat/" ;;
            esac ;;
        arch)
            case "$tool" in
                python)  echo "sudo pacman -S python python-pip" ;;
                node)    echo "sudo pacman -S nodejs npm" ;;
                mongodb) echo "sudo pacman -S mongodb-bin   (or build from AUR)" ;;
            esac ;;
        macos)
            case "$tool" in
                python)  echo "brew install python3" ;;
                node)    echo "brew install node" ;;
                mongodb) echo "brew tap mongodb/brew && brew install mongodb-community mongodb-database-tools" ;;
            esac ;;
        *)
            case "$tool" in
                python)  echo "https://www.python.org/downloads/" ;;
                node)    echo "https://nodejs.org/" ;;
                mongodb) echo "https://www.mongodb.com/try/download/community  and  https://www.mongodb.com/try/download/database-tools" ;;
            esac ;;
    esac
}

# Check if a TCP port is open, without depending on nc/mongosh being installed.
# Uses bash's built-in /dev/tcp pseudo-device.
port_open() {
    local host="$1" port="$2"
    (exec 3<>"/dev/tcp/${host}/${port}") 2>/dev/null
    local result=$?
    exec 3>&- 2>/dev/null || true
    return $result
}

# ========================================================================
# PHASE 1 — Prerequisites
# ========================================================================
phase "Phase 1/7 — Checking prerequisites"

MISSING=0

if command -v python3 &>/dev/null; then
    success "python3 found ($(python3 --version 2>&1))"
else
    error "python3 not found."
    echo "   Install with: $(install_hint python)"
    MISSING=1
fi

if command -v node &>/dev/null && command -v npm &>/dev/null; then
    success "node + npm found (node $(node --version), npm $(npm --version))"
else
    error "node/npm not found."
    echo "   Install with: $(install_hint node)"
    MISSING=1
fi

if command -v mongod &>/dev/null; then
    success "mongod found ($(mongod --version | head -n1))"
else
    error "mongod not found."
    echo "   Install with: $(install_hint mongodb)"
    MISSING=1
fi

if command -v mongorestore &>/dev/null; then
    success "mongorestore found"
else
    error "mongorestore (MongoDB Database Tools) not found."
    echo "   Install with: $(install_hint mongodb)"
    MISSING=1
fi

# Redis is optional — never block on it, just try to help if it's easy to.
if command -v redis-cli &>/dev/null; then
    if redis-cli ping &>/dev/null; then
        success "Redis is running (optional caching enabled)"
    else
        warn "Redis is installed but not running. Attempting to start it..."
        if [ "$OS_ID" = "macos" ] && command -v brew &>/dev/null; then
            brew services start redis &>/dev/null || true
        elif command -v systemctl &>/dev/null; then
            sudo systemctl start redis &>/dev/null || sudo systemctl start redis-server &>/dev/null || true
        fi
        sleep 2
        if redis-cli ping &>/dev/null; then
            success "Redis started successfully (optional caching enabled)"
        else
            warn "Could not start Redis automatically — continuing without caching."
            echo "   Start it manually if you want caching, e.g.: brew services start redis"
        fi
    fi
else
    warn "Redis not installed — dashboard will run fine without it (no caching)."
fi

if [ "$MISSING" -eq 1 ]; then
    echo
    error "One or more required tools are missing. Install them and re-run this script."
    exit 1
fi

# Make sure MongoDB is actually running, not just installed.
if port_open "127.0.0.1" "27017"; then
    success "MongoDB is running on localhost:27017"
else
    warn "MongoDB does not appear to be running. Attempting to start it..."
    if [ "$OS_ID" = "macos" ] && command -v brew &>/dev/null; then
        brew services start mongodb-community &>/dev/null || true
    elif command -v systemctl &>/dev/null; then
        sudo systemctl start mongod &>/dev/null || true
    fi
    sleep 3
    if port_open "127.0.0.1" "27017"; then
        success "MongoDB started successfully."
    else
        error "Could not start MongoDB automatically."
        echo "   Start it manually, then re-run this script. Examples:"
        echo "     macOS:  brew services start mongodb-community"
        echo "     Linux:  sudo systemctl start mongod"
        exit 1
    fi
fi

# ========================================================================
# PHASE 2 — Python venv + backend dependencies
# ========================================================================
phase "Phase 2/7 — Setting up Python environment"

if [ ! -d "$BACKEND_DIR" ]; then
    error "Backend directory not found at: $BACKEND_DIR"
    echo "   Run this script from the project root."
    exit 1
fi

if [ ! -d "$PROJECT_ROOT/venv" ]; then
    info "Creating virtual environment..."
    python3 -m venv "$PROJECT_ROOT/venv"
else
    info "Virtual environment already exists, reusing it."
fi

# shellcheck disable=SC1091
source "$PROJECT_ROOT/venv/bin/activate"

info "Installing backend Python dependencies (this can take a minute)..."
pip install --quiet --upgrade pip
pip install --quiet -r "$BACKEND_DIR/requirements.txt"
success "Python dependencies installed."

# ========================================================================
# PHASE 3 — Check whether the MongoDB databases already exist
# ========================================================================
phase "Phase 3/7 — Checking dataset status in MongoDB"

DATASET_CHECK=$(python3 - "$CONFIG_FILE" "$DEFAULT_MONGO_URI" "$DEFAULT_MAIN_DB" "$DEFAULT_RESULTS_DB" <<'PYEOF'
import json, sys
from pymongo import MongoClient
from pymongo.errors import PyMongoError

config_path, default_uri, default_main, default_results = sys.argv[1:5]

# Which "databases" entry to use — matches the dataset this script downloads.
DATASET_ID = "hugging-face-700k"

uri, main_db, results_db = default_uri, default_main, default_results
try:
    with open(config_path) as f:
        cfg = json.load(f)

    uri = cfg.get("mongo_uri", uri)

    entry = None
    for candidate in cfg.get("databases", []):
        if candidate.get("id") == DATASET_ID:
            entry = candidate
            break
    if entry is None and cfg.get("databases"):
        # Fall back to the first entry if no exact id match is found.
        entry = cfg["databases"][0]

    if entry:
        main_db = entry.get("main", main_db)
        results_db = entry.get("results", results_db)
except FileNotFoundError:
    pass
except Exception:
    pass

missing = []
try:
    client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    existing = client.list_database_names()
    if main_db not in existing:
        missing.append("main")
    if results_db not in existing:
        missing.append("results")
except PyMongoError:
    missing.append("main")
    missing.append("results")

if missing:
    print(",".join(missing))
else:
    print("READY")
PYEOF
)

NEED_MAIN=false
NEED_RESULTS=false

if [ "$DATASET_CHECK" = "READY" ]; then
    success "Both required databases already exist — skipping dataset download."
else
    warn "Some datasets not found in MongoDB."
    [[ "$DATASET_CHECK" == *"main"* ]]   && NEED_MAIN=true
    [[ "$DATASET_CHECK" == *"results"* ]] && NEED_RESULTS=true
    [ "$NEED_MAIN" = true ]    && info "Main database ($DEFAULT_MAIN_DB) missing."
    [ "$NEED_RESULTS" = true ] && info "Analytics database ($DEFAULT_RESULTS_DB) missing."

    # ====================================================================
    # PHASE 4 — Download dataset + mongorestore
    # ====================================================================
    phase "Phase 4/7 — Downloading and restoring dataset"

    mkdir -p "$DATASET_DIR"
    cd "$DATASET_DIR"

    human_size() {
        awk -v b="$1" 'BEGIN{
            split("B KB MB GB TB", u, " ")
            s=1; while (b >= 1024 && s < 5) { b /= 1024; s++ }
            printf "%.1f%s", b, u[s]
        }'
    }

    download() {
        local url="$1" out="$2"
        if [ -f "$out" ]; then
            info "$out already downloaded, skipping."
            return
        fi
        info "Downloading $out ..."

        # Best-effort total size — some CDNs omit Content-Length, so this can
        # come back empty, and that's handled below.
        local total
        total=$(curl -sIL "$url" 2>/dev/null | grep -i '^content-length:' | tail -1 | tr -d '\r' | awk '{print $2}')

        curl -sL -o "$out" "$url" &
        local pid=$!

        while kill -0 "$pid" 2>/dev/null; do
            if [ -f "$out" ]; then
                local current
                current=$(stat -f%z "$out" 2>/dev/null || stat -c%s "$out" 2>/dev/null || echo 0)
                if [ -n "$total" ] && [ "$total" -gt 0 ] 2>/dev/null; then
                    local pct=$(( current * 100 / total ))
                    printf "\r    %s / %s  (%d%%)   " "$(human_size "$current")" "$(human_size "$total")" "$pct"
                else
                    printf "\r    %s downloaded...   " "$(human_size "$current")"
                fi
            fi
            sleep 1
        done

        wait "$pid"
        local status=$?
        echo
        if [ $status -ne 0 ] || [ ! -f "$out" ]; then
            error "Download of $out failed."
            exit 1
        fi
        success "$out downloaded ($(human_size "$(stat -f%z "$out" 2>/dev/null || stat -c%s "$out")"))."
    }

    if [ "$NEED_MAIN" = true ]; then
        download "$HF_BASE_URL/$MAIN_ARCHIVE" "$MAIN_ARCHIVE"
        info "Restoring main certificate database..."
        mongorestore --archive="$MAIN_ARCHIVE" --gzip
        success "Main dataset restored."
    else
        info "Main database already exists — skipping."
    fi

    if [ "$NEED_RESULTS" = true ]; then
        download "$HF_BASE_URL/$RESULTS_ARCHIVE" "$RESULTS_ARCHIVE"
        info "Restoring pre-computed analytics database..."
        mongorestore --archive="$RESULTS_ARCHIVE" --gzip
        success "Analytics dataset restored."
    else
        info "Analytics database already exists — skipping."
    fi

    if [ "$NEED_MAIN" = true ] || [ "$NEED_RESULTS" = true ]; then
        read -p "Delete downloaded archive files to save disk space? [Y/n] " -r REPLY
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            [ "$NEED_MAIN" = true ]    && rm -f "$MAIN_ARCHIVE"
            [ "$NEED_RESULTS" = true ] && rm -f "$RESULTS_ARCHIVE"
            success "Archive files deleted."
        else
            info "Archive files kept in $DATASET_DIR"
        fi
    fi

    cd "$PROJECT_ROOT"
fi

# ========================================================================
# PHASE 5 — Frontend dependencies
# ========================================================================
phase "Phase 5/7 — Installing frontend dependencies"

if [ ! -d "$FRONTEND_DIR" ]; then
    error "Frontend directory not found at: $FRONTEND_DIR"
    exit 1
fi

cd "$FRONTEND_DIR"
if [ -d "node_modules" ]; then
    info "node_modules already present, skipping npm install."
else
    npm install
fi
success "Frontend dependencies ready."
cd "$PROJECT_ROOT"

# ========================================================================
# PHASE 6 — Start both servers
# ========================================================================
phase "Phase 6/7 — Starting servers"

if port_open "127.0.0.1" "$BACKEND_PORT"; then
    error "Port $BACKEND_PORT is already in use — backend can't start."
    echo "   Either free the port, or run the backend on another port manually:"
    echo "     1. cd dashboard/backend && python3 manage.py runserver 8001"
    echo "     2. Set NEXT_PUBLIC_API_URL=http://localhost:8001/api in frontend/.env.local"
    echo "     3. Add http://localhost:8001 to CORS_ALLOWED_ORIGINS in backend/ssl_dashboard/settings.py"
    exit 1
fi

if port_open "127.0.0.1" "$FRONTEND_PORT"; then
    error "Port $FRONTEND_PORT is already in use — frontend can't start."
    echo "   Either free the port, or run the frontend on another port manually:"
    echo "     1. cd dashboard/frontend && npm run dev -- -p 3001"
    echo "     2. Add http://localhost:3001 to CORS_ALLOWED_ORIGINS in backend/ssl_dashboard/settings.py"
    exit 1
fi

cleanup() {
    echo
    info "Shutting down servers..."
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
    wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
    success "Both servers stopped. Bye!"
}
trap cleanup EXIT INT TERM

cd "$BACKEND_DIR"
info "Applying Django migrations..."
python3 manage.py migrate --noinput

info "Starting backend on port $BACKEND_PORT..."
python3 manage.py runserver "$BACKEND_PORT" &
BACKEND_PID=$!

cd "$FRONTEND_DIR"
info "Starting frontend on port $FRONTEND_PORT..."
npm run dev -- -p "$FRONTEND_PORT" &
FRONTEND_PID=$!

cd "$PROJECT_ROOT"

# ========================================================================
# PHASE 7 — Done
# ========================================================================
sleep 2
phase "Phase 7/7 — Dashboard is running"
echo -e "  Backend:   ${GREEN}http://localhost:${BACKEND_PORT}${NC}"
echo -e "  Frontend:  ${GREEN}http://localhost:${FRONTEND_PORT}${NC}"
echo
echo "  Press Ctrl+C to stop both servers."
echo

wait