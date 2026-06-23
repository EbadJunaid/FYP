#!/usr/bin/env python3
"""
main.py — pipeline orchestrator

Implements, in order, the 7 steps from the "Main file" box in the
architecture diagram:

  1. Check Go server is running -> if yes, kill it
  2. Check global-dataset.csv exists -> if no, run data-creator.py
  3. Run data-renew.py
  4. Check data-renew.csv exists:
       - yes -> launch run-crawler.py as a separate (background) process
       - check if new-data.py is currently running:
            yes -> delete the go-server DB
            no  -> launch new-data.py as a separate (background) process
  5. Run renew-data-merge.py
  6. Delete data-renew.csv
  7. Run "Generic"

NOTE: the Master-file / "is main already running" guard is intentionally
NOT implemented here — you said that's handled outside this script.

----------------------------------------------------------------------
ASSUMPTIONS — please review the CONFIG block and the two stub functions
near the bottom (kill_go_server / delete_go_server_db / step_7_run_generic)
----------------------------------------------------------------------
- All sibling scripts live next to this file and are invoked with the
  same interpreter running main.py, with no CLI arguments.
- run-crawler.py / new-data.py are launched fully detached (fire-and-
  forget): main.py does not wait for them, it just records their PID
  and moves on to step 5.
- "Is new-data.py running?" can only be answered by checking a PID file,
  since each cron tick spawns a brand-new main.py process with no memory
  of the last run. main.py writes new-data.py's PID to .pids/new-data.pid
  when it launches it, and on every run checks whether that PID is still
  alive AND still actually a new-data.py process (to avoid false
  positives from PID re-use).
- "Go server" is treated as an independent, already-running OS process
  (e.g. a compiled Go binary) that main.py detects by matching its name/
  command line against GO_SERVER_MATCH, and kills with SIGTERM (SIGKILL
  if it won't die).

Requires: pip install psutil
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional
from unittest import result
from pymongo import MongoClient
from datetime import datetime

import signal

try:
    import psutil
except ImportError:
    print(
        "This script requires the 'psutil' package.\n"
        "Install it with: pip install psutil",
        file=sys.stderr,
    )
    sys.exit(1)

# ============================================================================
# CONFIG — adjust to match your actual setup
# ============================================================================

run_ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


BASE_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable  # interpreter used to launch every child script

SCRIPTS = {
    "fetch_domains_names": BASE_DIR / "fetch-domains-names.py",
    "data_renew":       BASE_DIR / "data-renew.py",
    "crawler":      BASE_DIR / "../ssl-certificates-crawler/domain-based-crawler/src/crawler-args.py",
    "data_renew_merge": BASE_DIR / "data-renew-merge.py",
    "new_data":         BASE_DIR / "new-data.py",
    "generic":          BASE_DIR / "../dashboard/backend/mongo-indexes-pre-compute-scripts/generic/run-generic.py",
    "go_server": BASE_DIR / "go-server.py",
}

GLOBAL_DATASET_CSV = BASE_DIR / "global-dataset.csv"
DATA_RENEW_CSV = BASE_DIR / "data-renew.csv"
NEW_DATA_CSV = BASE_DIR / "new-data.csv"

# MongoDB settings for Step 4
MONGO_URI = "mongodb://localhost:27017"

# How we recognise the Go server process (matched against process name
# AND full command line, so a path containing this string also matches).
GO_SERVER_MATCH = "go-server"
GO_SERVER_DB_NAME = "new-data"

# Where we remember new-data.py's PID between separate runs of main.py.
PID_DIR = BASE_DIR / ".pids"
NEW_DATA_PID_FILE = PID_DIR / "new-data.pid"

LOG_DIR = BASE_DIR / "logs"

# ============================================================================
# Logging
# ============================================================================


def setup_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_DIR / f"main_{run_ts}.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )


log = logging.getLogger("pipeline")

# ============================================================================
# Helpers — running child scripts
# ============================================================================


def run_script(key: str, cli_args: list[str] = None) -> None:
    """Run a script synchronously and block until it finishes. Raises on failure."""
    path = SCRIPTS[key]
    log.info("Running %s ...", path.name)
    
    cmd = [PYTHON, str(path)]
    if cli_args:
        cmd.extend(cli_args)
        
    result = subprocess.run(cmd, cwd=BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.stdout:
        for line in result.stdout.splitlines():
            log.info("[%s] %s", path.name, line)
    if result.returncode != 0:
        raise RuntimeError(f"{path.name} exited with code {result.returncode}")
    log.info("%s finished OK.", path.name)


def launch_background(key: str, cli_args: list[str] = None, pid_file: Optional[Path] = None) -> subprocess.Popen:
    """Start a script as a detached background process with optional CLI args."""
    path = SCRIPTS[key]
    log.info("Launching %s as a background process ...", path.name)

    cmd = [PYTHON, str(path)]
    if cli_args:
        cmd.extend(cli_args)

    out_log_path = LOG_DIR / f"{key}_{run_ts}.out.log"
    out_log = open(out_log_path, "a")
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=BASE_DIR,
            stdin=subprocess.DEVNULL,  # <-- THE FIX: Severs the input tether to main.py
            stdout=out_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,    # Creates a new isolated OS session
        )
    finally:
        out_log.close()  # child keeps its own duplicated fd

    if pid_file is not None:
        pid_file.parent.mkdir(exist_ok=True)
        pid_file.write_text(str(proc.pid))

    log.info("%s started (PID %s), logging to %s", path.name, proc.pid, out_log_path.name)
    return proc

# ============================================================================
# Helpers — cross-run process state checks
# ============================================================================


def is_pid_file_process_alive(pid_file: Path, name_hint: str) -> bool:
    """True if the PID stored in pid_file is alive AND still looks like the right script."""
    if not pid_file.exists():
        return False

    try:
        pid = int(pid_file.read_text().strip())
    except ValueError:
        pid_file.unlink(missing_ok=True)
        return False

    if not psutil.pid_exists(pid):
        pid_file.unlink(missing_ok=True)
        return False

    try:
        cmdline = " ".join(psutil.Process(pid).cmdline())
    except psutil.NoSuchProcess:
        pid_file.unlink(missing_ok=True)
        return False

    if name_hint not in cmdline:
        # PID got reused by an unrelated process since we last recorded it.
        pid_file.unlink(missing_ok=True)
        return False

    return True


def find_go_server_process() -> Optional["psutil.Process"]:
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = " ".join(proc.info["cmdline"] or [])
            if GO_SERVER_MATCH in (proc.info["name"] or "") or GO_SERVER_MATCH in cmdline:
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def kill_go_server() -> None:
    proc = find_go_server_process()
    if proc is None:
        log.info("Go server is not running.")
        return

    log.info("Go server is running (PID %s) — requesting graceful shutdown...", proc.pid)
    try:
        # 1. Send the graceful signal
        # Unix/Linux/macOS: SIGINT (Ctrl+C) is standard for Go's os.Interrupt
        # Windows: proc.terminate() is the safest fallback, as Windows signal handling is highly restricted.
        if sys.platform != "win32":
            proc.send_signal(signal.SIGINT)
        else:
            proc.terminate()

        # 2. Wait for the program to finish its jobs
        proc.wait(timeout=10)
        log.info("Go server successfully finished its job and stopped.")

    except psutil.TimeoutExpired:
        log.warning("Go server did not finish within 60 seconds — forcing shutdown with SIGKILL.")
        proc.kill()
    except psutil.NoSuchProcess:
        # Process already died on its own before we could wait/kill
        log.info("Go server stopped.")
    except Exception as e:
        log.error(f"Unexpected error while stopping Go server: {e}")


def delete_go_server_db(db_name: str) -> None:
    """Drops the specified database from MongoDB."""
    log.info("Connecting to MongoDB to drop database: '%s'", db_name)
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        collections = client[db_name].list_collection_names()
        log.info(
            "Dropping entire database '%s' (collections found: %s) …",
            db_name,
            collections if collections else "none",
        )
        client.drop_database(db_name)
        log.info("Database '%s' dropped completely.", db_name)
    except Exception as e:
        log.error("Failed to drop database '%s': %s", db_name, e)

# ============================================================================
# Pipeline steps
# ============================================================================


def step_1_kill_go_server_if_running() -> None:
    log.info("Step 1: checking whether the Go server is running ...")
    kill_go_server()


def step_2_ensure_global_dataset() -> None:
    log.info("Step 2: checking %s ...", GLOBAL_DATASET_CSV.name)
    if not GLOBAL_DATASET_CSV.exists():
        log.info("%s not found — running fetch-domains-names.py.", GLOBAL_DATASET_CSV.name)
        
        # We pass ["--dedup", "n"] to skip the interactive prompt automatically!
        run_script("fetch_domains_names", ["--dedup", "n"])
        
    else:
        log.info("%s already exists — skipping fetch-domains-names.py.", GLOBAL_DATASET_CSV.name)


def step_3_run_data_renew() -> None:
    log.info("Step 3: running data-renew.py ...")
    run_script("data_renew")


def step_4_crawler_and_new_data() -> None:
    log.info("Step 4: evaluating crawler conditions ...")

    # =====================================================================
    # PART 1: New Data Crawler (Asynchronous / Background)
    # Fired first so it runs in parallel while the script blocks on Part 2
    # =====================================================================
    
    new_data_running = is_pid_file_process_alive(NEW_DATA_PID_FILE, "new-data.py")

    if new_data_running and NEW_DATA_CSV.exists():
        log.info("new-data.py is already running AND %s exists — deleting Go server DB.", NEW_DATA_CSV.name)
        delete_go_server_db(GO_SERVER_DB_NAME)
    else:
        log.info("new-data.py not running or %s is absent — launching new-data.py in background.", NEW_DATA_CSV.name)
        try:
            launch_background("new_data", pid_file=NEW_DATA_PID_FILE)
        except Exception:
            log.exception("Failed to launch new-data.py.")

    # =====================================================================
    # PART 2: Data Renew Crawler (Synchronous / Blocking)
    # The script will pause here and wait for this to finish before Step 5
    # =====================================================================
    if DATA_RENEW_CSV.exists():
        log.info("%s found — running crawler for data-renew synchronously.", DATA_RENEW_CSV.name)
        try:
            args = [
                "--db-name", "data-renew",
                "--certificates-collection", "certificates",
                "--csv-file", str(DATA_RENEW_CSV)
            ]
            # CRITICAL FIX: Using run_script instead of launch_background
            run_script("crawler", cli_args=args)
        except Exception:
            log.exception("Failed to run crawler for data-renew.")
    else:
        log.info("%s not found — skipping data-renew crawler.", DATA_RENEW_CSV.name)


def step_5_run_merge() -> None:
    log.info("Step 5: running data-renew-merge.py ...")
    run_script("data_renew_merge")


def step_6_delete_data_renew_csv_database() -> None:
    log.info("Step 6: deleting %s and dropping data-renew database ...", DATA_RENEW_CSV.name)

    # Delete CSV — Path.unlink() is cross-platform (works on Windows, Mac, Linux)
    if DATA_RENEW_CSV.exists():
        DATA_RENEW_CSV.unlink()
        log.info("%s deleted.", DATA_RENEW_CSV.name)
    else:
        log.info("%s already absent — nothing to delete.", DATA_RENEW_CSV.name)

    # Drop the data-renew MongoDB database
    log.info("Dropping database: 'data-renew' ...")
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.drop_database("data-renew")
        log.info("Database 'data-renew' dropped successfully.")
    except Exception as e:
        log.error("Failed to drop database 'data-renew': %s", e)


def step_7_run_generic() -> None:
    log.info("Step 7: running Generic ...")
    run_script("generic")


def step_8_start_go_server() -> None:
    log.info("Step 8: launching go-server.py as an independent background process ...")
    try:
        launch_background("go_server")
    except Exception:
        log.exception("Failed to launch go-server.py.")

# ============================================================================
# Entry point
# ============================================================================


def main() -> None:
    setup_logging()
    log.info("=== Pipeline run started ===")
    try:
        step_1_kill_go_server_if_running()
        step_2_ensure_global_dataset()
        step_3_run_data_renew()
        step_4_crawler_and_new_data()
        step_5_run_merge()
        step_6_delete_data_renew_csv_database()
        step_7_run_generic()
        step_8_start_go_server()

    except Exception:
        log.exception("Pipeline failed.")
        sys.exit(1)
    log.info("=== Pipeline run finished successfully ===")


if __name__ == "__main__":
    main()