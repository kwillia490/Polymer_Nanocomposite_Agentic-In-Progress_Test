#! /bin/bash

# Generate a Slurm job file for a LAMMPS input script.
# Call this script from the directory where the LAMMPS input script is located.
#
# Optional environment variables:
#   SLURM_ACCOUNT      account/project allocation
#   SLURM_MAIL_USER    email for job notifications
#   LAMMPS_BIN         full path to the LAMMPS executable
#   MPI_COMMAND        MPI launcher command, defaults to mpiexec

nodes=''
cores=''
walltime=''
queue=''
script=''
submit=false

print_usage() {
   echo "Usage: qlammps -c 128 -n 2 -w 24:00:00 -q standard -f lammps_input.in"
   echo "       or"
   echo "       qlammps -c 128 -n 2 -w 1:00:00 -q debug -f lammps_input.in -s"
   echo "       -n [number of nodes], mandatory"
   echo "       -c [number of cores], mandatory"
   echo "       -w [hh:mm:ss], mandatory"
   echo "       -q [queue_name], mandatory"
   echo "       -f [LAMMPS_input_script_name], mandatory"
   echo "       -s, submit to job scheduler, optional"
   echo
}

while getopts 'n:c:w:q:f:s' flag
do
   case "${flag}" in
      n) nodes="${OPTARG}" ;;
      c) cores="${OPTARG}" ;;
      w) walltime="${OPTARG}" ;;
      q) queue="${OPTARG}" ;;
      f) script="${OPTARG}" ;;
      s) submit=true ;;
      *) print_usage
         exit 1 ;;
   esac
done

if (( "$#" < 10 ))
then
   echo "Error: You must supply all mandatory arguments."
   print_usage
   exit 1
fi

script_dir=$(pwd)
total_cores=$((nodes * cores))
slurm_account="${SLURM_ACCOUNT:-}"
slurm_mail_user="${SLURM_MAIL_USER:-}"
lammps_bin="${LAMMPS_BIN:-}"
mpi_command="${MPI_COMMAND:-mpiexec}"
slurm_account_line=""
slurm_mail_user_line=""

if [ -n "${slurm_account}" ]; then
   slurm_account_line="#SBATCH --account=${slurm_account}"
fi
if [ -n "${slurm_mail_user}" ]; then
   slurm_mail_user_line="#SBATCH --mail-user=${slurm_mail_user}"
fi

cat <<EOM >${script}.sh
#! /bin/bash
#SBATCH --nodes=${nodes}
#SBATCH --ntasks=${total_cores}
#SBATCH --ntasks-per-node=${cores}
#SBATCH --time=${walltime}
${slurm_account_line}
#SBATCH --qos ${queue}
#SBATCH --job-name=${script}
#SBATCH --mail-type=BEGIN,END,FAIL,TIME_LIMIT
${slurm_mail_user_line}
#SBATCH --output=${script}.sh.out
#SBATCH --error=${script}.sh.error

# Set runtime environment
#export CRAY_ROOTFS=DSL
#export CRAYPE_LINK_TYPE=dynamic
module list

script_dir=${script_dir}
script_name=${script}
lammps_bin=${lammps_bin}
mpi_command=${mpi_command}

cd \${script_dir}

if [ ! -x "\${lammps_bin}" ]; then
   echo "Error: LAMMPS executable not found or not executable: \${lammps_bin}" >&2
   echo "Set LAMMPS_BIN before generating job scripts." >&2
   exit 1
fi

\${mpi_command} -n ${total_cores} \${lammps_bin} -in \${script_name}
EOM

echo "${script}.sh successfully written!"

if [ ${submit} == true ]
then
   sbatch ${script}.sh
fi
