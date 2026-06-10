import os
import glob
import subprocess
import gzip

def validate_lammps_sequence_tool(directory_path=".") -> str:
    """Tasks 0 & 1: Validates sequence of IN files and checks for starting data file."""
    
    # Task 0: Wake-up Report - Check for sequential IN files
    expected_patterns = [
        "*_Densify_*.IN", "*_AN_*.IN", "*_ANEq_*.IN", 
        "*_ANEqPly_*_1.IN", "*_ANEqPly_*_2.IN", 
        "*_ANEqPlyAN_*.IN", "*_ANEqPlyANEq_*.IN"
    ]
    
    for pattern in expected_patterns:
        matches = glob.glob(os.path.join(directory_path, pattern))
        if not matches:
            return f"Error: Missing file in sequence matching {pattern}"
    
    # Task 1: Validate Inputs - Find Densify script and check for read_data
    densify_files = glob.glob(os.path.join(directory_path, "*_Densify_*.IN"))
    if not densify_files:
        return "Error: Densify script not found."
        
    densify_file = densify_files[0]
    data_file_name = None
    
    with open(densify_file, 'r') as f:
        for line in f:
            if line.strip().startswith("read_data"):
                parts = line.split()
                if len(parts) > 1:
                    data_file_name = parts[1]
                    break
                    
    if not data_file_name:
        return "Error: Could not find 'read_data' command in the Densify script."
        
    if not os.path.exists(os.path.join(directory_path, data_file_name)):
        return f"Error: Starting data file '{data_file_name}' not found in directory."
        
    return f"Validation successful: Sequence intact and starting data file '{data_file_name}' is present."

def execute_shell_script_tool(script_name: str, directory_path=".") -> str:
    """Tasks 2 & 4: Executes a local shell script."""
    script_path = os.path.join(directory_path, script_name)
    
    if not os.path.exists(script_path):
        return f"Error: Shell script {script_name} not found."
        
    try:
        # Ensure the script is executable
        subprocess.run(["chmod", "+x", script_path], check=True)
        # Execute the script
        result = subprocess.run(
            [f"./{script_name}"], 
            cwd=directory_path, 
            shell=True, 
            capture_output=True, 
            text=True, 
            check=True
        )
        return f"Success: {script_name} executed.\nOutput:\n{result.stdout}"
    except subprocess.CalledProcessError as e:
        return f"Error executing {script_name}:\n{e.stderr}"

def execute_python_script_tool(script_name: str, directory_path=".") -> str:
    """Task 4: Executes a local python script."""
    script_path = os.path.join(directory_path, script_name)
    
    if not os.path.exists(script_path):
        return f"Error: Python script {script_name} not found."
        
    try:
        result = subprocess.run(
            ["python3", script_name], 
            cwd=directory_path, 
            capture_output=True, 
            text=True, 
            check=True
        )
        return f"Success: {script_name} executed.\nOutput:\n{result.stdout}"
    except subprocess.CalledProcessError as e:
        return f"Error executing {script_name}:\n{e.stderr}"

def modify_bond_coeffs_tool(directory_path=".") -> str:
    """Task 3: Copies *.dat.gz to *_M.dat.gz and comments out the Bond Coeffs section."""
    # Find the original .dat.gz file (ignoring any existing modified files)
    dat_files = [f for f in glob.glob(os.path.join(directory_path, "*.dat.gz")) if not f.endswith("_M.dat.gz")]
    
    if not dat_files:
        return "Error: No original *.dat.gz file found."
        
    input_file = dat_files[0]
    
    # Create the output filename (*_M.dat.gz)
    base_name = input_file[:-7] # Strip off '.dat.gz'
    output_file = f"{base_name}_M.dat.gz"
    
    in_bond_coeffs = False
    
    try:
        with gzip.open(input_file, 'rt') as f_in, gzip.open(output_file, 'wt') as f_out:
            for line in f_in:
                stripped_line = line.strip()
                
                # Detect start of the section
                if stripped_line.startswith("Bond Coeffs"):
                    in_bond_coeffs = True
                    f_out.write(f"# {line}")
                    continue
                    
                if in_bond_coeffs:
                    # If we hit a new section (starts with a letter, ignoring empty lines), turn off commenting
                    if stripped_line and stripped_line[0].isalpha():
                        in_bond_coeffs = False
                        f_out.write(line)
                    else:
                        # We are still inside the Bond Coeffs section, so comment the line
                        if stripped_line == "":
                            f_out.write("\n") # Keep empty lines clean
                        else:
                            f_out.write(f"# {line}")
                else:
                    # Write normally if not in the target section
                    f_out.write(line)
                    
        return f"Success: Created {os.path.basename(output_file)} with Bond Coeffs section commented out."
    except Exception as e:
        return f"Error processing file: {str(e)}"
