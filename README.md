# Polymer Nanocomposite LAMMPS Workflow

This project contains a staged LAMMPS workflow for a polymer nanocomposite
system. The main workflow validates required inputs, prepares run-specific input
decks, generates Bash/Slurm job scripts, optionally submits the simulation
chain, and prepares post-processing jobs for mechanical and thermal analysis.

The folder `LUNAR_Prepared_REACTER_Files/` is included as a reference-only
polyethylene example. It is not required to run the main nanocomposite workflow.
Use it to learn what well-prepared `fix bond/react` / REACTER inputs look like.

## Quick Start

Check whether the workflow inputs are present:

```bash
python3 workflow.py status
```

Start the local web UI:

```bash
python3 web_server.py
```

Then open:

```text
http://127.0.0.1:8765
```

Generate Slurm job scripts without submitting:

```bash
python3 workflow.py build
```

Prepare a portable run bundle without generating job scripts:

```bash
python3 workflow.py prepare --run-name Polymer_test_001
```

Generate and submit the main workflow as a dependency chain:

```bash
python3 workflow.py build --submit
```

Prepare post-processing jobs after the final main output exists:

```bash
python3 workflow.py postprocess --final-data Polymer_ANEqPlyANEq_R1.dat.gz
```

## Main Simulation Stages

1. `Polymer_Densify_R1.in`
2. `Polymer_AN_R1.in`
3. `Polymer_ANEq_R1.in`
4. `Polymer_ANEqPly_R1_1.in`
5. `Polymer_ANEqPly_R1_2.in`
6. `Polymer_ANEqPlyAN_R1.in`
7. `Polymer_ANEqPlyANEq_R1.in`

Post-processing generators:

1. `YM_Generator.sh`
2. `Sh_Generator.sh`
3. `PrePoly_BK_Generator.sh`
4. `BK_Generator.sh`
5. `Generate_RNEMD_TC_Scripts.py`

## Dependencies

See `DEPENDENCIES.md` for required and optional software. At minimum, users
need Python 3, Bash on the machine that generates job scripts, a LAMMPS
executable on the target compute system, and Slurm if they want to submit jobs.

## More Documentation

- `QUICKSTART.md`: shortest path from unzip to status/build/web UI.
- `WORKFLOW.md`: detailed staged workflow and run-bundle behavior.
- `DEPENDENCIES.md`: software and Python package checklist.
- `docs/PE_REACTER_REFERENCE.md`: guide to the reference-only PE REACTER files.
- `AGENTS.md`: guidance for future coding agents or maintainers.
