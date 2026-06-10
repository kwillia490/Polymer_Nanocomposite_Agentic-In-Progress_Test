# -*- coding: utf-8 -*-
"""
Created on Tue Jul 19 13:31:31 2022
Updated Dec 16, 2024
@author: Dr. William A. Pisani, Research Chemist
@email: william.a.pisani@usace.army.mil

This script will write out LAMMPS input scripts and submission scripts
for thermal conductivity simulations.
"""

import os
from datetime import datetime
today = datetime.today().strftime('%m%d%Y')
current_dir = os.getcwd()

# To get a list of the data files [x for x in os.listdir(current_dir)]
data_files = ['Polymer_ANEqPlyANEq_R1.dat.gz']

temp = 300 # Kelvin, can be changed to a different temperature
direction = 'z' # Change to x, y, or z
n_bins = 34 # Please set this such that the bin thickness is around 3. This value must be an even number or LAMMPS will give an error.
for f in data_files:
    print("Note: You may need to change the parsing on lines 25, 26, and 27 to match your filename conventions.")
    f_split = f.split('.dat')[0].split('_')
    f_split_join = '_'.join(['_'.join(f_split[0:2]),today,'_'.join(f_split[3:-2])])
    f_name = f_split_join + f'_RNEMD_{direction}_{n_bins}bins_{temp}K_' + f_split[-1]
    
    with open(f_name+'.in','w') as handle:
        handle.write(f"""# The purpose of this script is to obtain the thermal conductivity using the reverse NEMD TC method.

#################################
### Initialization & Settings ###
#################################
#---------initialization---------
echo screen
units           real
dimension       3
boundary        p p p
variable myid string {f_name}
variable data string {f}
""")
        handle.write("""
log		    ${myid}.log.lammps

variable thermo_freq equal 1000
variable dump_freq equal 20*${thermo_freq}
timestep        1 #fs
variable runtime equal 600000 # fs""")
        handle.write(f"\nvariable set_temp equal {temp} # K\n")
        handle.write("""

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
read_data       ${data} 

##############################
### Thermo & Dump Settings ###
##############################
compute keperatom all ke/atom

thermo ${thermo_freq}
dump 1 all custom/gz ${dump_freq} ${myid}.lammpstrj.gz x y z type id c_keperatom

####################
### Run Settings ###
####################

# 1st equilibration run

fix		1 all nvt temp ${set_temp} ${set_temp} 1000
thermo		1000
run		${runtime} # 10 ps

velocity	all scale ${set_temp}

unfix		1

# 2nd equilibration run

compute   ke all ke/atom
variable  temp atom c_ke/1.5*503.2195335 # Divide by avogadro's number, multiply by 1000 cal/1kcal multiply by 4.184 J/cal and divide by Boltzmann's constant

fix 1 all nve
""")
        handle.write(f"compute   layers all chunk/atom bin/1d {direction} lower $(l{direction}/{n_bins}) units box\n")
        handle.write("fix       2 all ave/chunk 10 100 1000 layers v_temp file ${myid}_tmp.profile\n")
        handle.write(f"fix 3 all thermal/conductivity 10 {direction} {n_bins}\n")

        handle.write(f"variable        tdiff equal abs(f_2[{int(n_bins/2+1)}][3]-f_2[1][3])\n")
        handle.write("""
variable        heat_flux equal f_3

thermo_style custom step temp press etotal ke pe epair ebond eangle edihed eimp elong lx ly lz pxx pyy pzz vol density f_3 v_tdiff
run ${runtime} # 50 ps

# thermal conductivity calculation
# reset fix thermal/conductivity to zero energy accumulation
unfix 3
""")
        handle.write(f"fix	3 all thermal/conductivity 10 {direction} {n_bins}\n")
        
        handle.write("""
fix ave all ave/time 1 1 ${thermo_freq} v_tdiff ave running

thermo_style custom step temp press etotal ke pe epair ebond eangle edihed eimp elong lx ly lz pxx pyy pzz vol density f_3 v_tdiff f_ave
run ${runtime} # 50 ps
""")
        if direction == 'x':
            handle.write('variable J equal $(f_3/(v_runtime*lz*ly*2)*1000*4.184/(6.02214076*10^23)*10^15*(10^10)^2) # W/m^2, the 2 is there because it is a periodic system\n')
        elif direction == 'y':
            handle.write('variable J equal $(f_3/(v_runtime*lz*lx*2)*1000*4.184/(6.02214076*10^23)*10^15*(10^10)^2) # W/m^2, the 2 is there because it is a periodic system\n')
        elif direction == 'z':
            handle.write('variable J equal $(f_3/(v_runtime*lx*ly*2)*1000*4.184/(6.02214076*10^23)*10^15*(10^10)^2) # W/m^2, the 2 is there because it is a periodic system\n')

        
        handle.write(f'variable dT_d{direction} equal $(f_ave/(l{direction}/2/(10^10))) # K/m\n')
        handle.write(f'variable k equal $(v_J/v_dT_d{direction})\n')
        handle.write('print "J: ${J}"\n')
        handle.write(f'print "dT/d{direction}: $' + '{dT_d' + f'{direction}' + '}"\n')
        handle.write(f'print "average conductivity in {direction}-direction with {n_bins} bins: ' + '${k}[W/mK] @ ${set_temp} K"\n')
     
    print(f'{f_name}.in written successfully!')

    # 
    p = os.popen(f'/qlammps.sh -c 192 -n 1 -w 168:00:00 -q standard -f {f_name}.in -s')
    print(p.read())

