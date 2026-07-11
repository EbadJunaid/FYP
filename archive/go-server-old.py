import websocket
import json
import time

# ==========================================
# CONFIGURATION
# ==========================================
# Options: "domains-only", "lite-stream", "full-stream"
ENDPOINT_CHOICE = "domains-only"

# ==========================================

# Global variables for metrics
domain_counter = 0
certificate_counter = 0
start_time = time.time()

# Ask user for print preference before starting
user_input = input(f"Do you want to print the live data for '{ENDPOINT_CHOICE}'? (y/n): ").strip().lower()
PRINT_DATA = user_input == 'y'

def on_message(ws, message):
    global domain_counter, certificate_counter, start_time
    try:
        data = json.loads(message)
        discovered_domains = []
        raw_output_to_print = None

        # 1. Parse logic depending on endpoint
        if ENDPOINT_CHOICE == "domains-only":
            discovered_domains = data.get('data', [])
            raw_output_to_print = discovered_domains
            
        elif ENDPOINT_CHOICE == "lite-stream":
            if data.get('message_type') == 'certificate_update':
                discovered_domains = data.get('data', {}).get('leaf_cert', {}).get('all_domains', [])
                raw_output_to_print = data.get('data', {}).get('leaf_cert', {})
                
        elif ENDPOINT_CHOICE == "full-stream":
            if data.get('message_type') == 'certificate_update':
                discovered_domains = data.get('data', {}).get('leaf_cert', {}).get('all_domains', [])
                raw_output_to_print = data

        # 2. Clean domains and update the counters
        clean_domains = list(set([d.replace('*.', '') for d in discovered_domains]))
        domain_counter +=1 
        certificate_counter += len(clean_domains)

        # 3. Print the data if the user requested it
        if PRINT_DATA and raw_output_to_print:
            if ENDPOINT_CHOICE == "domains-only":
                 print(f"✅ Discovered: {clean_domains} , Counter : {domain_counter}")
            else:
                 # Print lite/full stream JSON beautifully indented
                 print(json.dumps(raw_output_to_print, indent=2))

        # 4. Calculate and display throughput every 1 second
        current_time = time.time()
        elapsed_time = current_time - start_time
        
        if elapsed_time >= 1.0:
            domains_per_second = domain_counter / elapsed_time
            print(f"📊 Speed Metrics: {domains_per_second:.2f} domains/sec | Window Total: {domain_counter}")
            
            # Reset counters
            domain_counter = 0
            start_time = time.time()

    except Exception as e:
        print(f"Parsing error: {e}")

def on_open(ws):
    print(f"\n🚀 Successfully connected to local endpoint: /{ENDPOINT_CHOICE}")
    if not PRINT_DATA:
        print("🔕 Live data printing disabled. Showing metrics only...\n")

if __name__ == "__main__":
    if ENDPOINT_CHOICE == "domains-only":
        url_suffix = "domains-only"
    elif ENDPOINT_CHOICE == "lite-stream":
        url_suffix = ""
    elif ENDPOINT_CHOICE == "full-stream":
        url_suffix = "full-stream"

    websocket_url = f"ws://localhost:8080/{url_suffix}"
    
    ws = websocket.WebSocketApp(
        websocket_url,
        on_open=on_open,
        on_message=on_message,
        on_error=lambda ws, err: print(f"Error: {err}"),
        on_close=lambda ws, stat, msg: print("### Connection Closed ###")
    )

    ws.run_forever()