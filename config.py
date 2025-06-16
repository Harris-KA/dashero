# config.py

# URL for your monerod RPC server
# Default for mainnet running locally:
MONEROD_RPC_URL = "	http://10.0.0.45:18081/json_rpc"

# Example for testnet running locally:
# MONEROD_RPC_URL = "http://127.0.0.1:28081/json_rpc"

# Example for stagenet running locally:
# MONEROD_RPC_URL = "http://127.0.0.1:38081/json_rpc"

# If your monerod requires authentication (using --rpc-login user:pass):
# MONEROD_RPC_USER = "your_rpc_user"
# MONEROD_RPC_PASSWORD = "your_rpc_password"
MONEROD_RPC_USER = None
MONEROD_RPC_PASSWORD = None

# How often to refresh the data (in seconds) - used by the HTML meta tag
REFRESH_INTERVAL = 30