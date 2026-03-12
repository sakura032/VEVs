from __future__ import annotations

from pathlib import Path
import json
import shutil

import pytest

from src.configs import ProjectPaths
from src.interfaces.contracts import DockingPose, InputManifest
from src.utils import ComplexAssembler, StructurePreprocessor


def _new_temp_root(test_name: str) -> Path:
    root = Path("work") / "pytest_temp" / test_name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_pdb(path: Path, chain: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"ATOM      1    N ALA {chain}   1       0.000   0.000   0.000  1.00  0.00           N\n"
        f"ATOM      2   CA ALA {chain}   1       1.400   0.000   0.000  1.00  0.00           C\n"
        f"ATOM      3    C ALA {chain}   1       2.200   1.200   0.000  1.00  0.00           C\n"
        f"ATOM      4    O ALA {chain}   1       2.000   2.300   0.100  1.00  0.00           O\n"
        "TER\nEND\n",
        encoding="utf-8",
    )


def test_structure_preprocessor_smoke() -> None:
    pytest.importorskip("pdbfixer")
    pytest.importorskip("openmm")

    root = _new_temp_root("preprocessor_smoke")
    receptor = root / "data" / "receptor.pdb"
    ligand = root / "data" / "ligand.pdb"
    _write_pdb(receptor, "A")
    _write_pdb(ligand, "L")

    paths = ProjectPaths.from_root(root)
    preprocessor = StructurePreprocessor(paths=paths, keep_water=False)
    manifest = InputManifest(receptor_path=receptor, ligand_path=ligand)
    prepared = preprocessor.preprocess(manifest)

    assert prepared.receptor_clean.exists()
    assert prepared.ligand_prepared.exists()
    assert prepared.preprocess_report is not None
    report = json.loads(prepared.preprocess_report.read_text(encoding="utf-8"))
    assert "receptor" in report and "ligand" in report


def test_complex_assembler_compatible_with_complex_pose() -> None:
    root = _new_temp_root("assembler_smoke")
    receptor = root / "data" / "receptor_clean.pdb"
    ligand = root / "data" / "ligand_prepared.pdb"
    pose = root / "data" / "pose_complex.pdb"
    _write_pdb(receptor, "A")
    _write_pdb(ligand, "L")
    _write_pdb(pose, "B")

    from src.interfaces.contracts import PreparedStructures

    prepared = PreparedStructures(receptor_clean=receptor, ligand_prepared=ligand)
    selected_pose = DockingPose(
        pose_id=0,
        score=0.0,
        pose_file=pose,
        metadata={"pose_representation": "complex_pdb", "backend": "placeholder"},
    )

    assembler = ComplexAssembler(paths=ProjectPaths.from_root(root))
    assembled = assembler.assemble(prepared, selected_pose)

    assert assembled.mode == "solution"
    assert assembled.complex_structure.exists()
    assert assembled.metadata["pose_representation"] == "complex_pdb"

