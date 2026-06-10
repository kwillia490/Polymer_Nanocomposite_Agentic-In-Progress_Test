#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ANALYSIS_DIR = ROOT / "analysis"

STAGE_OUTPUTS = [
    "Polymer_Densify_R1.dat.gz",
    "Polymer_AN_R1.dat.gz",
    "Polymer_ANEq_R1.dat.gz",
    "Polymer_ANEqPly_R1_1.data.gz",
    "Polymer_ANEqPly_R1_2.data.gz",
    "Polymer_ANEqPlyAN_R1.dat.gz",
    "Polymer_ANEqPlyANEq_R1.dat.gz",
]


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def write_gzip(path: Path, text: str) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(text)


def lammps_data(stage_index: int) -> str:
    density = 1.02 + stage_index * 0.035
    box = 12.0 - stage_index * 0.45
    atoms = "\n".join(
        f"{idx} 1 {1 + idx % 3} {(-0.05 + idx * 0.01):.3f} "
        f"{-2.0 + idx * 0.35:.3f} {-1.0 + idx * 0.22:.3f} {0.5 + idx * 0.18:.3f}"
        for idx in range(1, 13)
    )
    return f"""# DUMMY LAMMPS DATA
# Stage index: {stage_index}
# Density marker: {density:.3f} g/cc

12 atoms
3 bonds
1 angles
0 dihedrals
0 impropers

3 atom types
2 bond types
1 angle types
0 dihedral types
0 improper types

{-box / 2:.3f} {box / 2:.3f} xlo xhi
{-box / 2:.3f} {box / 2:.3f} ylo yhi
{-box / 2:.3f} {box / 2:.3f} zlo zhi

Masses

1 12.011
2 1.008
3 15.999

Pair Coeffs # lj/class2/coul/long

1 0.054 4.010
2 0.020 2.995
3 0.120 3.535

Bond Coeffs # class2

1 1.355 312.912 0 0
2 1.098 372.825 -803.453 894.317

Angle Coeffs # class2

1 109.5 39.516 -7.443 -9.558

Atoms # full

{atoms}

Bonds

1 1 1 2
2 2 2 3
3 1 3 4

Angles

1 1 1 2 3
"""


def write_dummy_outputs() -> None:
    for index, name in enumerate(STAGE_OUTPUTS, start=1):
        write_gzip(ROOT / name, lammps_data(index))
        base = name.replace(".dat.gz", "").replace(".data.gz", "")
        write_text(
            ROOT / f"{base}.log.lammps",
            "Step Temp Press Density Etotal\n"
            + "\n".join(
                f"{step} {300 + index * 5 + math.sin(step / 8000):.3f} "
                f"{1.0 + math.cos(step / 9000) * 0.08:.4f} "
                f"{1.02 + index * 0.035 + step / 5000000:.4f} "
                f"{-2400 + index * 42 - step * 0.0008:.3f}"
                for step in range(0, 100001, 10000)
            )
            + "\n",
        )


def write_csv(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_analysis_data() -> None:
    ANALYSIS_DIR.mkdir(exist_ok=True)

    thermo_rows = []
    for step in range(0, 700001, 10000):
        stage = min(step // 100000, 6)
        thermo_rows.append(
            {
                "step": step,
                "stage": stage + 1,
                "temperature_K": round(300 + 65 * math.exp(-step / 280000) + 8 * math.sin(step / 70000), 3),
                "pressure_atm": round(1.0 + 0.18 * math.sin(step / 55000), 4),
                "density_gcc": round(1.02 + 0.25 * (1 - math.exp(-step / 230000)), 4),
                "total_energy_kcal": round(-2100 - 260 * (1 - math.exp(-step / 180000)), 3),
            }
        )
    write_csv(ANALYSIS_DIR / "dummy_thermo.csv", thermo_rows)

    mechanics_rows = []
    for direction, modulus, strength in [("x", 2480, 68), ("y", 2310, 63), ("z", 2660, 72), ("xy", 890, 28), ("xz", 940, 31), ("yz", 870, 27)]:
        for idx in range(0, 41):
            strain = idx * 0.005
            stress = modulus * strain * math.exp(-strain * 2.3)
            stress = min(stress, strength + 4 * math.sin(idx / 3))
            mechanics_rows.append(
                {
                    "direction": direction,
                    "strain": round(strain, 4),
                    "stress_MPa": round(stress, 3),
                    "modulus_MPa": modulus,
                }
            )
    write_csv(ANALYSIS_DIR / "dummy_mechanics.csv", mechanics_rows)

    thermal_rows = []
    for bin_index in range(1, 35):
        position = (bin_index - 1) * 3.0
        thermal_rows.append(
            {
                "bin": bin_index,
                "position_A": round(position, 3),
                "temperature_K": round(318 - 0.58 * position + 2.1 * math.sin(bin_index / 2.5), 3),
                "heat_flux_Wm2": round(1.7e8 + 4.5e6 * math.cos(bin_index / 4), 3),
            }
        )
    write_csv(ANALYSIS_DIR / "dummy_thermal_profile.csv", thermal_rows)


def main() -> int:
    write_dummy_outputs()
    write_analysis_data()
    print(f"Dummy workflow outputs written to {ROOT}")
    print(f"Dummy analysis datasets written to {ANALYSIS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
