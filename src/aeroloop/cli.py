"""Only implemented commands are exposed."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from .contracts import ValidationError, load_json, validate_lock
from .doctor import probe

ROOT = Path(__file__).resolve().parents[2]


def main(argv=None):
    parser = argparse.ArgumentParser(prog="aeroloop", description="Simulation-only flight-control laboratory")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="inspect capabilities without installing software")
    lock = commands.add_parser("check-lock", help="validate dependency compatibility metadata")
    lock.add_argument("path", nargs="?", type=Path, default=ROOT / "versions.lock.json")
    test = commands.add_parser("test", help="run Python unit and contract tests")
    test.add_argument("--suite", choices=["cpu"], default="cpu")
    sim = commands.add_parser("simulate", help="record a CPU physics experiment with the native C++ controller")
    sim.add_argument("--scenario", choices=["hover", "position-step", "lateral-force-pulse"], default="hover")
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--dt", type=float, default=0.005)
    sim.add_argument("--output", type=Path, default=ROOT / "runs")
    suite = commands.add_parser("regress", help="run five seeds per CPU scenario and retain every outcome")
    suite.add_argument("--output", type=Path, default=ROOT / "runs")
    export = commands.add_parser("export", help="validate recordings and export a local research preview")
    export.add_argument("runs", nargs="+", type=Path)
    export.add_argument("--output", required=True, type=Path)
    verify = commands.add_parser("verify-run", help="verify checksums, conventions and recomputed metrics")
    verify.add_argument("run", type=Path)
    preview = commands.add_parser("showcase", help="serve an exported bundle on loopback only")
    preview.add_argument("--bundle", required=True, type=Path)
    preview.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            print(json.dumps(probe(), indent=2))
        elif args.command == "check-lock":
            validate_lock(load_json(args.path))
            print("Dependency lock is structurally valid; compatibility is not implied.")
        elif args.command == "test":
            return subprocess.call([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT)
        elif args.command in ("simulate", "regress"):
            from .simulation import SCENARIOS, encoded, record, simulate
            trials = [(args.scenario, args.seed)] if args.command == "simulate" else [(s, seed) for s in SCENARIOS for seed in range(5)]
            results = []
            for scenario, seed in trials:
                result = simulate(scenario, seed, dt=args.dt if args.command == "simulate" else .005)
                directory = record(result, args.output)
                summary = {"run_id": directory.name, "scenario": scenario, "seed": seed,
                           "status": result["status"], "metrics": result["metrics"]}
                results.append(summary)
                print(json.dumps(summary))
            if args.command == "regress":
                import uuid
                report = {"schema_version": 1, "trials": len(results), "passed": sum(r["status"] == "passed" for r in results), "results": results}
                (args.output / f"regression-{uuid.uuid4().hex[:12]}.json").write_bytes(encoded(report))
            return int(any(r["status"] != "passed" for r in results))
        elif args.command == "export":
            from .evidence import export_bundle
            result = export_bundle(args.runs, args.output)
            print(f"Exported {len(result['runs'])} verified recordings; research preview, Isaac not validated.")
        elif args.command == "verify-run":
            from .evidence import read_run
            read_run(args.run)
            print("Recording checksums, contracts and full-resolution metrics verified.")
        elif args.command == "showcase":
            from .server import serve
            if not 0 <= args.port <= 65535:
                raise ValidationError("invalid preview port")
            serve(args.bundle, args.port)
    except (OSError, ValueError) as error:
        print(f"aeroloop: {type(error).__name__}: input invalid or unavailable" if not isinstance(error, ValidationError)
              else f"aeroloop: {error}", file=sys.stderr)
        return 2
    return 0
