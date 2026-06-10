# Dependencies

This project can be inspected on a local workstation, but the full simulation
workflow is intended for an HPC/Linux environment with LAMMPS and a scheduler.

## Required For Basic Validation

- Python 3.9 or newer
- Standard Python library only for `workflow.py` and `web_server.py`
- A terminal capable of running:
  - `python3 workflow.py status`
  - `python3 web_server.py`

On Windows, use `python` instead of `python3` if that is how Python is installed.

## Required For Job Generation

- Bash
- `qlammps.sh`
- A LAMMPS executable available on the target system
- MPI launcher, usually `mpiexec`

Set these environment variables before generating jobs if your cluster differs
from the defaults:

```bash
export LAMMPS_BIN="/path/to/lammps/executable"
export MPI_COMMAND="mpiexec"
export SLURM_ACCOUNT="your_account"
export SLURM_MAIL_USER="your_email@example.com"
```

`qlammps.sh` remains Bash-dependent. On Windows, generate jobs inside WSL,
Git Bash, or on the HPC login node.

## Required For Submission

- Slurm command-line tools, especially `sbatch`
- A queue/QOS that accepts the requested node/core/walltime settings
- Cluster modules or environment needed by your LAMMPS build

The workflow submits jobs with `afterok` dependencies when `--submit` is used.

## Optional For Local Web UI

- A modern web browser
- Local network access to `http://127.0.0.1:8765`

The web UI calls the same `workflow.py` commands used by the command line. It is
intended for validation, job generation, submission, post-processing, and simple
CSV analysis. It does not include an interactive REACTER builder.

## Optional For Analysis Demos

- No third-party Python packages are required for the included dummy CSV data.
- Use `python3 make_dummy_data.py` or the web UI's `Make Dummy Data` button.

## Optional For REACTER Learning Reference

The folder `LUNAR_Prepared_REACTER_Files/` is reference-only. To reproduce or
extend that example, users may want:

- LUNAR: https://github.com/CMMRLab/LUNAR
- RDKit, if using LUNAR structure generation from SMILES
- Ketcher or another molecular editor for creating `.mol2`, `.sdf`, or `.pdb`
  structures
- OVITO, VMD, or another molecular visualizer
- LAMMPS with `fix bond/react` support

The PE reference files are provided so users can study a smaller example of
LUNAR-prepared REACTER files before attempting the longer nanocomposite workflow.

## Optional For Local Windows Smoke Tests

- LAMMPS for Windows or LAMMPS-GUI
- WSL or Git Bash if using Bash scripts locally

Windows users can inspect and edit files locally, but HPC job scripts and Slurm
submission are usually best run on the target Linux/HPC system.
