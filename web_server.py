#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import mimetypes
import os
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import workflow


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
ANALYSIS_ROOT = ROOT / "analysis"
CONFIG_PATH = ROOT / "config.json"
MAX_BODY_BYTES = 128 * 1024

EXPECTED_OUTPUTS = {
    "Polymer_Densify_R1.in": "Polymer_Densify_R1.dat.gz",
    "Polymer_AN_R1.in": "Polymer_AN_R1.dat.gz",
    "Polymer_ANEq_R1.in": "Polymer_ANEq_R1.dat.gz",
    "Polymer_ANEqPly_R1_1.in": "Polymer_ANEqPly_R1_1.data.gz",
    "Polymer_ANEqPly_R1_2.in": "Polymer_ANEqPly_R1_2.data.gz",
    "Polymer_ANEqPlyAN_R1.in": "Polymer_ANEqPlyAN_R1.dat.gz",
    "Polymer_ANEqPlyANEq_R1.in": "Polymer_ANEqPlyANEq_R1.dat.gz",
}


DEFAULT_CONFIG = {
    "environment": {
        "lammps_bin": "",
        "mpi_command": "mpiexec",
        "slurm_account": "",
        "slurm_mail_user": "",
    },
    "workflow": {
        "queue": "standard",
        "nodes": 1,
        "cores": 128,
        "start_data": "",
        "final_data": "",
        "dry_run": False,
        "submit": False,
        "run_dir": "",
        "run_name": "",
        "poly_same_settings": False,
        "seed_mode": "auto",
        "show_advanced": False,
        "target_density": 1.264,
        "densify_temp": 300,
        "densify_pressure": 1.0,
        "densify_velocity_seed": "",
        "densify_nvt_steps": 100000,
        "densify_npt_loops": 50,
        "densify_npt_steps": 20000,
        "densify_rate": 20,
        "densify_thermo_freq": 2000,
        "timestep": 1,
        "anneal_heat_start": 300,
        "anneal_heat_end": 600,
        "anneal_heat_steps": 100000,
        "anneal_cool_low": 300,
        "anneal_cool_step": 25,
        "anneal_cool_steps": 1000000,
        "first_eq_temp": 300,
        "first_eq_steps": 4000000,
        "first_eq_loop_time": 25000,
        "final_eq_temp": 300,
        "final_eq_steps": 5000000,
        "final_eq_loop_time": 25000,
        "poly1_monomers": 2999,
        "poly1_xlinkd": 0.99,
        "poly1_temp": 300,
        "poly1_prob": 0.2,
        "poly1_totaltime": 1000000,
        "poly1_loop_time": 20000,
        "poly1_seed": "",
        "poly2_monomers": 2999,
        "poly2_xlinkd": 0.99,
        "poly2_temp": 650,
        "poly2_prob": 0.2,
        "poly2_totaltime": 1000000,
        "poly2_loop_time": 20000,
        "poly2_seed": "",
        "poly2_cool_start": 650,
        "poly2_cool_end": 300,
        "poly2_cool_steps": 100000,
    },
    "analysis": {
        "dataset": "",
        "x_column": "",
        "y_column": "",
        "group_column": "",
        "chart_type": "line",
    },
}


def deep_merge(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)  # type: ignore[arg-type]
        else:
            merged[key] = value
    return merged


def load_config() -> dict[str, object]:
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG
    try:
        loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid config.json: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ValueError("Invalid config.json: top-level value must be an object")
    return deep_merge(DEFAULT_CONFIG, loaded)


def stage_label(input_name: str) -> str:
    labels = {
        "Polymer_Densify_R1.in": "Densify",
        "Polymer_AN_R1.in": "Anneal",
        "Polymer_ANEq_R1.in": "Equilibrate",
        "Polymer_ANEqPly_R1_1.in": "Polymerize 1",
        "Polymer_ANEqPly_R1_2.in": "Polymerize 2",
        "Polymer_ANEqPlyAN_R1.in": "Post-Poly Anneal",
        "Polymer_ANEqPlyANEq_R1.in": "Final Equilibrate",
    }
    return labels.get(input_name, input_name)


def data_candidates(root: Path = ROOT) -> list[dict[str, object]]:
    files = sorted(root.glob("*.dat.gz"), key=lambda path: (-path.stat().st_mtime, path.name))
    return [
        {
            "name": path.name,
            "size": path.stat().st_size,
            "modified": int(path.stat().st_mtime),
            "isModifiedCopy": path.name.endswith("_M.dat.gz"),
        }
        for path in files
    ]


def generated_artifacts(root: Path = ROOT) -> dict[str, list[str]]:
    return {
        "jobs": sorted(path.name for path in root.glob("*.in.sh")),
        "logs": sorted(path.name for path in root.glob("*.log.lammps")),
        "errors": sorted(path.name for path in root.glob("*.sh.error")),
        "outputs": sorted(path.name for path in root.glob("*.sh.out")),
    }


def parse_csv_value(value: str) -> object:
    value = value.strip()
    if value == "":
        return ""
    try:
        if any(marker in value.lower() for marker in (".", "e")):
            return float(value)
        return int(value)
    except ValueError:
        return value


def analysis_datasets() -> list[dict[str, object]]:
    if not ANALYSIS_ROOT.exists():
        return []

    datasets: list[dict[str, object]] = []
    for path in sorted(ANALYSIS_ROOT.glob("*.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = [
                {key: parse_csv_value(value) for key, value in row.items()}
                for row in reader
            ]
        columns = list(rows[0].keys()) if rows else []
        numeric_columns = [
            column
            for column in columns
            if rows and all(isinstance(row.get(column), (int, float)) for row in rows if row.get(column) != "")
        ]
        datasets.append(
            {
                "id": path.stem,
                "name": path.stem.replace("_", " ").title(),
                "file": path.name,
                "columns": columns,
                "numericColumns": numeric_columns,
                "rowCount": len(rows),
                "rows": rows,
            }
        )
    return datasets


def analysis_summary() -> dict[str, object]:
    return {
        "datasets": analysis_datasets(),
        "analysisRoot": str(ANALYSIS_ROOT),
        "config": load_config(),
    }


def create_dummy_data() -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "make_dummy_data.py"],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=60,
    )
    output = completed.stdout
    if completed.stderr:
        output = f"{output}\n{completed.stderr}".strip()
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "output": output,
        "status": workflow_status(),
        "analysis": analysis_summary(),
    }


def resolve_status_root(run_dir: str | None = None) -> Path:
    if not clean_value(run_dir):
        return ROOT
    candidate = Path(clean_value(run_dir)).expanduser()
    return candidate if candidate.is_absolute() else ROOT / candidate


def workflow_status(start_data: str | None = None, run_dir: str | None = None) -> dict[str, object]:
    status_root = resolve_status_root(run_dir)
    result = workflow.validate(status_root, start_data_override=start_data or None)
    stages = []
    for input_name, walltime in workflow.JOB_RUN_ORDER:
        input_path = status_root / input_name
        output_name = EXPECTED_OUTPUTS.get(input_name)
        output_path = status_root / output_name if output_name else None
        script_path = status_root / f"{input_name}.sh"
        error_path = status_root / f"{input_name}.sh.error"
        stdout_path = status_root / f"{input_name}.sh.out"
        stages.append(
            {
                "label": stage_label(input_name),
                "input": input_name,
                "walltime": walltime,
                "inputExists": input_path.exists(),
                "jobScriptExists": script_path.exists(),
                "output": output_name,
                "outputExists": bool(output_path and output_path.exists()),
                "errorLogExists": error_path.exists(),
                "stdoutLogExists": stdout_path.exists(),
            }
        )

    return {
        "root": str(status_root),
        "ready": not result.missing,
        "missing": result.missing,
        "startData": str(result.start_data),
        "stages": stages,
        "dataCandidates": data_candidates(status_root),
        "artifacts": generated_artifacts(status_root),
        "environment": {
            "LAMMPS_BIN": os.environ.get("LAMMPS_BIN", ""),
            "SLURM_ACCOUNT": os.environ.get("SLURM_ACCOUNT", ""),
            "SLURM_MAIL_USER": os.environ.get("SLURM_MAIL_USER", ""),
            "MPI_COMMAND": os.environ.get("MPI_COMMAND", "mpiexec"),
        },
        "config": load_config(),
    }


def clean_value(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def workflow_env(options: dict[str, object]) -> dict[str, str]:
    env = dict(os.environ)
    for key in ("LAMMPS_BIN", "SLURM_ACCOUNT", "SLURM_MAIL_USER", "MPI_COMMAND"):
        value = clean_value(options.get(key.lower()))
        if value:
            env[key] = value
        elif key in env and key != "MPI_COMMAND":
            env.pop(key)
    if "MPI_COMMAND" not in env:
        env["MPI_COMMAND"] = "mpiexec"
    return env


def run_workflow(action: str, options: dict[str, object]) -> dict[str, object]:
    if action not in {"status", "prepare", "build", "postprocess", "all"}:
        raise ValueError(f"Unsupported action: {action}")

    cmd = [sys.executable, "workflow.py", action]
    if clean_value(options.get("start_data")):
        cmd += ["--start-data", clean_value(options.get("start_data"))]
    if clean_value(options.get("final_data")):
        cmd += ["--final-data", clean_value(options.get("final_data"))]
    if clean_value(options.get("queue")):
        cmd += ["--queue", clean_value(options.get("queue"))]
    if clean_value(options.get("cores")):
        cmd += ["--cores", clean_value(options.get("cores"))]
    if clean_value(options.get("nodes")):
        cmd += ["--nodes", clean_value(options.get("nodes"))]
    if clean_value(options.get("run_dir")):
        cmd += ["--run-dir", clean_value(options.get("run_dir"))]
    if clean_value(options.get("run_name")):
        cmd += ["--run-name", clean_value(options.get("run_name"))]
    if bool(options.get("poly_same_settings")):
        cmd.append("--poly-same-settings")
    if clean_value(options.get("seed_mode")):
        cmd += ["--seed-mode", clean_value(options.get("seed_mode"))]
    for key, flag in (
        ("target_density", "--target-density"),
        ("densify_temp", "--densify-temp"),
        ("densify_pressure", "--densify-pressure"),
        ("densify_velocity_seed", "--densify-velocity-seed"),
        ("densify_nvt_steps", "--densify-nvt-steps"),
        ("densify_npt_loops", "--densify-npt-loops"),
        ("densify_npt_steps", "--densify-npt-steps"),
        ("densify_rate", "--densify-rate"),
        ("densify_thermo_freq", "--densify-thermo-freq"),
        ("timestep", "--timestep"),
        ("anneal_heat_start", "--anneal-heat-start"),
        ("anneal_heat_end", "--anneal-heat-end"),
        ("anneal_heat_steps", "--anneal-heat-steps"),
        ("anneal_cool_low", "--anneal-cool-low"),
        ("anneal_cool_step", "--anneal-cool-step"),
        ("anneal_cool_steps", "--anneal-cool-steps"),
        ("first_eq_temp", "--first-eq-temp"),
        ("first_eq_steps", "--first-eq-steps"),
        ("first_eq_loop_time", "--first-eq-loop-time"),
        ("final_eq_temp", "--final-eq-temp"),
        ("final_eq_steps", "--final-eq-steps"),
        ("final_eq_loop_time", "--final-eq-loop-time"),
        ("poly1_monomers", "--poly1-monomers"),
        ("poly1_xlinkd", "--poly1-xlinkd"),
        ("poly1_temp", "--poly1-temp"),
        ("poly1_prob", "--poly1-prob"),
        ("poly1_totaltime", "--poly1-totaltime"),
        ("poly1_loop_time", "--poly1-loop-time"),
        ("poly1_seed", "--poly1-seed"),
        ("poly2_monomers", "--poly2-monomers"),
        ("poly2_xlinkd", "--poly2-xlinkd"),
        ("poly2_temp", "--poly2-temp"),
        ("poly2_prob", "--poly2-prob"),
        ("poly2_totaltime", "--poly2-totaltime"),
        ("poly2_loop_time", "--poly2-loop-time"),
        ("poly2_seed", "--poly2-seed"),
        ("poly2_cool_start", "--poly2-cool-start"),
        ("poly2_cool_end", "--poly2-cool-end"),
        ("poly2_cool_steps", "--poly2-cool-steps"),
    ):
        if clean_value(options.get(key)):
            cmd += [flag, clean_value(options.get(key))]
    if bool(options.get("submit")):
        cmd.append("--submit")
    if bool(options.get("dry_run")):
        cmd.append("--dry-run")

    completed = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=workflow_env(options),
        text=True,
        capture_output=True,
        timeout=300,
    )
    output = completed.stdout
    if completed.stderr:
        output = f"{output}\n{completed.stderr}".strip()

    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "command": " ".join(cmd),
        "output": output,
        "status": workflow_status(clean_value(options.get("start_data")), clean_value(options.get("run_dir"))),
    }


class WorkflowHandler(BaseHTTPRequestHandler):
    server_version = "PolymerWorkflowWeb/1.0"

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")

    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_static(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        content_type, _ = mimetypes.guess_type(path.name)
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY_BYTES:
            raise ValueError("Request body is too large")
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            try:
                query = parse_qs(parsed.query)
                start_data = query.get("start_data", [""])[0]
                run_dir = query.get("run_dir", [""])[0]
                self.send_json(workflow_status(start_data, run_dir))
            except Exception as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if parsed.path == "/api/analysis":
            try:
                self.send_json(analysis_summary())
            except Exception as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return


        if parsed.path in {"/", "/index.html"}:
            self.send_static(WEB_ROOT / "index.html")
            return

        requested = (WEB_ROOT / parsed.path.lstrip("/")).resolve()
        if WEB_ROOT.resolve() not in requested.parents and requested != WEB_ROOT.resolve():
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return
        self.send_static(requested)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/run":
            if parsed.path == "/api/dummy-data":
                try:
                    self.send_json(create_dummy_data())
                except Exception as exc:
                    self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        try:
            payload = self.read_json_body()
            action = clean_value(payload.get("action"))
            options = payload.get("options", {})
            if not isinstance(options, dict):
                raise ValueError("options must be an object")
            self.send_json(run_workflow(action, options))
        except subprocess.TimeoutExpired:
            self.send_json({"error": "Workflow action timed out"}, HTTPStatus.REQUEST_TIMEOUT)
        except Exception as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local polymer workflow web interface.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), WorkflowHandler)
    print(f"Polymer workflow web UI: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
