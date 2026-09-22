"""Bounded, read-only loopback observation of a running physics worker."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import math
import os
from pathlib import Path
import time

from .contracts import ValidationError, finite, load_json
from .frames import vector
from .simulation import encoded

STATES = ("starting", "running", "verifying", "completed", "failed")
FIELDS = ("time_s", "sequence", "position_m", "velocity_m_s", "quaternion_wxyz", "target_m",
          "rates_rad_s", "rate_setpoint_rad_s", "effort_normalized", "rotor_thrust_n",
          "allocation_scale", "wind_velocity_m_s", "external_force_n", "mission_phase",
          "contact_normal_force_n", "support_clearance_m")
PHASES = ("grounded", "takeoff", "hover", "north", "north_hold", "east", "east_hold",
          "return", "home_hold", "landing", "landed")


def validate_snapshot(value):
    expected = {"schema_version", "state", "seed", "physics_dt_s", "paced", "elapsed_s",
                "lag_s", "max_lag_s", "late_steps", "updated_monotonic_s", "sample"}
    if not isinstance(value, dict) or set(value) != expected:
        raise ValidationError("invalid monitor fields")
    if (type(value["schema_version"]) is not int or value["schema_version"] != 1 or value["state"] not in STATES
            or type(value["seed"]) is not int or not 0 <= value["seed"] <= 2**31-1
            or value["physics_dt_s"] not in (.005, .0025, .00125) or type(value["paced"]) is not bool
            or type(value["late_steps"]) is not int or not 0 <= value["late_steps"] <= 10001):
        raise ValidationError("invalid monitor state")
    for key in ("elapsed_s", "lag_s", "max_lag_s", "updated_monotonic_s"):
        if not finite(value[key]) or value[key] < 0:
            raise ValidationError("invalid monitor clock")
    s = value["sample"]
    if s is None:
        if value["state"] not in ("starting", "failed"):
            raise ValidationError("missing live sample")
        return value
    if not isinstance(s, dict) or set(s) != set(FIELDS):
        raise ValidationError("invalid live sample fields")
    if (type(s["sequence"]) is not int or not 0 <= s["sequence"] <= 10000
            or not finite(s["time_s"]) or abs(s["time_s"] - s["sequence"]*.005) > 1e-8
            or s["mission_phase"] not in PHASES):
        raise ValidationError("invalid live sequence")
    for key in set(FIELDS) - {"time_s", "sequence", "mission_phase", "allocation_scale", "support_clearance_m"}:
        vector(s[key], 4 if key in ("quaternion_wxyz", "rotor_thrust_n") else 3)
    if (abs(math.hypot(*s["quaternion_wxyz"])-1) > 1e-6
            or not finite(s["allocation_scale"]) or not 0 <= s["allocation_scale"] <= 1
            or not finite(s["support_clearance_m"])):
        raise ValidationError("invalid live pose")
    return value


def write_snapshot(directory, value):
    content = encoded(validate_snapshot(value))
    path = Path(directory) / "live.json"
    temporary = path.with_suffix(".tmp")
    # The selected session is locally owned; refuse link substitution too.
    if path.is_symlink() or temporary.is_symlink():
        raise ValidationError("linked monitor file")
    temporary.write_bytes(content)
    # A brief Windows reader lock must not abort an otherwise valid flight.
    # If all attempts collide, retain the old frame; the monitor reports its age.
    for attempt in range(3):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt < 2:
                time.sleep(.001)


class FlightClock:
    """Wall pacing never changes simulated dt or drops integration steps."""
    def __init__(self, paced=False, clock=time.perf_counter, sleep=time.sleep):
        self.clock, self.sleep, self.paced = clock, sleep, paced
        self.start = clock()
        self.elapsed = self.lag = self.max_lag = 0.
        self.late_steps = 0

    def tick(self, simulation_s):
        remaining = self.start + simulation_s - self.clock()
        if self.paced and remaining > 0:
            self.sleep(remaining)
        self.elapsed = max(0., self.clock()-self.start)
        self.lag = max(0., self.elapsed-simulation_s)
        self.max_lag = max(self.max_lag, self.lag)
        self.late_steps += self.lag > .005

    def snapshot(self, seed, dt, sample=None, state="running"):
        return {"schema_version": 1, "state": state, "seed": seed, "physics_dt_s": dt,
                "paced": self.paced, "elapsed_s": self.elapsed, "lag_s": self.lag,
                "max_lag_s": self.max_lag, "late_steps": self.late_steps,
                "updated_monotonic_s": self.clock(),
                "sample": {key: sample[key] for key in FIELDS} if sample else None}


def finish_monitor(directory, passed):
    path = Path(directory) / "live.json"
    if path.is_file() and not path.is_symlink():
        value = validate_snapshot(load_json(path, 16384))
        value.update(state="completed" if passed else "failed", updated_monotonic_s=time.perf_counter())
        write_snapshot(directory, value)


def monitor_server(directory, assets, port=8771):
    """Only explicit built assets and sanitized telemetry can leave this server."""
    directory, assets = Path(directory).absolute(), Path(assets).resolve()
    files = {"/": assets / "monitor.html"}
    for path in (assets / "assets").glob("*"):
        if path.suffix in (".js", ".css"):
            files["/assets/" + path.name] = path
    payloads = {}
    for name, path in files.items():
        if (path.is_symlink() or not path.resolve().is_relative_to(assets)
                or not path.is_file() or path.stat().st_size > 8*1024*1024):
            raise ValidationError("invalid monitor asset")
        payloads[name] = (path.read_bytes(), "text/javascript" if path.suffix == ".js" else
                          "text/css" if path.suffix == ".css" else "text/html")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            hosts = (f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}")
            host, origin = self.headers.get("Host"), self.headers.get("Origin")
            if (host not in hosts or origin not in (None, "http://" + host)
                    or self.headers.get("Sec-Fetch-Site") == "cross-site"):
                self.respond(403, b"Forbidden", "text/plain")
                return
            if self.path == "/api/live":
                try:
                    path = directory / "live.json"
                    if directory.is_symlink() or path.is_symlink() or directory.resolve() != directory:
                        raise ValidationError("linked session")
                    value = validate_snapshot(load_json(path, 16384))
                    age = max(0., time.perf_counter()-value.pop("updated_monotonic_s"))
                    value.update(age_s=age, stale=value["state"] in ("running", "verifying") and age > 1.)
                    self.respond(200, encoded(value), "application/json")
                except FileNotFoundError:
                    self.respond(200, encoded({"state": "waiting"}), "application/json")
                except (OSError, ValueError, TypeError):
                    self.respond(503, encoded({"state": "unavailable"}), "application/json")
            elif self.path in payloads:
                self.respond(200, *payloads[self.path])
            else:
                self.respond(404, b"Not found", "text/plain")

        def do_POST(self):
            self.respond(405, b"Read only", "text/plain")

        do_PUT = do_DELETE = do_PATCH = do_POST

        def respond(self, code, data, content_type):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *_):
            pass

        def setup(self):
            super().setup()
            self.connection.settimeout(2.)

    return HTTPServer(("127.0.0.1", port), Handler)
