import requests
import json
from flask import Flask, render_template
from datetime import datetime, timedelta
import math
import time # Import time for uptime calculation

# --- Configuration Loading ---
try:
    import config
except ImportError:
    print("Error: config.py not found. Please create it.")
    exit(1)

# --- Flask App Initialization ---
app = Flask(__name__)

# Store daemon start time roughly (won't be exact across restarts)
# A more robust solution would store this externally or parse logs
daemon_start_time = time.time()

# --- Helper Functions ---
def format_bytes(size_bytes):
   """Formats byte count into KB, MB, GB etc."""
   if size_bytes == 0:
       return "0 B"
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size_bytes, 1024)))
   p = math.pow(1024, i)
   s = round(size_bytes / p, 2)
   return f"{s} {size_name[i]}"

def format_hash_rate(hr):
    """Formats hash rate (H/s) into kH/s, MH/s, GH/s etc."""
    if hr == 0: return "0 H/s"
    units = ['H/s', 'kH/s', 'MH/s', 'GH/s', 'TH/s', 'PH/s']
    # Ensure power calculation handles potentially very small or large numbers safely
    try:
        # Use max(1, hr) to avoid log10(0) or log10(<1) issues if hr is tiny
        power = int(math.log10(max(1, hr)) / 3) if hr > 0 else 0
    except ValueError:
        power = 0 # Handle potential math errors gracefully
    power = max(0, power) # Ensure power is not negative
    unit = units[min(power, len(units) - 1)]
    value = hr / (1000 ** power)
    return f"{value:.2f} {unit}"

def format_uptime(seconds):
    """Formats seconds into a human-readable duration."""
    if seconds < 0: seconds = 0
    delta = timedelta(seconds=int(seconds))
    days, remainder = divmod(delta.total_seconds(), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if days > 0: parts.append(f"{int(days)}d")
    if hours > 0: parts.append(f"{int(hours)}h")
    if minutes > 0: parts.append(f"{int(minutes)}m")
    if not parts: # If less than a minute, show seconds
         parts.append(f"{int(secs)}s")

    return " ".join(parts) if parts else "0s"


def call_monerod_rpc(method, params={}):
    """Makes a JSON-RPC call to the monerod daemon."""
    headers = {'Content-Type': 'application/json'}
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": "0",
        "method": method,
        "params": params
    })

    auth = None
    if config.MONEROD_RPC_USER and config.MONEROD_RPC_PASSWORD:
        auth = requests.auth.HTTPDigestAuth(config.MONEROD_RPC_USER, config.MONEROD_RPC_PASSWORD)

    try:
        response = requests.post(
            config.MONEROD_RPC_URL,
            data=payload,
            headers=headers,
            auth=auth,
            timeout=15 # Increased timeout slightly for potentially larger connection list
        )
        response.raise_for_status()
        data = response.json()

        if 'error' in data:
            return None, f"RPC Error ({method}): {data['error'].get('message', 'Unknown RPC error')} (Code: {data['error'].get('code', 'N/A')})"
        elif 'result' in data:
            return data['result'], None
        else:
            return None, f"Invalid RPC response format ({method})"

    except requests.exceptions.ConnectionError as e:
        return None, f"Connection Error: Could not connect to {config.MONEROD_RPC_URL}. Is monerod running? {e}"
    except requests.exceptions.Timeout:
        return None, f"Connection Timeout: Request to {config.MONEROD_RPC_URL} timed out ({method})."
    except requests.exceptions.RequestException as e:
        return None, f"Request Error ({method}): {e}"
    except json.JSONDecodeError:
        return None, f"JSON Decode Error: Invalid response received from server ({method})."
    except Exception as e:
        return None, f"An unexpected error occurred ({method}): {e}"


# --- Flask Routes ---
@app.route('/')
def index():
    """Main route to display the dashboard."""
    global daemon_start_time # Access the global start time

    # Call get_info
    info_result, info_error = call_monerod_rpc('get_info')

    # Call get_connections
    connections_result, conn_error = call_monerod_rpc('get_connections')

    # Combine errors if any
    error = info_error or conn_error # Show the first error encountered

    dashboard_data = None
    processed_connections = None
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if info_result:
        # --- Process get_info data ---
        target_height = info_result.get('target_height', 0)
        height = info_result.get('height', 0)
        # If daemon restarts, target_height might be 0 initially
        if target_height == 0 and height > 0:
            target_height = height # Avoid division by zero and nonsensical percentages

        sync_percentage = (height / target_height * 100) if target_height > 0 else (100 if height > 0 else 0)
        sync_percentage = max(0, min(sync_percentage, 100))

        # Try to get start_time from RPC info (more accurate than global var)
        rpc_start_time_secs = info_result.get('start_time', 0)
        if rpc_start_time_secs > 0:
             uptime_seconds = time.time() - rpc_start_time_secs
        else:
             # Fallback to rough uptime calculation if start_time not in RPC
             uptime_seconds = time.time() - daemon_start_time

        difficulty = info_result.get('difficulty', 0)
        target_block_time = info_result.get('target', 120) # Default to 120 seconds
        if target_block_time <= 0: target_block_time = 120 # Avoid division by zero

        hash_rate = difficulty / target_block_time if difficulty > 0 else 0

        dashboard_data = {
            'height': height,
            'target_height': target_height if target_height >= height else height,
            'difficulty': difficulty,
            'hash_rate': hash_rate,
            'hash_rate_formatted': format_hash_rate(hash_rate),
            'tx_pool_size': info_result.get('tx_pool_size', 0),
            'incoming_connections_count': info_result.get('incoming_connections_count', 0),
            'outgoing_connections_count': info_result.get('outgoing_connections_count', 0),
            'total_connections': (info_result.get('incoming_connections_count', 0) +
                                  info_result.get('outgoing_connections_count', 0)),
            'version': info_result.get('version', 'N/A'),
            'nettype': info_result.get('nettype', 'N/A'),
            'synchronized': info_result.get('synchronized', False),
            'sync_percentage': sync_percentage,
            'uptime_seconds': uptime_seconds,
            'uptime_formatted': format_uptime(uptime_seconds),
            'start_time': info_result.get('start_time', 0) # Store raw start time if available
        }

    if connections_result and 'connections' in connections_result:
        # --- Process get_connections data ---
        processed_connections = []
        for conn in connections_result['connections']:
            processed_connections.append({
                'incoming': conn.get('incoming', False),
                # Prefer 'address_str' if available (combines IP and port cleanly)
                'address': conn.get('address_str', f"{conn.get('ip', 'N/A')}:{conn.get('port', 'N/A')}"),
                'ip': conn.get('ip', 'N/A'),
                'port': conn.get('port', 'N/A'),
                'recv_count': conn.get('recv_count', 0),
                'send_count': conn.get('send_count', 0),
                'recv_count_formatted': format_bytes(conn.get('recv_count', 0)),
                'send_count_formatted': format_bytes(conn.get('send_count', 0)),
                # Add other fields if needed: state, height, live_time, avg_download, avg_upload etc.
            })
        # Optional: Sort connections, e.g., by IP
        processed_connections.sort(key=lambda x: (x['ip'], x['port']))


    # Render the template
    return render_template(
        'index.html',
        data=dashboard_data,
        connections=processed_connections,
        error=error,
        current_time=current_time_str,
        refresh_interval=config.REFRESH_INTERVAL
        )

# --- Run the App ---
if __name__ == '__main__':
    # Use host='0.0.0.0' to allow access from other devices on your network
    # Use host='127.0.0.1' to restrict access to only the machine running the script
    app.run(host='0.0.0.0', port=5000, debug=False) # Turn off debug for basic deployment
