# PE REACTER Reference Files

The folder `LUNAR_Prepared_REACTER_Files/` is a reference-only polyethylene
example. It is included so users can study a smaller, reproducible REACTER setup
before preparing their own chemistry for the longer polymer nanocomposite
workflow.

It is not required to run the main nanocomposite workflow.

## Why This Folder Exists

`fix bond/react` inputs are easy to get syntactically correct but chemically
wrong. This folder gives users a concrete, inspectable example of files prepared
with LUNAR and tested in a small polyethylene system.

Use it to learn:

- what pre-reaction and post-reaction structures look like
- how LUNAR atom typing outputs are organized
- how merged `.lmpmol` files differ from source structures
- what a REACTER map file looks like
- how a small `fix bond/react` test can be set up before scaling to the long
  workflow

## Important Caveat

This is a learning and reproducibility example, not a publication-ready
polyethylene model. The included PE monomer is not hydrogen-terminated on one
end, which may create charge or chemistry issues after polymerization. Use this
folder to learn and test the workflow mechanics, then build and validate your
own chemically appropriate monomer/reaction system.

## Key Files

Source/reference structures:

- `PE_Unit.sdf`
- `PE_PreReaction.pdb`
- `PE_PostReaction.sdf`

LUNAR atom typing outputs:

- `PE_Unit_typed.data`
- `PE_Unit_typed.nta`
- `PE_Unit_typed.log.lunar`
- `PE_PreReaction_typed.data`
- `PE_PreReaction_typed.nta`
- `PE_PreReaction_typed.log.lunar`
- `PE_PostReaction_typed.data`
- `PE_PostReaction_typed.nta`
- `PE_PostReaction_typed.log.lunar`

LUNAR all2lmp / IFF outputs:

- `PE_Unit_typed_IFF.data`
- `PE_PreReaction_typed_IFF.data`
- `PE_PostReaction_typed_IFF.data`
- matching `.txt` and `.log.lunar` files

Merged REACTER-style files:

- `PE_PreReaction_typed_IFF_merged.lmpmol`
- `PE_PostReaction_typed_IFF_merged.lmpmol`
- `pre1-post1_rxn-map_commented.txt`
- `pre1-post1_rxn-map_uncommented.txt`

Small test system and scripts:

- `PE_Test_System.data`
- `in.create_atoms.script`
- `in.fix_bond_react.script`
- `in.PE_Test_System.script`
- `PE_IFFDfyS0.in`
- `PE_IFFPlyS0.in`
- `PE_IFFDfyS0.dat.gz`
- `PE_IFFPlyS0.dat.gz`
- `force_field.data`

## How The Example Was Prepared

The example was prepared with LUNAR:

1. Create monomer, pre-reaction, and post-reaction structures using a molecular
   editor such as Ketcher.
2. Run each structure through LUNAR `atom_typing.py`.
3. Use PCFF-IFF style atom typing and include comments in `.nta` files.
4. Inspect `.nta` files for typing failures.
5. Run the typed `.data` and `.nta` files through LUNAR `all2lmp.py`.
6. Add LUNAR bond/react header hints to the pre/post typed IFF data files:

   ```text
   Reduce = [4,4]; BondingIDs = [8,25,8,25]
   ```

7. Run LUNAR `bond_react_merge.py` to create merged molecule templates and map
   files.
8. Test the files in a small PE system before attempting larger simulations.

Refer to the LUNAR manual for exact GUI and command-line details.

## What To Copy Into Experiments

For a small REACTER experiment, the most relevant files are usually:

- `PE_PreReaction_typed_IFF_merged.lmpmol`
- `PE_PostReaction_typed_IFF_merged.lmpmol`
- `pre1-post1_rxn-map_uncommented.txt`
- `force_field.data`
- `in.fix_bond_react.script`

Do not blindly copy these files into a new chemistry. The atom IDs, map file,
bonding IDs, edge atoms, deleted/created atoms, force-field types, and charges
must match the chemistry being modeled.

## Suggested Visual Checks

Use OVITO, VMD, or another visualizer to inspect:

- pre-reaction and post-reaction structures
- merged `.lmpmol` templates
- `PE_IFFDfyS0.dat.gz`
- `PE_IFFPlyS0.dat.gz`

For this example, cluster analysis can show whether the small system polymerized
as expected.

## Relationship To The Main Workflow

The main nanocomposite workflow has its own polymer reaction files:

- `Polymer_Pre-Rxn.template`
- `Polymer_Post-Rxn.template`
- `map_file_Polymer_deleteH2.txt`

The PE folder is a teaching/reference set. It does not replace those files and
is not called by `workflow.py`.
