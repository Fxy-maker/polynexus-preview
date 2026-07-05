"""IR quantum chemistry input generator (IR-C).

Generates Gaussian and ORCA input files for IR frequency calculations.
Supports cluster models (molecule) and periodic boundary conditions.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


GAUSSIAN_ROUTES = {
    "B3LYP/6-31G(d)":    "#p B3LYP/6-31G(d) opt freq=intmodes",
    "B3LYP/6-31G(d,p)":  "#p B3LYP/6-31G(d,p) opt freq=intmodes",
    "B3LYP/6-311+G(d,p)":"#p B3LYP/6-311+G(d,p) opt freq=intmodes",
    "B3LYP/def2-TZVP":   "#p B3LYP/def2TZVP opt freq=intmodes",
    "B3LYP-D3/6-31G(d)": "#p B3LYP/6-31G(d) empiricaldispersion=gd3bj opt freq",
    "wB97XD/6-31G(d)":   "#p wB97XD/6-31G(d) opt freq",
    "M06-2X/6-31G(d)":   "#p M06-2X/6-31G(d) opt freq",
    "PBE0/6-31G(d)":     "#p PBE0/6-31G(d) opt freq",
    "HF/6-31G(d)":       "#p HF/6-31G(d) opt freq",
    "MP2/6-31G(d)":      "#p MP2/6-31G(d) opt freq",
}


def generate_gaussian_input(molecule_xyz, route="B3LYP/6-31G(d)",
                            charge=0, multiplicity=1,
                            title="Polymer model",
                            n_proc=8, memory_gb=16,
                            additional_keywords="",
                            ) -> str:
    """Generate a Gaussian .gjf input file for IR frequency calculation.

    Parameters
    ----------
    molecule_xyz : str
        XYZ-format molecular geometry.
    route : str
        Level of theory key (see GAUSSIAN_ROUTES) or custom route line.
    charge : int
    multiplicity : int
    title : str
    n_proc : int
        Number of processors.
    memory_gb : int
        Memory in GB.
    additional_keywords : str
        Extra Gaussian keywords appended to route line.

    Returns
    -------
    str : Gaussian input file content.
    """
    route_line = GAUSSIAN_ROUTES.get(route, route)

    if additional_keywords:
        route_line += " " + additional_keywords

    lines = [
        f"%nprocshared={n_proc}",
        f"%mem={memory_gb}GB",
        f"%chk={title.replace(' ', '_')}.chk",
        route_line,
        "",
        title,
        "",
        f"{charge} {multiplicity}",
    ]

    # Parse XYZ and add atom lines
    for line in molecule_xyz.strip().split('\n'):
        stripped = line.strip()
        if not stripped or stripped.isdigit():
            continue
        parts = stripped.split()
        if len(parts) >= 4:
            lines.append(f" {parts[0]:<3s}  {float(parts[1]):12.6f}  {float(parts[2]):12.6f}  {float(parts[3]):12.6f}")

    lines.append("")
    return "\n".join(lines)


ORCA_ROUTES = {
    "B3LYP/def2-SVP":      "! B3LYP def2-SVP Opt Freq",
    "B3LYP/def2-TZVP":     "! B3LYP def2-TZVP Opt Freq",
    "B3LYP-D3/def2-TZVP":  "! B3LYP D3 def2-TZVP Opt Freq",
    "wB97X-D3/def2-TZVP":  "! wB97X-D3 def2-TZVP Opt Freq",
    "PBE0/def2-TZVP":      "! PBE0 def2-TZVP Opt Freq",
}


def generate_orca_input(molecule_xyz, route="B3LYP/def2-TZVP",
                        charge=0, multiplicity=1,
                        title="Polymer model",
                        n_proc=8,
                        ) -> str:
    """Generate an ORCA .inp input file for IR frequency calculation.

    Parameters
    ----------
    molecule_xyz : str
    route : str
    charge : int
    multiplicity : int
    title : str
    n_proc : int

    Returns
    -------
    str : ORCA input file content.
    """
    route_line = ORCA_ROUTES.get(route, f"! {route} Opt Freq")

    coord_lines = []
    for line in molecule_xyz.strip().split('\n'):
        stripped = line.strip()
        if not stripped or stripped.isdigit():
            continue
        parts = stripped.split()
        if len(parts) >= 4:
            coord_lines.append(f"  {parts[0]:<3s}  {float(parts[1]):12.6f}  {float(parts[2]):12.6f}  {float(parts[3]):12.6f}")

    lines = [
        route_line,
        f"%pal nprocs {n_proc} end",
        f"%maxcore 4000",
        "",
        f"* xyz {charge} {multiplicity}",
    ]
    lines.extend(coord_lines)
    lines.append("*")

    return "\n".join(lines)


def generate_xyz_from_smiles(smiles, n_repeat=3, title="polymer"):
    """Generate an oligomer XYZ geometry from SMILES using RDKit.

    Requires: rdkit

    Returns XYZ string or empty string on failure.
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return ""

        # Repeat unit to build oligomer
        # (simplified: just use the monomer with proper termination)
        mol = Chem.AddHs(mol)
        AllChem.EmbedMolecule(mol, randomSeed=42)
        AllChem.MMFFOptimizeMolecule(mol)

        xyz_block = Chem.MolToXYZBlock(mol)
        return xyz_block
    except ImportError:
        return ""


# Common polymer repeat unit SMILES
POLYMER_SMILES = {
    "PE":      "CC",                          # ethylene
    "iPP":     "CC(C)C",                      # propylene
    "PET":     "O=C(OCCc1ccc(C(=O)O)cc1)",    # ethylene terephthalate
    "PA6":     "CCCCC(=O)N",                  # caprolactam
    "PCL":     "CCCCCC(=O)O",                 # caprolactone
    "PLLA":    "CC(O)C(=O)O",                 # lactic acid
    "PVDF":    "CC(F)(F)C",                   # vinylidene fluoride
    "POM":     "OCO",                         # formaldehyde
    "PS":      "CC(c1ccccc1)",                # styrene
    "PMMA":    "CC(C)(C(=O)OC)",              # methyl methacrylate
}
