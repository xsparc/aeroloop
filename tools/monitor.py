"""Serve read-only live physics telemetry on loopback."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aeroloop.live import monitor_server

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Exact output directory of a flight --monitor session")
    parser.add_argument("--port", type=int, default=8771)
    args = parser.parse_args()
    with monitor_server(args.directory, ROOT / "web/replay/demo-dist", args.port) as server:
        print(f"Live physics monitor: http://127.0.0.1:{server.server_port}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
