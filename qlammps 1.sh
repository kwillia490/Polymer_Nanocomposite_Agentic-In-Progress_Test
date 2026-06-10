#! /bin/bash

# This script will generate an appropriate .sh file for a LAMMPS input script.
# You must call this script from the directory where the LAMMPS input script is located.

# Inputs are number of cores, walltime in hh:mm:ss, queue, and LAMMPS input script name
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
   echo "       -c [number of cores] must be less than or equal to 128, mandatory"
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

if (( "$#" < 10 )) # Five options each with a mandatory argument equals 10
then
   echo "Error: You must supply all mandatory arguments."
   print_usage
   exit 1
fi


script_dir=$(pwd)

total_cores=$(echo "${nodes}*${cores}" | bc)

cat <<EOM >${script}.sh
#! /bin/bash
#SBATCH --nodes=${nodes}
#SBATCH --ntasks=${total_cores}
#SBATCH --ntasks-per-node=${cores}
#SBATCH --time=${walltime}
#SBATCH --account=Account_number_here
#SBATCH --qos ${queue}
#SBATCH --job-name=${script}
#SBATCH --mail-type=BEGIN,END,FAIL,TIME_LIMIT
#SBATCH --mail-user=email_address_here
#SBATCH --output=${script}.sh.out
#SBATCH --error=${script}.sh.error

# Set runtime environment
#export CRAY_ROOTFS=DSL
#export CRAYPE_LINK_TYPE=dynamic
module list

# Set LAMMPS and script directories, and name of script to run
lmp_dir=/path/to/LAMMPS_Binaries
script_dir=${script_dir}
script_name=${script}

# Move into script directory
cd \${script_dir}

# Run simulation with the total requested number of mpi cores
mpiexec -n ${total_cores} \${lmp_dir}/lmp_binary_name -in \${script_name}
EOM

echo "${script}.sh successfully written!"

if [ ${submit} == true ]
then
   sbatch ${script}.sh
fi 
