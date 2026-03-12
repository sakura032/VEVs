from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from src.configs import DockingConfig, ProjectPaths
from src.interfaces.contracts import PreparedStructures
from src.models.docking import (
    PlaceholderDockingEngine,
    summarize_docking_result,
    validate_docking_result,
)


def _write_minimal_pdb(path: Path, chain: str, atom_block: list[tuple[str, str, int, float, float, float, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        serial = 1
        for atom_name, res_name, resid, x, y, z, element in atom_block:
            handle.write(
                f"ATOM  {serial:>5} {atom_name:>4} {res_name:>3} {chain}{resid:>4}    "
                f"{x:>8.3f}{y:>8.3f}{z:>8.3f}{1.00:>6.2f}{0.00:>6.2f}          {element:>2}\n"
            )
            serial += 1
        handle.write("TER\nEND\n")


def _new_temp_root(test_name: str) -> Path:
    root = Path("work") / "pytest_temp" / test_name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _build_prepared_structures(root: Path) -> PreparedStructures:
    receptor = root / "data" / "test_receptor.pdb"
    ligand = root / "data" / "test_ligand.pdb"

    _write_minimal_pdb(
        receptor,
        chain="A",
        atom_block=[
            ("N", "ALA", 1, 0.0, 0.0, 0.0, "N"),
            ("CA", "ALA", 1, 1.4, 0.0, 0.0, "C"),
            ("C", "ALA", 1, 2.2, 1.2, 0.0, "C"),
            ("O", "ALA", 1, 2.0, 2.3, 0.1, "O"),
        ],
    )
    _write_minimal_pdb(
        ligand,
        chain="L",
        atom_block=[
            ("N", "GLY", 1, 8.0, 0.0, 0.0, "N"),
            ("CA", "GLY", 1, 9.2, 0.4, 0.0, "C"),
            ("C", "GLY", 1, 10.0, 1.3, 0.2, "C"),
        ],
    )
    return PreparedStructures(receptor_clean=receptor, ligand_prepared=ligand)


def test_placeholder_engine_reproducible_and_valid() -> None:
    root = _new_temp_root("docking_reproducible")
    paths = ProjectPaths.from_root(root)
    prepared = _build_prepared_structures(root)

    cfg = DockingConfig(backend="placeholder", n_poses=6, random_seed=20260310)
    engine = PlaceholderDockingEngine(cfg, paths)

    first = engine.dock(prepared)
    second = engine.dock(prepared)

    first_scores = [pose.score for pose in first.poses]
    second_scores = [pose.score for pose in second.poses]

    assert first_scores == second_scores
    validate_docking_result(second, require_pose_files=True)

    summary = summarize_docking_result(second)
    assert summary["num_poses"] == 6
    assert summary["best_score"] <= summary["worst_score"]
    assert second.ranked_pose_table is not None
    assert second.ranked_pose_table.exists()


def test_placeholder_engine_score_cutoff_filters_all() -> None:
    root = _new_temp_root("docking_cutoff_all")
    paths = ProjectPaths.from_root(root)
    prepared = _build_prepared_structures(root)

    cfg = DockingConfig(
        backend="placeholder",
        n_poses=4,
        random_seed=20260310,
        score_cutoff=-1_000_000_000.0,
    )
    engine = PlaceholderDockingEngine(cfg, paths)

    with pytest.raises(ValueError, match="No poses passed score_cutoff"):
        engine.dock(prepared)
