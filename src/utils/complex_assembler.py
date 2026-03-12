from __future__ import annotations

from pathlib import Path
import shutil

from src.configs import ProjectPaths
from src.interfaces.contracts import AssembledComplex, ComplexAssemblerProtocol, DockingPose, PreparedStructures
from src.models.docking.pdb_utils import read_pdb_atoms, write_complex_pdb


class ComplexAssembler(ComplexAssemblerProtocol):
    """Assemble solution-phase complex from receptor and selected docking pose."""

    def __init__(self, paths: ProjectPaths):
        self.paths = paths
        self.paths.ensure_dirs()

    def assemble(self, prepared: PreparedStructures, pose: DockingPose) -> AssembledComplex:
        if pose.pose_file is None:
            raise ValueError("Selected pose does not provide pose_file")
        if not pose.pose_file.exists():
            raise FileNotFoundError(f"Selected pose file not found: {pose.pose_file}")

        assembled_dir = self.paths.work_dir / "assembled"
        assembled_dir.mkdir(parents=True, exist_ok=True)
        complex_path = assembled_dir / "complex_initial.pdb"

        representation = str(pose.metadata.get("pose_representation", "unknown"))
        if representation == "complex_pdb":
            # Compatibility path with current PlaceholderDockingEngine output.
            shutil.copy2(pose.pose_file, complex_path)
        elif representation == "ligand_pose_pdb":
            receptor_atoms = read_pdb_atoms(prepared.receptor_clean)
            ligand_atoms = read_pdb_atoms(pose.pose_file)
            write_complex_pdb(receptor_atoms, ligand_atoms, complex_path)
        else:
            # Conservative fallback: treat pose file as already assembled complex.
            shutil.copy2(pose.pose_file, complex_path)

        return AssembledComplex(
            complex_structure=complex_path,
            mode="solution",
            metadata={
                "source_pose_id": pose.pose_id,
                "source_pose_file": str(pose.pose_file),
                "pose_representation": representation,
                "docking_backend": pose.metadata.get("backend", "unknown"),
            },
        )

