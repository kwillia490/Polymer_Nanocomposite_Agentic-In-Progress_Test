#!/bin/bash

# This script will download and compile LAMMPS with the AOCC compilers

# Define LAMMPS directory
lmp_directory=/${USER}/Programs/LAMMPS

mkdir -p ${lmp_directory}
if [ ! -d "${lmp_directory}/lammps-git" ]; then
    echo "Cloning LAMMPS repository to ${lmp_directory}/lammps-git"
    git clone -b release https://github.com/lammps/lammps.git ${lmp_directory}/lammps-git
else
    cd ${lmp_directory}/lammps-git
    echo "Updating LAMMPS repository to the latest release"
    git fetch origin release
    git checkout release
    git pull origin release
fi

# Load and list modules
# Use the modules loaded by default (AOCC)
module list

compiler="aocc"

# set dynamic linking,ltbbmalloc will not be found otherwise. There's no static library for tbb
#export CRAYPE_LINK_TYPE=dynamic
cd ${HOME}
build_dir=${lmp_directory}/lammps-git/build_${compiler}
if [ -d "${build_dir}" ]; then
    echo "Removing build directory from previous run"
    rm -r ${build_dir}
fi

echo "Creating ${build_dir}"
mkdir -p ${build_dir}

cd ${build_dir}

# Specify LAMMPS packages and compiler settings
cmake -C ../cmake/presets/clang.cmake \
-D CMAKE_CXX_COMPILER=mpic++ \
-D CMAKE_C_COMPILER=mpicc \
-D CMAKE_Fortran_COMPILER=mpif90 \
-D PKG_CLASS2=on \
-D PKG_COMPRESS=on \
-D PKG_EXTRA-MOLECULE=on \
-D PKG_GRANULAR=on \
-D PKG_INTEL=off \
-D PKG_KSPACE=on \
-D PKG_MANYBODY=on \
-D PKG_MC=on \
-D PKG_MISC=on \
-D PKG_MOLECULE=on \
-D PKG_OPENMP=on \
-D PKG_QEQ=on \
-D PKG_REACTION=on \
-D PKG_REAXFF=on \
-D PKG_RIGID=on \
-D PKG_SHOCK=on \
-D WITH_GZIP=yes \
-D BUILD_MPI=yes \
-D BUILD_OMP=yes \
-D FFT=FFTW3 \
-D FFTW3_INCLUDE_DIR=/aocc/include \
-D FFTW3_LIBRARY=/aocc/lib/libfftw3.a \
-D LAMMPS_MACHINE=mpi ../cmake

# Build
if cmake --build . -j 64 ; then
    today=$(date +"%Y%m%d")
    mkdir -p /${USER}/LAMMPS_Binaries
    cp lmp_mpi /${USER}/LAMMPS_Binaries/lmp_${today}_${compiler}
    echo "lmp_${today}_${compiler} copied to /${USER}/LAMMPS_Binaries"
else
    echo "LAMMPS compilation failed."
fi
