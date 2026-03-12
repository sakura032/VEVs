from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .pdb_utils import PDBAtom, distance

#计算 contact/clash、vdW-like、electrostatic-like、distance penalty，
#输出统一 InteractionScoreBreakdown
#排序规则：分值越低越好，和 BindingWorkflow.rank_poses() 兼容
@dataclass(slots=True)
class InteractionScoreBreakdown:
    """Coarse interaction score for deterministic placeholder docking."""

    min_distance_angstrom: float
    contact_count: int
    clash_count: int
    vdw_like_energy: float
    electrostatic_like_energy: float
    distance_penalty: float
    total_score: float


def _pseudo_charge(atom: PDBAtom) -> float:
    # Pseudo charges are only for relative ranking in placeholder mode.
    element = (atom.element or "").upper()
    if element == "O":
        return -0.45
    if element == "N":
        return -0.30
    if element == "S":
        return -0.20
    if element == "H":
        return 0.30
    if element == "P":
        return 0.35
    if element == "C":
        return 0.10
    return 0.00


def _pairwise_energy(atom_a: PDBAtom, atom_b: PDBAtom, r_angstrom: float) -> tuple[float, float]:
    # A stable, bounded coarse interaction proxy: not physically rigorous.
    r = max(r_angstrom, 1e-6)
    sigma = 3.5
    epsilon = 0.08
    sr = sigma / r
    vdw = epsilon * (sr**12 - 2.0 * sr**6)
    electro = 0.05 * _pseudo_charge(atom_a) * _pseudo_charge(atom_b) / r
    return vdw, electro


def calculate_interaction_score(
    receptor_atoms: list[PDBAtom],
    ligand_atoms: list[PDBAtom],
    contact_cutoff_angstrom: float = 4.5,
    clash_cutoff_angstrom: float = 1.8,
    interaction_cutoff_angstrom: float = 8.0,
) -> InteractionScoreBreakdown:
    """Compute deterministic contact/clash/energy proxies for one docked pose."""
    if not receptor_atoms or not ligand_atoms:
        raise ValueError("receptor_atoms and ligand_atoms must be non-empty")

    min_distance = float("inf")
    contact_count = 0
    clash_count = 0
    vdw_sum = 0.0
    electro_sum = 0.0

    nearest_sum = 0.0
    for lig_atom in ligand_atoms:
        nearest = float("inf")
        for rec_atom in receptor_atoms:
            r = distance(lig_atom, rec_atom)
            if r < nearest:
                nearest = r
            if r < min_distance:
                min_distance = r
            if r <= contact_cutoff_angstrom:
                contact_count += 1
            if r <= clash_cutoff_angstrom:
                clash_count += 1
            if r <= interaction_cutoff_angstrom:
                vdw, electro = _pairwise_energy(lig_atom, rec_atom, r)
                vdw_sum += vdw
                electro_sum += electro
        nearest_sum += nearest

    avg_nearest = nearest_sum / float(len(ligand_atoms))
    distance_penalty = max(0.0, avg_nearest - 2.8)

    # Lower score is better (compatible with workflow rank_poses sorting).
    total = (
        4.0 * clash_count
        + 1.5 * distance_penalty
        + vdw_sum
        + electro_sum
        - 0.03 * contact_count
    )
    if not isfinite(total):
        raise ValueError("calculated non-finite interaction score")

    return InteractionScoreBreakdown(
        min_distance_angstrom=min_distance,
        contact_count=contact_count,
        clash_count=clash_count,
        vdw_like_energy=vdw_sum,
        electrostatic_like_energy=electro_sum,
        distance_penalty=distance_penalty,
        total_score=total,
    )

