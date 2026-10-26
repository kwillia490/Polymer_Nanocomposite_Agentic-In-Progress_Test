from __future__ import annotations

import argparse
from datetime import datetime
import gzip
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


STAGE_SPECS = [
    ("densify", "*_Densify_*.in", "Polymer_Densify_R1.in", "96:00:00"),
    ("an", "*_AN_*.in", "Polymer_AN_R1.in", "168:00:00"),
    ("aneq", "*_ANEq_*.in", "Polymer_ANEq_R1.in", "96:00:00"),
    ("aneqply_1", "*_ANEqPly_*_1.in", "Polymer_ANEqPly_R1_1.in", "96:00:00"),
    ("aneqply_2", "*_ANEqPly_*_2.in", "Polymer_ANEqPly_R1_2.in", "96:00:00"),
    ("aneqplyan", "*_ANEqPlyAN_*.in", "Polymer_ANEqPlyAN_R1.in", "168:00:00"),
    ("aneqplyaneq", "*_ANEqPlyANEq_*.in", "Polymer_ANEqPlyANEq_R1.in", "96:00:00"),
]

POLYMERIZATION_STAGES = {
    "poly1": "Polymer_ANEqPly_R1_1.in",
    "poly2": "Polymer_ANEqPly_R1_2.in",
}

SEED_VARIABLES = {
    "Polymer_ANEqPly_R1_1.in": ["prob_seed"],
    "Polymer_ANEqPly_R1_2.in": ["prob_seed"],
}

RUN_BUNDLE_EXCLUDES = {".git", "runs", "__pycache__"}

GENERATOR_STEPS = [
    ("YM_Generator.sh", ["bash", "YM_Generator.sh"]),
    ("Sh_Generator.sh", ["bash", "Sh_Generator.sh"]),
    ("PrePoly_BK_Generator.sh", ["bash", "PrePoly_BK_Generator.sh"]),
    ("BK_Generator.sh", ["bash", "BK_Generator.sh"]),
    ("Generate_RNEMD_TC_Scripts.py", ["python3", "Generate_RNEMD_TC_Scripts.py"]),
]

JOB_RUN_ORDER = [
    ("Polymer_Densify_R1.in", "96:00:00"),
    ("Polymer_AN_R1.in", "168:00:00"),
    ("Polymer_ANEq_R1.in", "96:00:00"),
    ("Polymer_ANEqPly_R1_1.in", "96:00:00"),
    ("Polymer_ANEqPly_R1_2.in", "96:00:00"),
    ("Polymer_ANEqPlyAN_R1.in", "168:00:00"),
    ("Polymer_ANEqPlyANEq_R1.in", "96:00:00"),
]


@dataclass
class ValidationResult:
    root: Path
    stage_matches: dict[str, list[Path]]
    densify_file: Path
    start_data: Path
    missing: list[str]


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def run(
    cmd: list[str],
    cwd: Path,
    *,
    env: dict[str, str] | None = None,
    dry_run: bool = False,
    capture: bool = False,
) -> str:
    pretty = " ".join(cmd)
    if dry_run:
        print(f"[dry-run] {pretty}")
        return ""

    print(f"[run] {pretty}")
    completed = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
    )
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if completed.returncode != 0:
        if completed.stderr:
            eprint(completed.stderr.rstrip())
        raise SystemExit(completed.returncode)
    if completed.stderr:
        eprint(completed.stderr.rstrip())
    if capture:
        return completed.stdout
    return ""


def collect_matches(root: Path, pattern: str) -> list[Path]:
    return sorted(root.glob(pattern))


def pick_one(paths: list[Path], preferred_name: str | None = None) -> Path:
    if not paths:
        raise ValueError("no paths available")
    if preferred_name:
        for path in paths:
            if path.name == preferred_name:
                return path
    return paths[0]


def find_densify_input(root: Path) -> Path:
    matches = collect_matches(root, "*_Densify_*.in")
    if not matches:
        matches = collect_matches(root, "*_Densify_*.IN")
    if not matches:
        raise FileNotFoundError("No Densify input file found.")
    return pick_one(matches, "Polymer_Densify_R1.in")


def read_data_target(densify_file: Path) -> str:
    variables = {}
    for line in densify_file.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        variable_match = re.match(r"^variable\s+(\S+)\s+string\s+(\S+)", stripped)
        if variable_match:
            variables[variable_match.group(1)] = variable_match.group(2)
            continue

        match = re.match(r"^read_data\s+(\S+)", stripped)
        if not match:
            continue
        target = match.group(1)
        variable_ref = re.fullmatch(r"\$\{([^}]+)\}", target)
        if variable_ref and variable_ref.group(1) in variables:
            return variables[variable_ref.group(1)]
        return target
    raise ValueError(f"Could not find read_data in {densify_file.name}")


def resolve_path(root: Path, target: str) -> Path:
    target_path = Path(target)
    if target_path.is_absolute():
        return target_path
    return root / target_path


def timestamp_run_name() -> str:
    return f"Polymer_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def random_lammps_seed() -> int:
    return secrets.randbelow(899999999) + 100000000


def unique_seed(used: set[int], requested: int | None = None) -> int:
    if requested is not None:
        if requested in used:
            raise ValueError(f"Seed values must be different across steps: {requested} is repeated")
        used.add(requested)
        return requested
    while True:
        seed = random_lammps_seed()
        if seed not in used:
            used.add(seed)
            return seed


def run_bundle_path(root: Path, runs_dir: str, run_name: str | None, run_dir: str | None) -> Path:
    if run_dir:
        candidate = Path(run_dir).expanduser()
        return candidate if candidate.is_absolute() else root / candidate
    return root / runs_dir / (run_name or timestamp_run_name())


def copy_portable_bundle(source_root: Path, bundle_root: Path, *, dry_run: bool = False) -> None:
    if dry_run:
        print(f"[dry-run] create portable run bundle: {bundle_root}")
        return
    if bundle_root.exists() and any(bundle_root.iterdir()):
        raise FileExistsError(f"Run bundle already exists and is not empty: {bundle_root}")
    bundle_root.parent.mkdir(parents=True, exist_ok=True)

    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored = {name for name in names if name in RUN_BUNDLE_EXCLUDES}
        try:
            current = Path(directory).resolve()
            for name in names:
                if (current / name).resolve() == bundle_root.resolve():
                    ignored.add(name)
        except OSError:
            return ignored
        return ignored

    shutil.copytree(source_root, bundle_root, ignore=ignore, dirs_exist_ok=True)


def replace_lammps_variable(path: Path, variable: str, value: object) -> None:
    pattern = re.compile(rf"^(\s*variable\s+{re.escape(variable)}\s+equal\s+)(\S+)(.*)$")
    lines = path.read_text().splitlines()
    replaced = False
    next_lines = []
    for line in lines:
        match = pattern.match(line)
        if match:
            next_lines.append(f"{match.group(1)}{value}{match.group(3)}")
            replaced = True
        else:
            next_lines.append(line)
    if not replaced:
        raise ValueError(f"Could not find LAMMPS variable '{variable}' in {path.name}")
    path.write_text("\n".join(next_lines) + "\n")


def replace_lammps_string_variable(path: Path, variable: str, value: object) -> None:
    pattern = re.compile(rf"^(\s*variable\s+{re.escape(variable)}\s+string\s+)(\S+)(.*)$")
    lines = path.read_text().splitlines()
    replaced = False
    next_lines = []
    for line in lines:
        match = pattern.match(line)
        if match:
            next_lines.append(f"{match.group(1)}{value}{match.group(3)}")
            replaced = True
        else:
            next_lines.append(line)
    if not replaced:
        raise ValueError(f"Could not find LAMMPS string variable '{variable}' in {path.name}")
    path.write_text("\n".join(next_lines) + "\n")


def replace_lammps_loop_variable(path: Path, variable: str, value: object) -> None:
    pattern = re.compile(rf"^(\s*variable\s+{re.escape(variable)}\s+loop\s+)(\S+)(.*)$")
    lines = path.read_text().splitlines()
    replaced = False
    next_lines = []
    for line in lines:
        match = pattern.match(line)
        if match:
            next_lines.append(f"{match.group(1)}{value}{match.group(3)}")
            replaced = True
        else:
            next_lines.append(line)
    if not replaced:
        raise ValueError(f"Could not find LAMMPS loop variable '{variable}' in {path.name}")
    path.write_text("\n".join(next_lines) + "\n")


def replace_regex_once(path: Path, pattern: str, replacement: str, label: str) -> None:
    text = path.read_text()
    next_text, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"Could not update {label} in {path.name}")
    path.write_text(next_text)


def maybe_replace_lammps_variable(path: Path, variable: str, value: object | None) -> None:
    if value is not None:
        replace_lammps_variable(path, variable, value)


def maybe_replace_regex(path: Path, pattern: str, replacement: str, label: str, enabled: bool) -> None:
    if enabled:
        replace_regex_once(path, pattern, replacement, label)


def copy_start_data_override(source_root: Path, bundle_root: Path, start_data: str | None) -> str | None:
    if not start_data:
        return None
    source = resolve_path(source_root, start_data)
    if not source.exists():
        raise FileNotFoundError(f"Starting data file not found: {source}")
    target = bundle_root / source.name
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    replace_lammps_string_variable(bundle_root / "Polymer_Densify_R1.in", "data", target.name)
    return target.name


def compact_number(value: object) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def parameterize_densify_input(
    bundle_root: Path,
    args: argparse.Namespace,
    seed_record: dict[str, int],
    used_seeds: set[int],
) -> dict[str, object]:
    path = bundle_root / "Polymer_Densify_R1.in"
    if not path.exists():
        raise FileNotFoundError(f"Missing densify input in run bundle: {path}")

    maybe_replace_lammps_variable(path, "target_density", args.target_density)
    maybe_replace_lammps_variable(path, "thermofreq", args.densify_thermo_freq)
    maybe_replace_lammps_variable(path, "velocity_angperns", args.densify_rate)
    if args.timestep is not None:
        replace_regex_once(
            path,
            r"^(\s*timestep\s+)\S+.*$",
            rf"\g<1>{compact_number(args.timestep)}",
            "densify timestep",
        )

    velocity_seed = args.densify_velocity_seed
    if velocity_seed is not None or args.seed_mode == "auto":
        velocity_seed = unique_seed(used_seeds, velocity_seed)
        seed_record["Polymer_Densify_R1.in:velocity_seed"] = velocity_seed

    if args.densify_temp is not None or velocity_seed is not None:
        temp = compact_number(args.densify_temp if args.densify_temp is not None else 300)
        seed = velocity_seed if velocity_seed is not None else 9735874
        replace_regex_once(
            path,
            r"^velocity\s+all\s+create\s+\S+\s+\S+.*$",
            f"velocity all create {temp} {seed}",
            "densify velocity create",
        )

    if args.densify_temp is not None or args.densify_nvt_steps is not None:
        temp = compact_number(args.densify_temp if args.densify_temp is not None else 300)
        replace_regex_once(
            path,
            r"^fix\s+1\s+all\s+nvt\s+temp\s+\S+\s+\S+\s+1000$",
            f"fix 1 all nvt temp {temp} {temp} 1000",
            "densify NVT temperature",
        )
        if args.densify_nvt_steps is not None:
            replace_regex_once(
                path,
                r"^run\s+100000$",
                f"run {args.densify_nvt_steps}",
                "densify NVT steps",
            )

    if args.densify_temp is not None or args.densify_pressure is not None:
        temp = compact_number(args.densify_temp if args.densify_temp is not None else 300)
        pressure = compact_number(args.densify_pressure if args.densify_pressure is not None else 1.0)
        replace_regex_once(
            path,
            r"^fix\s+1\s+all\s+npt\s+temp\s+\S+\s+\S+\s+100\s+iso\s+\S+\s+\S+\s+1000$",
            f"fix 1 all npt temp {temp} {temp} 100 iso {pressure} {pressure} 1000",
            "densify NPT",
        )

    if args.densify_npt_loops is not None:
        replace_lammps_loop_variable(path, "npt", args.densify_npt_loops)
    if args.densify_npt_steps is not None:
        replace_regex_once(
            path,
            r"^run\s+20000\s+# 20 ps$",
            f"run {args.densify_npt_steps} # densify NPT chunk",
            "densify NPT chunk",
        )

    return {
        "target_density": args.target_density,
        "temperature": args.densify_temp,
        "pressure": args.densify_pressure,
        "nvt_steps": args.densify_nvt_steps,
        "npt_loops": args.densify_npt_loops,
        "npt_steps": args.densify_npt_steps,
        "deformation_rate_ang_per_ns": args.densify_rate,
        "thermo_freq": args.densify_thermo_freq,
        "timestep": args.timestep,
    }


def anneal_schedule_lines(
    myid_suffix: str,
    heat_start: float,
    heat_end: float,
    heat_steps: int,
    cool_low: float,
    cool_step: float,
    cool_steps: int,
) -> list[str]:
    lines = [
        "fix 2 all balance 100000 1.05 shift xyz 20 1.05",
        f"fix 1 all nvt temp {compact_number(heat_start)} {compact_number(heat_end)} 1000",
        f"run {heat_steps} # heat ramp",
        "unfix 1",
        "",
    ]

    current = heat_end
    while current - cool_step >= cool_low:
        next_temp = current - cool_step
        lines.extend(
            [
                f"fix 1 all nvt temp {compact_number(current)} {compact_number(next_temp)} 1000",
                f"run {cool_steps} # cooling segment",
                "unfix 1",
                f"write_data ${{myid}}_{compact_number(next_temp)}K.dat",
                "",
            ]
        )
        current = next_temp
    lines.append(f"write_data ${{myid}}{myid_suffix}.dat")
    return lines


def replace_anneal_schedule(
    path: Path,
    heat_start: float,
    heat_end: float,
    heat_steps: int,
    cool_low: float,
    cool_step: float,
    cool_steps: int,
) -> None:
    text = path.read_text()
    pattern = re.compile(
        r"fix 2 all balance 100000 1\.05 shift xyz 20 1\.05\n.*?write_data \$\{myid\}\.dat",
        flags=re.DOTALL,
    )
    replacement = "\n".join(
        anneal_schedule_lines("", heat_start, heat_end, heat_steps, cool_low, cool_step, cool_steps)
    )
    next_text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise ValueError(f"Could not replace anneal schedule in {path.name}")
    path.write_text(next_text)


def parameterize_anneal_inputs(bundle_root: Path, args: argparse.Namespace) -> dict[str, object]:
    changed = any(
        value is not None
        for value in (
            args.anneal_heat_start,
            args.anneal_heat_end,
            args.anneal_heat_steps,
            args.anneal_cool_low,
            args.anneal_cool_step,
            args.anneal_cool_steps,
        )
    )
    if not changed:
        return {}

    heat_start = args.anneal_heat_start if args.anneal_heat_start is not None else 300
    heat_end = args.anneal_heat_end if args.anneal_heat_end is not None else 600
    heat_steps = args.anneal_heat_steps if args.anneal_heat_steps is not None else 100000
    cool_low = args.anneal_cool_low if args.anneal_cool_low is not None else 300
    cool_step = args.anneal_cool_step if args.anneal_cool_step is not None else 25
    cool_steps = args.anneal_cool_steps if args.anneal_cool_steps is not None else 1000000
    if cool_step <= 0:
        raise ValueError("Anneal cooling step must be greater than zero")
    if heat_end < cool_low:
        raise ValueError("Anneal high temperature must be at or above cooling low temperature")

    for input_name in ("Polymer_AN_R1.in", "Polymer_ANEqPlyAN_R1.in"):
        replace_anneal_schedule(
            bundle_root / input_name,
            heat_start=heat_start,
            heat_end=heat_end,
            heat_steps=heat_steps,
            cool_low=cool_low,
            cool_step=cool_step,
            cool_steps=cool_steps,
        )

    return {
        "heat_start": heat_start,
        "heat_end": heat_end,
        "heat_steps": heat_steps,
        "cool_low": cool_low,
        "cool_step": cool_step,
        "cool_steps": cool_steps,
    }


def parameterize_equilibration_inputs(bundle_root: Path, args: argparse.Namespace) -> dict[str, object]:
    records = {}
    for input_name, temp_arg, steps_arg, loop_arg in (
        ("Polymer_ANEq_R1.in", args.first_eq_temp, args.first_eq_steps, args.first_eq_loop_time),
        ("Polymer_ANEqPlyANEq_R1.in", args.final_eq_temp, args.final_eq_steps, args.final_eq_loop_time),
    ):
        path = bundle_root / input_name
        if temp_arg is not None:
            replace_regex_once(
                path,
                r"^(fix 1 all npt temp )\S+\s+\S+(\s+1000\s+(?:iso|aniso)\s+\S+\s+\S+\s+1000)$",
                rf"\g<1>{compact_number(temp_arg)} {compact_number(temp_arg)}\g<2>",
                f"{input_name} NPT temperature",
            )
        if loop_arg is not None:
            replace_lammps_variable(path, "loop_time", f"$({loop_arg})")
        if steps_arg is not None:
            replace_regex_once(
                path,
                r"^(variable run_loop_npt loop \$\()\d+(/v_loop_time\))$",
                rf"\g<1>{steps_arg}\g<2>",
                f"{input_name} total equilibration steps",
            )
        records[input_name] = {
            "temperature": temp_arg,
            "total_steps": steps_arg,
            "loop_time": loop_arg,
        }
    return records


def stage_settings(args: argparse.Namespace) -> dict[str, dict[str, object | None]]:
    poly1 = {
        "monomers": args.poly1_monomers,
        "target_conversion": args.poly1_xlinkd,
        "temperature": args.poly1_temp,
        "probability": args.poly1_prob,
        "totaltime": args.poly1_totaltime,
        "loop_time": args.poly1_loop_time,
        "seed": args.poly1_seed,
    }
    if args.poly_same_settings:
        poly2 = dict(poly1)
        poly2["seed"] = args.poly2_seed
    else:
        poly2 = {
            "monomers": args.poly2_monomers,
            "target_conversion": args.poly2_xlinkd,
            "temperature": args.poly2_temp,
            "probability": args.poly2_prob,
            "totaltime": args.poly2_totaltime,
            "loop_time": args.poly2_loop_time,
            "seed": args.poly2_seed,
        }
    return {"poly1": poly1, "poly2": poly2}


def parameterize_polymerization_inputs(
    bundle_root: Path,
    args: argparse.Namespace,
    *,
    used_seeds: set[int] | None = None,
    seed_record: dict[str, int] | None = None,
) -> tuple[dict[str, object], dict[str, int]]:
    settings = stage_settings(args)
    used_seeds = used_seeds if used_seeds is not None else set()
    seed_record = seed_record if seed_record is not None else {}

    for stage_key, input_name in POLYMERIZATION_STAGES.items():
        path = bundle_root / input_name
        if not path.exists():
            raise FileNotFoundError(f"Missing polymerization input in run bundle: {path}")
        stage = settings[stage_key]
        if stage["monomers"] is not None:
            replace_lammps_variable(path, "maxbond", stage["monomers"])
        if stage["target_conversion"] is not None:
            replace_lammps_variable(path, "xlinkd", stage["target_conversion"])
        if stage["temperature"] is not None:
            replace_lammps_variable(path, "temp", stage["temperature"])
        if stage["probability"] is not None:
            replace_lammps_variable(path, "prob", stage["probability"])
        if stage["totaltime"] is not None:
            replace_lammps_variable(path, "totaltime", stage["totaltime"])
        if stage["loop_time"] is not None:
            replace_lammps_variable(path, "loop_time", f"$({stage['loop_time']})")

        explicit_seed = stage["seed"]
        if explicit_seed is not None or args.seed_mode == "auto":
            seed = unique_seed(used_seeds, int(explicit_seed) if explicit_seed is not None else None)
            replace_lammps_variable(path, "prob_seed", seed)
            seed_record[f"{input_name}:prob_seed"] = seed

    if (
        args.poly2_cool_start is not None
        or args.poly2_cool_end is not None
        or args.poly2_cool_steps is not None
    ):
        path = bundle_root / "Polymer_ANEqPly_R1_2.in"
        start = compact_number(args.poly2_cool_start if args.poly2_cool_start is not None else 650)
        end = compact_number(args.poly2_cool_end if args.poly2_cool_end is not None else 300)
        steps = args.poly2_cool_steps if args.poly2_cool_steps is not None else 100000
        replace_regex_once(
            path,
            r"^fix 1 all npt temp \S+ \S+ 1000 aniso 1\.0 1\.0 1000$",
            f"fix 1 all npt temp {start} {end} 1000 aniso 1.0 1.0 1000",
            "stage 2 cool-down",
        )
        replace_regex_once(
            path,
            r"^run 100000 # 100 ps$",
            f"run {steps} # stage 2 cool-down",
            "stage 2 cool-down steps",
        )

    config_record = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_root": str(args.source_root),
        "run_root": str(bundle_root),
        "seed_mode": args.seed_mode,
        "poly_same_settings": args.poly_same_settings,
        "polymerization": settings,
        "stage2_cooldown": {
            "start": args.poly2_cool_start,
            "end": args.poly2_cool_end,
            "steps": args.poly2_cool_steps,
        },
    }
    return config_record, seed_record


def parameterize_workflow_inputs(
    bundle_root: Path,
    args: argparse.Namespace,
) -> tuple[dict[str, object], dict[str, int]]:
    used_seeds = set()
    seed_record = {}
    start_data_name = copy_start_data_override(args.source_root, bundle_root, args.start_data)
    densify = parameterize_densify_input(bundle_root, args, seed_record, used_seeds)
    anneal = parameterize_anneal_inputs(bundle_root, args)
    equilibration = parameterize_equilibration_inputs(bundle_root, args)
    poly_config, poly_seeds = parameterize_polymerization_inputs(
        bundle_root,
        args,
        used_seeds=used_seeds,
        seed_record=seed_record,
    )
    seed_record.update(poly_seeds)
    poly_config.update(
        {
            "start_data": start_data_name,
            "densify": densify,
            "anneal": anneal,
            "equilibration": equilibration,
        }
    )
    return poly_config, seed_record


def write_run_metadata(
    bundle_root: Path,
    config_record: dict[str, object],
    seed_record: dict[str, int],
    dry_run: bool,
) -> None:
    if dry_run:
        print("[dry-run] write run_config.json and seeds.json")
        return
    (bundle_root / "run_config.json").write_text(json.dumps(config_record, indent=2) + "\n")
    (bundle_root / "seeds.json").write_text(json.dumps(seed_record, indent=2) + "\n")


def prepare_run_bundle(root: Path, args: argparse.Namespace) -> Path:
    bundle_root = run_bundle_path(root, args.runs_dir, args.run_name, args.run_dir).resolve()
    if args.run_dir and bundle_root.exists() and any(bundle_root.iterdir()):
        required_inputs = [bundle_root / input_name for input_name, _ in JOB_RUN_ORDER]
        missing_inputs = [path.name for path in required_inputs if not path.exists()]
        if missing_inputs:
            raise FileExistsError(
                f"Run directory exists but is not an empty folder or prepared bundle: {bundle_root}. "
                f"Missing workflow inputs: {', '.join(missing_inputs)}"
            )
        print(f"Using existing run bundle: {bundle_root}")
    else:
        copy_portable_bundle(root, bundle_root, dry_run=args.dry_run)
        print(f"Run bundle: {bundle_root}")
    if not args.dry_run:
        args.source_root = root
        config_record, seed_record = parameterize_workflow_inputs(bundle_root, args)
        write_run_metadata(bundle_root, config_record, seed_record, dry_run=args.dry_run)
        if seed_record:
            print("Random seed assignments:")
            for label, seed in seed_record.items():
                print(f"  - {label}: {seed}")
        return bundle_root
    print("[dry-run] workflow parameter updates would be applied inside the run bundle")
    return root


def validate(root: Path, start_data_override: str | None = None) -> ValidationResult:
    stage_matches = {}
    missing = []

    for stage_name, pattern, default_name, _ in STAGE_SPECS:
        matches = collect_matches(root, pattern)
        if not matches:
            matches = collect_matches(root, pattern.replace(".in", ".IN"))
        preferred = pick_one(matches, default_name) if matches else None
        stage_matches[stage_name] = [preferred] if preferred else []
        if not matches:
            missing.append(pattern)

    densify_file = find_densify_input(root)
    start_data_name = start_data_override or read_data_target(densify_file)
    start_data = resolve_path(root, start_data_name)
    if not start_data.exists():
        missing.append(f"start data file: {start_data_name}")

    return ValidationResult(
        root=root,
        stage_matches=stage_matches,
        densify_file=densify_file,
        start_data=start_data,
        missing=missing,
    )


def print_validation_report(result: ValidationResult) -> None:
    print("Workflow status")
    print(f"Project root: {result.root}")
    print("Stage inputs:")
    for stage_name, pattern, _, _ in STAGE_SPECS:
        matches = result.stage_matches.get(stage_name, [])
        if matches:
            print(f"  - {stage_name}: {matches[0].name}")
        else:
            print(f"  - {stage_name}: missing ({pattern})")
    print(f"Starting data file: {result.start_data}")
    if result.missing:
        print("Status: not ready")
        for item in result.missing:
            print(f"  - missing: {item}")
        return
    print("Status: ready")


def pick_final_data_file(root: Path, explicit: str | None = None) -> Path:
    if explicit:
        candidate = resolve_path(root, explicit)
        if not candidate.exists():
            raise FileNotFoundError(f"Final data file not found: {candidate}")
        return candidate

    candidates = [
        path
        for path in root.glob("*.dat.gz")
        if not path.name.endswith("_M.dat.gz")
    ]
    if not candidates:
        raise FileNotFoundError("No .dat.gz files found.")

    def score(path: Path) -> tuple[int, float, str]:
        name = path.name
        if "ANEqPlyANEq" in name:
            priority = 0
        elif "ANEqPlyAN" in name:
            priority = 1
        elif "ANEqPly" in name:
            priority = 2
        elif "ANEq" in name:
            priority = 3
        elif "_AN_" in name or name.startswith("Polymer_AN_"):
            priority = 4
        else:
            priority = 9
        return (priority, -path.stat().st_mtime, name)

    return sorted(candidates, key=score)[0]


def comment_bond_coeffs(input_file: Path, output_file: Path) -> None:
    in_section = False
    with gzip.open(input_file, "rt") as fin, gzip.open(output_file, "wt") as fout:
        for line in fin:
            stripped = line.strip()
            if stripped.startswith("Bond Coeffs"):
                in_section = True
                fout.write(line if line.startswith("#") else f"# {line}")
                continue

            if in_section:
                if not stripped:
                    fout.write(line)
                    continue
                if stripped[0].isalpha():
                    in_section = False
                    fout.write(line)
                    continue
                fout.write(line if line.startswith("#") else f"# {line}")
                continue

            fout.write(line)


def create_modified_data_copy(root: Path, final_data: Path) -> Path:
    output_file = final_data.with_name(final_data.name[:-7] + "_M.dat.gz")
    comment_bond_coeffs(final_data, output_file)
    return output_file


def generate_job_scripts(root: Path, queue: str, cores: int, nodes: int, dry_run: bool) -> None:
    for input_name, walltime in JOB_RUN_ORDER:
        input_path = root / input_name
        if not input_path.exists():
            raise FileNotFoundError(f"Missing input file: {input_path}")

        cmd = [
            "bash",
            "qlammps.sh",
            "-c",
            str(cores),
            "-n",
            str(nodes),
            "-w",
            walltime,
            "-q",
            queue,
            "-f",
            input_name,
        ]
        run(cmd, cwd=root, dry_run=dry_run)


def submit_main_chain(root: Path, dry_run: bool) -> None:
    previous_job_id = None
    submitted = []

    for input_name, _ in JOB_RUN_ORDER:
        script = f"{input_name}.sh"
        script_path = root / script
        if not script_path.exists():
            raise FileNotFoundError(f"Missing generated job script: {script_path}")

        cmd = ["sbatch"]
        if previous_job_id:
            cmd.append(f"--dependency=afterok:{previous_job_id}")
        cmd.append(script)

        output = run(cmd, cwd=root, dry_run=dry_run, capture=True)
        if dry_run:
            previous_job_id = "<job-id>"
            continue

        match = re.search(r"Submitted batch job\s+(\d+)", output)
        if not match:
            raise RuntimeError(f"Could not parse sbatch job id from output: {output!r}")

        previous_job_id = match.group(1)
        submitted.append((input_name, previous_job_id))

    if submitted:
        print("Submitted main workflow chain:")
        for input_name, job_id in submitted:
            print(f"  - {input_name}: {job_id}")


def run_generators(root: Path, submit: bool, dry_run: bool) -> None:
    env = dict(os.environ)
    env["SUBMIT_JOBS"] = "1" if submit else "0"
    for label, cmd in GENERATOR_STEPS:
        if not (root / label).exists():
            raise FileNotFoundError(f"Missing generator: {label}")
        run(cmd, cwd=root, env=env, dry_run=dry_run)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and orchestrate the polymer nanocomposite workflow."
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["status", "prepare", "build", "postprocess", "all"],
        default="status",
        help="Workflow action to run.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Project root directory that contains the workflow files.",
    )
    parser.add_argument(
        "--start-data",
        default=None,
        help="Override the starting data file referenced by the Densify input.",
    )
    parser.add_argument(
        "--final-data",
        default=None,
        help="Override the final .dat.gz file used to create the _M copy.",
    )
    parser.add_argument(
        "--queue",
        default="standard",
        help="Queue name used when generating scheduler scripts.",
    )
    parser.add_argument(
        "--cores",
        type=int,
        default=128,
        help="Number of cores to request per job.",
    )
    parser.add_argument(
        "--nodes",
        type=int,
        default=1,
        help="Number of nodes to request per job.",
    )
    parser.add_argument(
        "--runs-dir",
        default="runs",
        help="Directory under the project root where portable run bundles are created.",
    )
    parser.add_argument(
        "--run-name",
        default=None,
        help="Name for a new run bundle. Defaults to Polymer_run_YYYYMMDD_HHMMSS.",
    )
    parser.add_argument(
        "--run-dir",
        default=None,
        help="Use an existing run bundle, or create this exact run bundle path if it does not exist.",
    )
    parser.add_argument(
        "--poly-same-settings",
        action="store_true",
        help="Use stage 1 monomer, temperature, and probability settings for polymerization stage 2.",
    )
    parser.add_argument("--target-density", type=float, default=None, help="Densification target density in g/cc.")
    parser.add_argument("--densify-temp", type=float, default=None, help="Densification temperature in K.")
    parser.add_argument("--densify-pressure", type=float, default=None, help="Densification pressure in atm.")
    parser.add_argument("--densify-velocity-seed", type=int, default=None, help="Velocity seed for the densification stage.")
    parser.add_argument("--densify-nvt-steps", type=int, default=None, help="Densification NVT run length in steps.")
    parser.add_argument("--densify-npt-loops", type=int, default=None, help="Number of densification NPT loop chunks.")
    parser.add_argument("--densify-npt-steps", type=int, default=None, help="Steps per densification NPT loop chunk.")
    parser.add_argument("--densify-rate", type=float, default=None, help="Densification deformation rate in Angstrom/ns.")
    parser.add_argument("--densify-thermo-freq", type=int, default=None, help="Densification thermo output frequency.")
    parser.add_argument("--timestep", type=float, default=None, help="Main workflow timestep in fs where safely parameterized.")
    parser.add_argument("--anneal-heat-start", type=float, default=None, help="Anneal heat-ramp starting temperature in K.")
    parser.add_argument("--anneal-heat-end", type=float, default=None, help="Anneal high temperature in K.")
    parser.add_argument("--anneal-heat-steps", type=int, default=None, help="Anneal heat-ramp length in steps.")
    parser.add_argument("--anneal-cool-low", type=float, default=None, help="Anneal final cooling temperature in K.")
    parser.add_argument("--anneal-cool-step", type=float, default=None, help="Anneal cooling temperature decrement in K.")
    parser.add_argument("--anneal-cool-steps", type=int, default=None, help="Steps per anneal cooling segment.")
    parser.add_argument("--first-eq-temp", type=float, default=None, help="First equilibration NPT temperature in K.")
    parser.add_argument("--first-eq-steps", type=int, default=None, help="First equilibration total NPT steps.")
    parser.add_argument("--first-eq-loop-time", type=int, default=None, help="First equilibration loop chunk size.")
    parser.add_argument("--final-eq-temp", type=float, default=None, help="Final equilibration NPT temperature in K.")
    parser.add_argument("--final-eq-steps", type=int, default=None, help="Final equilibration total NPT steps.")
    parser.add_argument("--final-eq-loop-time", type=int, default=None, help="Final equilibration loop chunk size.")
    parser.add_argument("--poly1-monomers", type=int, default=None, help="Stage 1 polymerization monomer/maxbond count.")
    parser.add_argument("--poly1-xlinkd", type=float, default=None, help="Stage 1 target conversion fraction.")
    parser.add_argument("--poly1-temp", type=float, default=None, help="Stage 1 polymerization temperature.")
    parser.add_argument("--poly1-prob", type=float, default=None, help="Stage 1 polymerization probability.")
    parser.add_argument("--poly1-totaltime", type=int, default=None, help="Stage 1 polymerization total time in fs.")
    parser.add_argument("--poly1-loop-time", type=int, default=None, help="Stage 1 polymerization loop chunk size.")
    parser.add_argument("--poly1-seed", type=int, default=None, help="Stage 1 polymerization probability seed.")
    parser.add_argument("--poly2-monomers", type=int, default=None, help="Stage 2 polymerization monomer/maxbond count.")
    parser.add_argument("--poly2-xlinkd", type=float, default=None, help="Stage 2 target conversion fraction.")
    parser.add_argument("--poly2-temp", type=float, default=None, help="Stage 2 polymerization temperature.")
    parser.add_argument("--poly2-prob", type=float, default=None, help="Stage 2 polymerization probability.")
    parser.add_argument("--poly2-totaltime", type=int, default=None, help="Stage 2 polymerization total time in fs.")
    parser.add_argument("--poly2-loop-time", type=int, default=None, help="Stage 2 polymerization loop chunk size.")
    parser.add_argument("--poly2-seed", type=int, default=None, help="Stage 2 polymerization probability seed.")
    parser.add_argument("--poly2-cool-start", type=float, default=None, help="Stage 2 post-polymerization cool-down start temperature.")
    parser.add_argument("--poly2-cool-end", type=float, default=None, help="Stage 2 post-polymerization cool-down end temperature.")
    parser.add_argument("--poly2-cool-steps", type=int, default=None, help="Stage 2 post-polymerization cool-down steps.")
    parser.add_argument(
        "--seed-mode",
        choices=["auto", "keep"],
        default="auto",
        help="auto generates distinct seeds for seed-bearing steps; keep preserves existing input seeds unless explicit seeds are provided.",
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Submit generated jobs. Main jobs are chained with Slurm afterok dependencies.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without modifying files or launching jobs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    args.source_root = root
    if not root.exists():
        raise SystemExit(f"Project root does not exist: {root}")

    for label, value in (
        ("--poly1-prob", args.poly1_prob),
        ("--poly2-prob", args.poly2_prob),
        ("--poly1-xlinkd", args.poly1_xlinkd),
        ("--poly2-xlinkd", args.poly2_xlinkd),
    ):
        if value is not None and not (0 <= value <= 1):
            raise SystemExit(f"{label} must be between 0 and 1")
    for label, value in (
        ("--poly1-monomers", args.poly1_monomers),
        ("--poly2-monomers", args.poly2_monomers),
    ):
        if value is not None and value < 1:
            raise SystemExit(f"{label} must be at least 1")

    result = validate(root, start_data_override=args.start_data)

    if args.command in {"status", "prepare", "build", "postprocess", "all"}:
        print_validation_report(result)

    if args.command == "status":
        return 1 if result.missing else 0

    if result.missing:
        eprint("Workflow cannot continue until the missing items above are added.")
        return 1

    work_root = root

    if args.command in {"prepare", "build", "all"}:
        work_root = prepare_run_bundle(root, args)
        if not args.dry_run:
            bundle_result = validate(work_root)
            if bundle_result.missing:
                print_validation_report(bundle_result)
                eprint("Run bundle cannot continue until the missing items above are added.")
                return 1

    if args.command in {"build", "all"}:
        generate_job_scripts(
            work_root,
            queue=args.queue,
            cores=args.cores,
            nodes=args.nodes,
            dry_run=args.dry_run,
        )

        if args.submit:
            submit_main_chain(work_root, dry_run=args.dry_run)

    if args.command in {"postprocess", "all"}:
        if args.command == "postprocess" and args.run_dir:
            work_root = run_bundle_path(root, args.runs_dir, args.run_name, args.run_dir).resolve()
        final_data = pick_final_data_file(work_root, explicit=args.final_data)
        print(f"Final data file: {final_data.name}")
        modified = create_modified_data_copy(work_root, final_data)
        print(f"Created modified copy: {modified.name}")
        run_generators(work_root, submit=args.submit, dry_run=args.dry_run)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
