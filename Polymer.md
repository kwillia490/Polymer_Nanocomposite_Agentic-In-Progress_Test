# Agent Playbook: Polymer Workflow

**Role:** You are an autonomous orchestration agent managing a sequential Molecular Dynamics simulation workflow. You have access to local file system tools to validate, execute, and modify simulation files.

**Instructions:** Execute the following tasks strictly in order. Do not proceed to the next task if the current task fails.

**Task 0: Wake-Up Report**
* Scan the current directory for the sequence of input `*.IN` files. 
* Verify that the following files exist and are sequentially linked (each should read the output of the previous):
  1. `*_Densify_*`
  2. `*_AN_*`
  3. `*_ANEq_*`
  4. `*_ANEqPly_*_1`
  5. `*_ANEqPly_*_2`
  6. `*_ANEqPlyAN_*`
  7. `*_ANEqPlyANEq_*`
* Report the presence of these files back to the user.

**Task 1: Validate Inputs**
* Check the current directory for the starting data file required by the `*_Densify_*` script.
* If the starting data file is missing, halt execution and alert the user. 
* If present, report successful validation.

**Task 2: Run submission_1.x**
* Execute the `submission_1.x` shell script to begin the simulation pipeline.
* Monitor standard output and wait for the process to complete successfully.

**Task 3: Process Output Data**
* Locate the final simulation output file ending in `*.dat.gz`.
* Create a copy of this file named `*_M.dat.gz`.
* In `*_M.dat.gz`, locate the section beginning with `Bond Coeffs # class2`. Add a comment character (`#`) to the beginning of the header and every coefficient line underneath it, stopping when you reach the next section header.

**Task 4: Run Post-Processing Generators**
* Execute the following shell scripts sequentially: `YM_Generator`, `Sh_Generator`, `PrePoly_BK_Generator`, `BK_Generator`.
* Finally, execute the Python script: `Generate_RNEMD_TC_Scripts`.
* Report final workflow completion to the user.
