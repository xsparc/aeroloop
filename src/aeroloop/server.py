"""A loopback-only preview serves a verified bundle's explicit file allowlist."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from .contracts import ValidationError, load_json
from .evidence import RUN_ID, HASH, require
from .simulation import sha256


def serve(bundle, port=8765):
    bundle = Path(bundle).resolve()
    index = load_json(bundle / "index.json")
    require(type(index.get("schema_version")) is int and index["schema_version"] in (1, 2, 3, 4, 5) and isinstance(index.get("checksums"), dict), "invalid bundle index")
    allowed = {"index.html", "index.json", "viewer.js", "viewer.css"}
    for name, digest in index["checksums"].items():
        parts = name.split("/")
        require(len(parts) == 2 and RUN_ID.fullmatch(parts[0]) and parts[1] in ("manifest.json", "config.json", "samples.json", "events.json", "metrics.json", "replay.json"), "unsafe bundle path")
        require(isinstance(digest, str) and HASH.fullmatch(digest), "invalid bundle checksum")
        allowed.add(name)
    for name in allowed:
        path = bundle / name
        require(path.resolve().is_relative_to(bundle) and path.is_file() and not path.is_symlink(), "unsafe or missing bundle file")
        if name in index["checksums"]:
            require(path.stat().st_size <= 32*1024*1024 and sha256(path.read_bytes()) == index["checksums"][name], "bundle checksum mismatch")

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            name = urlsplit(self.path).path.removeprefix("/") or "index.html"
            if name not in allowed:
                self.send_error(404)
                return
            self.path = "/" + name
            super().do_GET()

        def do_HEAD(self):
            name = urlsplit(self.path).path.removeprefix("/") or "index.html"
            if name not in allowed:
                self.send_error(404)
                return
            self.path = "/" + name
            super().do_HEAD()

        def end_headers(self):
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def log_message(self, *_):
            pass

    with ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=str(bundle))) as server:
        print(f"Recorded simulation preview: http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
