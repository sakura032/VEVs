from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from pathlib import Path


# This module provides minimal PDB parsing and writing utilities for docking-related tasks.
#读取 PDB 原子、计算质心/距离/RMSD、平移 ligand、合并 receptor+ligand 写出 pose 结构
@dataclass(slots=True)
class PDBAtom:    
    """Minimal atom record used by placeholder docking utilities."""

    serial: int
    atom_name: str
    residue_name: str
    chain_id: str
    residue_id: int
    insertion_code: str
    x: float
    y: float
    z: float
    element: str
    record_name: str = "ATOM"


def _infer_element(atom_name: str) -> str: #根据原子名称推断元素符号
    stripped = atom_name.strip()
    if not stripped:
        return "X"
    if len(stripped) >= 2 and stripped[0].isdigit():
        return stripped[1].upper()
    return stripped[0].upper()


def _parse_atom_line(line: str) -> PDBAtom:  #解析原子行
    record_name = line[0:6].strip() or "ATOM"
    serial = int(line[6:11])
    atom_name = line[12:16].strip()
    residue_name = line[17:20].strip() or "UNK"
    chain_id = (line[21:22].strip() or "A")[0]
    residue_id = int(line[22:26])
    insertion_code = line[26:27].strip()
    x = float(line[30:38])
    y = float(line[38:46])
    z = float(line[46:54])
    element = line[76:78].strip() or _infer_element(atom_name)
    return PDBAtom(
        serial=serial,
        atom_name=atom_name,
        residue_name=residue_name,
        chain_id=chain_id,
        residue_id=residue_id,
        insertion_code=insertion_code,
        x=x,
        y=y,
        z=z,
        element=element,
        record_name=record_name,
    )


def read_pdb_atoms(pdb_path: Path) -> list[PDBAtom]:
    """Read ATOM/HETATM records from a PDB file."""
    if not pdb_path.exists():
        raise FileNotFoundError(f"PDB file not found: {pdb_path}")

    atoms: list[PDBAtom] = []
    with open(pdb_path, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(("ATOM", "HETATM")):
                atoms.append(_parse_atom_line(line))

    if not atoms:
        raise ValueError(f"No ATOM/HETATM records found in PDB: {pdb_path}")
    return atoms


def centroid(atoms: list[PDBAtom]) -> tuple[float, float, float]:  #计算原子列表的质心
    if not atoms:
        raise ValueError("Cannot compute centroid of empty atom list")
    n = float(len(atoms))
    return (
        sum(a.x for a in atoms) / n,
        sum(a.y for a in atoms) / n,
        sum(a.z for a in atoms) / n,
    )


def distance(a: PDBAtom, b: PDBAtom) -> float:
    dx = a.x - b.x
    dy = a.y - b.y
    dz = a.z - b.z
    return sqrt(dx * dx + dy * dy + dz * dz)


def translate_atoms(
    atoms: list[PDBAtom],
    dx: float,
    dy: float,
    dz: float,
    chain_id: str | None = None,
    serial_start: int | None = None,
) -> list[PDBAtom]:
    """Create translated atom copy and optionally normalize chain and serials."""
    translated: list[PDBAtom] = []
    for index, atom in enumerate(atoms):
        new_serial = serial_start + index if serial_start is not None else atom.serial
        translated.append(
            PDBAtom(
                serial=new_serial,
                atom_name=atom.atom_name,
                residue_name=atom.residue_name,
                chain_id=chain_id or atom.chain_id,
                residue_id=atom.residue_id,
                insertion_code=atom.insertion_code,
                x=atom.x + dx,
                y=atom.y + dy,
                z=atom.z + dz,
                element=atom.element,
                record_name=atom.record_name,
            )
        )
    return translated


# For simplicity, assume the input atom lists are already aligned and ordered by atom index
def rmsd(reference: list[PDBAtom], target: list[PDBAtom]) -> float:
    """RMSD between two atom sets with identical atom ordering."""
    if len(reference) != len(target):
        raise ValueError("reference and target atom lists must have equal length")
    if not reference:
        return 0.0
    sq_sum = 0.0
    for atom_ref, atom_target in zip(reference, target):
        dx = atom_ref.x - atom_target.x
        dy = atom_ref.y - atom_target.y
        dz = atom_ref.z - atom_target.z
        sq_sum += dx * dx + dy * dy + dz * dz
    return sqrt(sq_sum / len(reference))


# For simplicity, write all atoms with the same chain and sequential serials, ignoring original PDB formatting nuances
def _format_atom_line(serial: int, atom: PDBAtom) -> str:
    atom_name = atom.atom_name.rjust(4)
    res_name = atom.residue_name.rjust(3)
    chain = (atom.chain_id or "A")[0]
    icode = atom.insertion_code[:1] if atom.insertion_code else " "
    element = (atom.element or _infer_element(atom.atom_name)).rjust(2)
    return (
        f"{atom.record_name:<6}{serial:>5} {atom_name} "
        f"{res_name} {chain}{atom.residue_id:>4}{icode}   "
        f"{atom.x:>8.3f}{atom.y:>8.3f}{atom.z:>8.3f}"
        f"{1.00:>6.2f}{0.00:>6.2f}          {element}\n"
    )



def write_complex_pdb(
    receptor_atoms: list[PDBAtom],
    ligand_atoms: list[PDBAtom],
    output_path: Path,
) -> None:
    """Write a merged receptor+ligand pose PDB."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    serial = 1
    with open(output_path, "w", encoding="utf-8") as handle:
        for atom in receptor_atoms:
            handle.write(_format_atom_line(serial, atom))
            serial += 1
        handle.write("TER\n")
        for atom in ligand_atoms:
            handle.write(_format_atom_line(serial, atom))
            serial += 1
        handle.write("TER\nEND\n")

