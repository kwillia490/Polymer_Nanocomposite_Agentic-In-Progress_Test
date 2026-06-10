#!/bin/bash
#
# This script will generate bulk modulus LAMMPS input scripts for unpolymerized PCFF systems.

# Sim data files here


sim_data_files=("Polymer_ANEq_R1.dat.gz")

for sim in ${sim_data_files[@]}
do
# uncomment the following line if you use line 7 to find all of the systems you want to test (useful if you run many different replicates all with similar filenames)
#    sim=${sim:2} 
   
#input_script=${sim: 0: -7}BK
input_script=${sim: 0: 13}BK
# Begin writing bulk mod script
cat <<EOM >${input_script}.in
# This script will run at 300 K and 1.0 atm for 500 ps and then ramp to 5000 atm and 300 K for 500 ps. Both runs NPT aniso

##########################
### Simulation history ###
##########################

#################################
### Initialization & Settings ###
#################################

# Debugging
echo screen

units 		real
dimension	3
boundary	p p p

variable myid string ${input_script}
variable data string ${sim}
log \${myid}.log.lammps

timestep        1 #fs

##############################
### Force Field Parameters ###
##############################

atom_style	full
bond_style class2
angle_style class2
dihedral_style class2
improper_style class2
special_bonds lj/coul 0 0 1
pair_style lj/class2/coul/long 10.0
pair_modify mix sixthpower
kspace_style pppm 1e-6
read_data       \${data}

variable thermo_freq equal 10000
variable dump_freq equal 20*\${thermo_freq}

##############################
########## Stresses ##########
##############################

compute         p all pressure thermo_temp
variable        sxx equal -0.101325*c_p[1] #in MPa
variable        syy equal -0.101325*c_p[2] #in MPa
variable        szz equal -0.101325*c_p[3] #in MPa
fix             sxx_ave all ave/time 1 \${thermo_freq} \${thermo_freq} v_sxx
fix             syy_ave all ave/time 1 \${thermo_freq} \${thermo_freq} v_syy
fix             szz_ave all ave/time 1 \${thermo_freq} \${thermo_freq} v_szz

##############################
### Thermo & Dump Settings ###
##############################

thermo \${thermo_freq}
thermo_style custom step temp press etotal ke pe epair ebond eangle edihed eimp elong lx ly lz pxx pyy pzz v_sxx v_syy v_szz f_sxx_ave f_syy_ave f_szz_ave vol density

dump 1 all custom/gz \${dump_freq} \${myid}.lammpstrj.gz x y z type id 

####################
### Run Settings ###
####################
neigh_modify    delay 0 every 1 check yes one 2500 page 100000
fix	1 all npt temp 300 300 1000 aniso 1.0 1.0 10000

run 100000 # 100 ps
run 100000 # 100 ps
run 100000 # 100 ps
run 100000 # 100 ps
run 100000 # 100 ps
unfix 1

fix 1 all npt temp 300 300 1000 aniso 5000.0 5000.0 10000
run 100000 # 100 ps
run 100000 # 100 ps
run 100000 # 100 ps
run 100000 # 100 ps
run 100000 # 100 ps
write_data \${myid}_5000atm.dat
EOM
      echo "${input_script}.in created!"
      # Add the -s submission flag after you verify that the scripts were written correctly
      /qlammps.sh -c 192 -n 1 -w 72:00:00 -q standard -f ${input_script}.in -s



done
