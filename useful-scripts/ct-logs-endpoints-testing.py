### This file is testing all of the endpoints [API's] for the CT logs used in ct_index.json
### and checking how much change happens at them in realtime 



import os
import json
import time
import httpx
import concurrent.futures
from collections import deque

def load_endpoints_from_json(filename="ct_index.json"):
    """Reads the endpoints directly from the local JSON file."""
    if not os.path.exists(filename):
        print(f"❌ Error: '{filename}' not found.")
        return []
        
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if isinstance(data, list): endpoints = data
        elif isinstance(data, dict):
            for key in ['logs', 'endpoints', 'urls', 'nodes']:
                if key in data and isinstance(data[key], list):
                    endpoints = data[key]
                    break
            else:
                endpoints = list(data.keys())
        else:
            return []
            
        cleaned_endpoints = []
        for item in endpoints:
            url = item.strip() if isinstance(item, str) else item.get('url', '').strip() if isinstance(item, dict) else ""
            if url: cleaned_endpoints.append(url)
                
        return cleaned_endpoints
    except Exception as e:
        print(f"❌ Error reading '{filename}': {e}")
        return []

def run_health_check_worker(log_url):
    """Startup worker: Finds out exactly which URL path works (/checkpoint vs /get-sth)."""
    base_url = log_url if log_url.startswith("http") else f"https://{log_url}"
    base_url = base_url.rstrip('/')
    
    api_url_checkpoint = f"{base_url}/checkpoint"
    api_url_json = f"{base_url}/ct/v1/get-sth"
    
    headers = {
        "User-Agent": "certstream-research-crawler/1.0 (cs_student@itu.edu.pk)",
        "Accept": "*/*"
    }
    
    try:
        with httpx.Client(http2=True, timeout=5.0) as client:
            # Try Checkpoint First
            resp_checkpoint = client.get(api_url_checkpoint, headers=headers)
            if resp_checkpoint.status_code == 200:
                lines = resp_checkpoint.text.strip().split('\n')
                if len(lines) >= 2 and lines[1].strip().isdigit():
                    return log_url, int(lines[1].strip()), "Checkpoint", api_url_checkpoint
            
            # Try JSON Second
            resp_json = client.get(api_url_json, headers=headers)
            if resp_json.status_code == 200:
                try:
                    return log_url, int(resp_json.json().get("tree_size", 0)), "JSON", api_url_json
                except Exception:
                    pass
            
            # Determine Failure
            if resp_checkpoint.status_code in [403, 404] and resp_json.status_code in [403, 404]:
                return log_url, None, f"Blocked or Missing (HTTP {resp_checkpoint.status_code})", None
            return log_url, None, f"Fail (CP: {resp_checkpoint.status_code}, JSON: {resp_json.status_code})", None
                
    except httpx.TimeoutException:
        return log_url, None, "Timeout", None
    except Exception as e:
        return log_url, None, f"Error: {str(e)[:30]}", None

def poll_fast_live_endpoint(exact_url, is_json):
    """Live loop worker: ONLY hits the known working URL for maximum speed."""
    headers = {"User-Agent": "certstream-research-crawler/1.0 (cs_student@itu.edu.pk)", "Accept": "*/*"}
    try:
        with httpx.Client(http2=True, timeout=3.0) as client:
            resp = client.get(exact_url, headers=headers)
            if resp.status_code == 200:
                if is_json:
                    return exact_url, int(resp.json().get("tree_size", 0))
                else:
                    return exact_url, int(resp.text.strip().split('\n')[1].strip())
    except Exception:
        pass
    return exact_url, None

def main():
    json_file = "ct_index.json"
    all_endpoints = load_endpoints_from_json(json_file)
    if not all_endpoints: return
        
    print("\n" + "="*110)
    print(f"🚀 STARTUP HEALTH CHECK: TESTING {len(all_endpoints)} ENDPOINTS")
    print("="*110)
    
    working_logs = {}
    broken_logs = {}
    
    # --- PHASE 1: STARTUP HEALTH CHECK ---
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_url = {executor.submit(run_health_check_worker, url): url for url in all_endpoints}
        for future in concurrent.futures.as_completed(future_to_url):
            base_url, tree_size, status, exact_url = future.result()
            if tree_size is not None:
                working_logs[exact_url] = {"size": tree_size, "is_json": (status == "JSON")}
            else:
                broken_logs[base_url] = status

    print(f"\n🟢 WORKING EXACT ENDPOINTS ({len(working_logs)}):")
    print(f"{'Exact Verified URL':<75} | {'Initial Size'}")
    print("-" * 110)
    for exact_url, info in sorted(working_logs.items()):
        print(f"{exact_url:<75} | {info['size']}")
        
    print(f"\n🔴 BROKEN ENDPOINTS ({len(broken_logs)}):")
    for base_url, status in sorted(broken_logs.items()):
        print(f"{base_url:<75} | {status}")
        
    if not working_logs:
        print("\n🛑 Zero working endpoints. Exiting.")
        return

    # --- PHASE 2: INITIALIZE LIVE STATE TRACKING ---
    # We use collections.deque(maxlen=3) to prevent memory leaks while keeping history
    log_state = {}
    for exact_url, info in working_logs.items():
        log_state[exact_url] = {
            "last_size": info["size"],
            "is_json": info["is_json"],
            "sth_history": deque([info["size"]], maxlen=3),
            "delta_history": deque([0], maxlen=3)
        }
        
    global_total_new = 0
    poll_interval = 2.0
    
    print("\n" + "="*110)
    print(f"📡 INITIATING LIVE REAL-TIME STREAM ({poll_interval}s TICK)")
    print("="*110)
    time.sleep(1) # Brief pause before the flood starts

    # --- PHASE 3: INFINITE POLLING LOOP ---
    while True:
        loop_start_time = time.time()
        loop_new_count = 0
        results = []
        
        # Concurrently poll ONLY the exact working URLs
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_url = {executor.submit(poll_fast_live_endpoint, url, state["is_json"]): url 
                             for url, state in log_state.items()}
            for future in concurrent.futures.as_completed(future_to_url):
                results.append(future.result())
                
        print("\n" + "━"*110)
        print(f"⏱️ POLLING WINDOW RESULTS")
        print(f"{'Exact URL':<60} | {'STH History':<30} | {'Delta History'}")
        print("-" * 110)
        
        # Process and Print
        for exact_url, current_size in sorted(results, key=lambda x: x[0]):
            state = log_state[exact_url]
            
            if current_size is None:
                print(f"⚠️ {exact_url[:58]:<60} | Connection Dropped / Timeout")
                continue
                
            delta = current_size - state["last_size"]
            
            if delta > 0:
                # Update memory-safe arrays
                state["sth_history"].append(current_size)
                state["delta_history"].append(delta)
                state["last_size"] = current_size
                
                loop_new_count += delta
                global_total_new += delta
                
                # Format output
                disp_sth = list(state["sth_history"])
                disp_del = list(state["delta_history"])
                print(f"✅ {exact_url[:58]:<60} | {str(disp_sth):<30} | {str(disp_del)}")
            else:
                print(f"💤 {exact_url[:58]:<60} | Nothing changes here")
                
        print("-" * 110)
        print(f"📈 Window Delta: +{loop_new_count} new certificates")
        print(f"🏆 GLOBAL TOTAL AUDITED: {global_total_new} certificates")
        print("━"*110)
        
        # Calculate precise sleep to maintain exactly a 2.0s tick, accounting for network latency
        elapsed = time.time() - loop_start_time
        sleep_time = max(0.1, poll_interval - elapsed)
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()