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

BASE_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable  # interpreter used to launch every child script

SCRIPTS = {
    "data_creator":     BASE_DIR / "data-creator.py",
    "data_renew":       BASE_DIR / "data-renew.py",
    "run_crawler":      BASE_DIR / "run-crawler.py",
    "renew_data_merge": BASE_DIR / "renew-data-merge.py",
    "new_data":         BASE_DIR / "new-data.py",
    # TODO confirm: what file does step 7 ("Run Generic") actually run?
    # Stubbed as generic.py until you tell me otherwise.
    "generic":          BASE_DIR / "generic.py",
}

GLOBAL_DATASET_CSV = BASE_DIR / "global-dataset.csv"
DATA_RENEW_CSV = BASE_DIR / "data-renew.csv"

# How we recognise the Go server process (matched against process name
# AND full command line, so a path containing this string also matches).
GO_SERVER_MATCH = "go-server"

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
            logging.FileHandler(LOG_DIR / "main.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )


log = logging.getLogger("pipeline")

# ============================================================================
# Helpers — running child scripts
# ============================================================================


def run_script(key: str) -> None:
    """Run a script synchronously and block until it finishes. Raises on failure."""
    path = SCRIPTS[key]
    log.info("Running %s ...", path.name)
    result = subprocess.run([PYTHON, str(path)], cwd=BASE_DIR)
    if result.returncode != 0:
        raise RuntimeError(f"{path.name} exited with code {result.returncode}")
    log.info("%s finished OK.", path.name)


def launch_background(key: str, pid_file: Optional[Path] = None) -> subprocess.Popen:
    """Start a script as a detached background process; optionally remember its PID."""
    path = SCRIPTS[key]
    log.info("Launching %s as a background process ...", path.name)

    out_log_path = LOG_DIR / f"{key}.out.log"
    out_log = open(out_log_path, "a")
    try:
        proc = subprocess.Popen(
            [PYTHON, str(path)],
            cwd=BASE_DIR,
            stdout=out_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,  # detach from main.py's process group
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

    log.info("Go server is running (PID %s) — sending SIGTERM.", proc.pid)
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except psutil.TimeoutExpired:
        log.warning("Go server did not stop in time — sending SIGKILL.")
        proc.kill()
    except psutil.NoSuchProcess:
        pass
    log.info("Go server stopped.")


def delete_go_server_db() -> None:
    """
    TODO: implement the real deletion logic.
    main.py doesn't have connection details for the go-server's database,
    so this is a stub — wire it up to whatever you already use elsewhere
    (e.g. a pymongo drop_database() call, or an admin endpoint).
    """
    log.warning("delete_go_server_db() is a stub — implement the real deletion logic here.")


# ============================================================================
# Pipeline steps
# ============================================================================


def step_1_kill_go_server_if_running() -> None:
    log.info("Step 1: checking whether the Go server is running ...")
    kill_go_server()


def step_2_ensure_global_dataset() -> None:
    log.info("Step 2: checking %s ...", GLOBAL_DATASET_CSV.name)
    if not GLOBAL_DATASET_CSV.exists():
        log.info("%s not found — running data-creator.py.", GLOBAL_DATASET_CSV.name)
        run_script("data_creator")
    else:
        log.info("%s already exists — skipping data-creator.py.", GLOBAL_DATASET_CSV.name)


def step_3_run_data_renew() -> None:
    log.info("Step 3: running data-renew.py ...")
    run_script("data_renew")


def step_4_crawler_and_new_data() -> None:
    log.info("Step 4: checking %s ...", DATA_RENEW_CSV.name)

    if DATA_RENEW_CSV.exists():
        log.info("%s found — launching run-crawler.py in the background.", DATA_RENEW_CSV.name)
        try:
            launch_background("run_crawler")
        except Exception:
            log.exception("Failed to launch run-crawler.py — continuing with the rest of the pipeline.")
    else:
        log.info("%s not found — skipping run-crawler.py.", DATA_RENEW_CSV.name)

    if is_pid_file_process_alive(NEW_DATA_PID_FILE, "new-data.py"):
        log.info("new-data.py is already running from a previous cycle — deleting go-server DB.")
        delete_go_server_db()
    else:
        log.info("new-data.py is not running — launching it in the background.")
        try:
            launch_background("new_data", pid_file=NEW_DATA_PID_FILE)
        except Exception:
            log.exception("Failed to launch new-data.py — continuing with the rest of the pipeline.")


def step_5_run_merge() -> None:
    log.info("Step 5: running renew-data-merge.py ...")
    run_script("renew_data_merge")


def step_6_delete_data_renew_csv() -> None:
    log.info("Step 6: deleting %s ...", DATA_RENEW_CSV.name)
    if DATA_RENEW_CSV.exists():
        DATA_RENEW_CSV.unlink()
        log.info("%s deleted.", DATA_RENEW_CSV.name)
    else:
        log.info("%s already absent — nothing to delete.", DATA_RENEW_CSV.name)


def step_7_run_generic() -> None:
    log.info("Step 7: running Generic ...")
    run_script("generic")


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
        step_6_delete_data_renew_csv()
        step_7_run_generic()
    except Exception:
        log.exception("Pipeline failed.")
        sys.exit(1)
    log.info("=== Pipeline run finished successfully ===")


if __name__ == "__main__":
    main()