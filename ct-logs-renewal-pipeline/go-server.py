import sys
import os
import signal
import subprocess
import websocket
import json
import time
import threading
import psutil
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.errors import BulkWriteError

# ==========================================
# CONFIGURATION & BINARY NAMING
# ==========================================
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "go-server"
MAIN_COLLECTION = "certificates"
META_COLLECTION = "metadata"

# Exact process name of your Go binary
GO_BINARY_NAME = "./binaries/certstream-server-go_1.9.0_macOS_amd64"
# Path to execute if it needs to be spawned (assumes current directory, adjust if needed)
GO_BINARY_EXEC_PATH = f"./{GO_BINARY_NAME}" 

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[MAIN_COLLECTION]
meta_collection = db[META_COLLECTION]

# Guarantee unique multikey index exists
collection.create_index("domains", unique=True)

# ==========================================
# CRAWLER STATE & METRICS
# ==========================================
BATCH_SIZE = 5000
batch_buffer = {}  

crawler_started_at = datetime.now(timezone.utc).isoformat()
total_batches_processed = 0
total_domains_processed = 0   
total_certificates_saved = 0  

# Track if this Python execution spawned the child process
go_process_reference = None

# ==========================================
# PROCESS MANAGEMENT FUNCTIONS
# ==========================================
def is_go_server_running():
    """Checks running processes for the Go binary — cross-platform via psutil."""
    try:
        
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                cmdline = " ".join(proc.info["cmdline"] or [])
                if GO_BINARY_NAME in cmdline:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    except Exception as e:
        print(f"⚠️ Error checking process status: {e}")
        return False

def manage_go_server_startup():
    """Ensures the Go backend firehose is running before Python attaches."""
    global go_process_reference
    
    if is_go_server_running():
        print(f"ℹ️  Process '{GO_BINARY_NAME}' is already active. Utilizing current stream.")
    else:
        print(f"⚙️  '{GO_BINARY_NAME}' not detected. Spawning background instance...")
        try:
            # Spawn as a completely separate process group so it doesn't instantly die if python stumbles unexpectedly
            go_process_reference = subprocess.Popen(
                [GO_BINARY_EXEC_PATH],
                stdout=subprocess.DEVNULL, # Mute stdout/stderr to prevent cluttering ingestion terminal logs
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid
            )
            # Give the server 2 seconds to warm up and bind to port 8080
            time.sleep(2.0)
            print("🚀 Background process successfully initiated.")
        except Exception as e:
            print(f"❌ Failed to spawn Go binary at {GO_BINARY_EXEC_PATH}: {e}")
            print("⚠️ Ingestion script terminating due to missing stream dependency.")
            sys.exit(1)

def terminate_go_server_gracefully():
    """Terminates the Go binary via psutil — cross-platform."""
    print(f"🛑 Killing target backend process '{GO_BINARY_NAME}' gracefully...")
    try:
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                cmdline = " ".join(proc.info["cmdline"] or [])
                if GO_BINARY_NAME in cmdline:
                    proc.send_signal(signal.SIGTERM)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        print(f"⚠️ Error during process termination routine: {e}")

# ==========================================
# GRACEFUL SHUTDOWN HANDLER
# ==========================================
def graceful_shutdown(signum, frame):
    """Caught an OS kill signal (Ctrl+C or standard pkill). Flush memory and clean up dependencies."""
    print(f"\n\n🛑 SHUTDOWN SIGNAL CAUGHT ({signum}). Initiating Graceful Exit...")
    
    # 1. Clear out dependency process first to stop incoming WebSocket data flood
    terminate_go_server_gracefully()
    
    # 2. Flush remaining records from memory
    if batch_buffer:
        print(f"📦 Rescuing {len(batch_buffer)} pending certificates from RAM...")
        flush_batch_to_db()
    else:
        print("📦 RAM buffer is empty. No final flush required.")

    # 3. Save final telemetry counters
    print("⏱️ Syncing final metadata to database...")
    try:
        meta_collection.update_one(
            {"_id": "run_status"},
            {"$set": {
                "crawler_started_at": crawler_started_at,
                "total_batches_processed": total_batches_processed,
                "total_domains_processed": total_domains_processed,
                "total_certificates_saved": total_certificates_saved,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )
    except Exception as e:
        print(f"⚠️ Final sync failed: {e}")

    print("✅ Graceful shutdown complete. Goodbye!")
    sys.exit(0)

# Register signal catchers
signal.signal(signal.SIGINT, graceful_shutdown)  # Ctrl+C
signal.signal(signal.SIGTERM, graceful_shutdown) # Standard pkill

# ==========================================
# CORE PIPELINE FUNCTIONS
# ==========================================
def flush_metadata_loop():
    """Background thread: Saves metrics to MongoDB every 5 seconds."""
    while True:
        time.sleep(5.0)
        try:
            meta_collection.update_one(
                {"_id": "run_status"},
                {"$set": {
                    "crawler_started_at": crawler_started_at,
                    "total_batches_processed": total_batches_processed,
                    "total_domains_processed": total_domains_processed,
                    "total_certificates_saved": total_certificates_saved,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }},
                upsert=True
            )
            print(f"⏱️ [METADATA] DB Saved: {total_certificates_saved} | Domains Audited: {total_domains_processed}")
        except Exception:
            pass

def flush_batch_to_db():
    """Flushes the RAM buffer to MongoDB and tracks success rates."""
    global batch_buffer, total_batches_processed, total_certificates_saved
    
    if not batch_buffer:
        return

    records_to_insert = list(batch_buffer.values())
    batch_buffer.clear()
    
    total_batches_processed += 1

    try:
        result = collection.insert_many(records_to_insert, ordered=False)
        inserted = len(result.inserted_ids)
        total_certificates_saved += inserted
        print(f"💾 [DB WRITE] Batch {total_batches_processed} -> {inserted} newly saved (0 historical duplicates).")
    except BulkWriteError as bwe:
        inserted = bwe.details['nInserted']
        total_certificates_saved += inserted
        dropped = len(records_to_insert) - inserted
        print(f"💾 [DB WRITE] Batch {total_batches_processed} -> {inserted} newly saved (Dropped {dropped} historical duplicates in DB).")
    except Exception as e:
        print(f"⚠️ Database Error during flush: {e}")

def on_message(ws, message):
    """Processes the live firehose stream."""
    global total_domains_processed, batch_buffer
    
    try:
        data = json.loads(message)
        discovered_domains = data.get('data', [])
        
        if not discovered_domains:
            return

        clean_domains = list(set([d.replace('*.', '') for d in discovered_domains]))
        total_domains_processed += len(clean_domains)

        cert_signature = tuple(sorted(clean_domains))
        
        if cert_signature not in batch_buffer:
            batch_buffer[cert_signature] = {
                "domains": clean_domains,
                "found": False
            }

        if len(batch_buffer) >= BATCH_SIZE:
            flush_batch_to_db()

    except Exception:
        pass

def on_open(ws):
    print("\n🚀 Successfully connected to local Go WebSocket: /domains-only")
    print("ℹ️  Press Ctrl+C or use standard 'kill' to safely terminate both scripts.")
    print("========================================================================\n")

if __name__ == "__main__":
    print("Checking infrastructure dependencies...")
    manage_go_server_startup()
    
    print("Initiating MongoDB Connection & Background Services...")
    threading.Thread(target=flush_metadata_loop, daemon=True).start()

    websocket_url = "ws://localhost:8080/domains-only"
    
    ws = websocket.WebSocketApp(
        websocket_url,
        on_open=on_open,
        on_message=on_message,
        on_error=lambda ws, err: print(f"Connection Error: {err}"),
        on_close=lambda ws, stat, msg: print("\n### WebSocket Connection Closed ###")
    )

    ws.run_forever()