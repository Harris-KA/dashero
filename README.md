# Dashero

Simple Flask dashboard for monitoring a Monero node via RPC.

## Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Update `config.py` with the URL of your `monerod` RPC server.
3. Run the application:
   ```bash
   python app.py
   ```
4. Open `http://localhost:5000` in your browser.



## Docker

You can run the dashboard in a container.

Build the image:

```bash
docker build -t dashero .
```

Run the container (mounting your `config.py` for configuration):

```bash
docker run --rm -p 5000:5000 \
    -v $(pwd)/config.py:/app/config.py \
    dashero
```

Then open `http://localhost:5000` in your browser.
