#! /bin/bash
#PBS -l select=1:ncpus=192:mpiprocs=10
#PBS -l walltime=01:00:00
#PBS -q debug
#PBS -A ERDCV00898FAE
#PBS -l application=lmp_20260210_intel_barfoot
#PBS -m abe
#PBS -M Kyle.I.Williamson@erdc.dren.mil
#PBS -o PE_IFFPlyS0.in.sh.out
#PBS -e PE_IFFPlyS0.in.sh.error
#PBS -V

# Set runtime environment
#export CRAY_ROOTFS=DSL
export CRAYPE_LINK_TYPE=dynamic
module swap PrgEnv-cray PrgEnv-intel
module list


# Set LAMMPS and script directories, and name of script to run
lmp_dir=/p/global/Projects/erdc-cct/bin
script_dir=/p/work/kiwillia/PE_REACTER
script_name=PE_IFFPlyS0.in

# Move into script directory
cd ${script_dir}

# Run simulation with the total requested number of mpi cores
mpiexec -n 10 ${lmp_dir}/lmp_20260210_intel_barfoot -in ${script_name}
