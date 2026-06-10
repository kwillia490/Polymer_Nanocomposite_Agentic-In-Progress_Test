# Quick Start

## 1. Unpack And Enter The Project

```bash
cd Polymer_Nanocomposite_Project-main
```

## 2. Check Inputs

```bash
python3 workflow.py status
```

The first stage expects the starting structure referenced by
`Polymer_Densify_R1.in`. If needed, pass an override:

```bash
python3 workflow.py status --start-data /path/to/starting_file.data
```

The ZIP does not include the production nanocomposite starting data file. The PE
data in `LUNAR_Prepared_REACTER_Files/` is a reference/toy example, not the
production CNT/polymer starting structure.

## 3. Start The Web UI

```bash
python3 web_server.py
```

Open:

```text
http://127.0.0.1:8765
```

The web UI has three tabs:

- `Prepare`: starting data, basic simulation settings, advanced controls, and polymerization stages
- `Workflow`: readiness, main stages, job generation, post-processing
- `Analysis`: simple local CSV plotting

Use `Prepare Files` first when you want the UI to create a run-specific bundle
with edited `.in` files before any HPC job scripts are made.

## 4. Prepare Run Files

The prepare step copies the project into `runs/<run_name>/`, copies a
user-supplied starting data file into that bundle when needed, edits the known
tunable values in the LAMMPS input decks, and writes `run_config.json` plus
`seeds.json`.

Example:

```bash
python3 workflow.py prepare \
  --start-data /path/to/starting_file.data \
  --run-name Polymer_test_001 \
  --target-density 1.264 \
  --poly1-monomers 2999 --poly1-temp 300 --poly1-prob 0.2 \
  --poly2-monomers 2999 --poly2-temp 650 --poly2-prob 0.2
```

## 5. Generate Job Scripts

Set cluster-specific values if needed:

```bash
export LAMMPS_BIN="/path/to/lammps"
export MPI_COMMAND="mpiexec"
export SLURM_ACCOUNT="your_account"
export SLURM_MAIL_USER="your_email@example.com"
```

Generate scripts:

```bash
python3 workflow.py build --run-name Polymer_test_001
```

Dry run:

```bash
python3 workflow.py build --dry-run
```

Submit the dependency chain:

```bash
python3 workflow.py build --submit
```

## 6. Postprocess

After the final main output exists:

```bash
python3 workflow.py postprocess --final-data Polymer_ANEqPlyANEq_R1.dat.gz
```

Submit post-processing jobs:

```bash
python3 workflow.py postprocess --final-data Polymer_ANEqPlyANEq_R1.dat.gz --submit
```

## 7. PE REACTER Reference

The `LUNAR_Prepared_REACTER_Files/` folder is an educational reference. It is
not required by the main workflow. See `docs/PE_REACTER_REFERENCE.md`.
