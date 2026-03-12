from __future__ import annotations

from csv import DictWriter
from math import sqrt
from pathlib import Path
import random

from src.configs import DockingConfig, ProjectPaths
from src.interfaces.contracts import DockingEngineProtocol, DockingPose, DockingResult, PreparedStructures

from .pdb_utils import centroid, read_pdb_atoms, rmsd, translate_atoms, write_complex_pdb
from .scoring import calculate_interaction_score


def _random_unit_vector(rng: random.Random) -> tuple[float, float, float]:
    x = rng.uniform(-1.0, 1.0)
    y = rng.uniform(-1.0, 1.0)
    z = rng.uniform(-1.0, 1.0)
    norm = sqrt(x * x + y * y + z * z)
    if norm < 1e-8:
        return 1.0, 0.0, 0.0
    return x / norm, y / norm, z / norm


class PlaceholderDockingEngine(DockingEngineProtocol):
    """Deterministic placeholder docking engine for functional pipeline validation.

    Notes:
    - This implementation is intentionally simple and reproducible.
    - Scores are coarse interaction proxies, not publication-grade energies.
    - Designed for CPU-only functional testing and integration.
    基于固定随机种子生成 deterministic poses，
    输出 outputs/docking/poses/pose_*.pdb 和 poses.csv，可直接注入现有 BindingWorkflow
    第二次修改补充：pose_representation="complex_pdb" 元数据，便于 assembler 兼容
    """

    def __init__(self, docking_config: DockingConfig, paths: ProjectPaths):
        self.cfg = docking_config
        self.paths = paths
        self.paths.ensure_dirs()

    def _validate_inputs(self, prepared: PreparedStructures) -> None:
        receptor = prepared.receptor_clean
        ligand = prepared.ligand_prepared
        if not receptor.exists():
            raise FileNotFoundError(f"receptor_clean does not exist: {receptor}")
        if not ligand.exists():
            raise FileNotFoundError(f"ligand_prepared does not exist: {ligand}")
        if receptor.suffix.lower() != ".pdb":
            raise ValueError("placeholder docking currently supports only PDB receptor input")
        if ligand.suffix.lower() != ".pdb":
            raise ValueError("placeholder docking currently supports only PDB ligand input")

    def dock(self, prepared: PreparedStructures) -> DockingResult:
        """Generate deterministic poses and score them using coarse interactions."""
        self._validate_inputs(prepared)

        receptor_atoms = read_pdb_atoms(prepared.receptor_clean)
        ligand_atoms = read_pdb_atoms(prepared.ligand_prepared)

        receptor_center = centroid(receptor_atoms)
        ligand_center = centroid(ligand_atoms)

        out_dir = self.paths.output_dir / "docking"
        poses_dir = out_dir / "poses"
        poses_dir.mkdir(parents=True, exist_ok=True)
        pose_table = out_dir / "poses.csv"

        rng = random.Random(self.cfg.random_seed)
        generated_poses: list[DockingPose] = []

        # Generate a non-overlapping radial shell around receptor center for deterministic sampling.
        # The key goal is pipeline stability (avoid catastrophic steric clashes -> NaN in MD).
        clash_free_min_distance = 2.2
        clash_free_required_clashes = 0
        for pose_id in range(self.cfg.n_poses):
            ux, uy, uz = _random_unit_vector(rng)
            # Keep ligand away from receptor core in minimum workflow mode.
            base_radius = 10.0 + (6.0 * pose_id / max(1, self.cfg.n_poses - 1))
            best_candidate: tuple[float, float, list, object] | None = None
            accepted_candidate: tuple[float, float, list, object] | None = None

            for attempt in range(8):
                jitter = rng.uniform(-0.35, 0.35)
                radius = max(6.0, base_radius + 1.5 * attempt + jitter)

                target_x = receptor_center[0] + ux * radius
                target_y = receptor_center[1] + uy * radius
                target_z = receptor_center[2] + uz * radius

                dx = target_x - ligand_center[0]
                dy = target_y - ligand_center[1]
                dz = target_z - ligand_center[2]

                moved_ligand = translate_atoms(
                    ligand_atoms,
                    dx=dx,
                    dy=dy,
                    dz=dz,
                    chain_id="B",
                )
                scored = calculate_interaction_score(receptor_atoms, moved_ligand)
                score = scored.total_score

                candidate = (radius, score, moved_ligand, scored)
                if best_candidate is None:
                    best_candidate = candidate
                else:
                    _, best_score, _, best_scored = best_candidate
                    if scored.clash_count < best_scored.clash_count or (
                        scored.clash_count == best_scored.clash_count and score < best_score
                    ):
                        best_candidate = candidate

                if (
                    scored.clash_count <= clash_free_required_clashes
                    and scored.min_distance_angstrom >= clash_free_min_distance
                ):
                    accepted_candidate = candidate
                    break

            if accepted_candidate is None:
                # Keep workflow robust: use least-clashing candidate if strict condition fails.
                if best_candidate is None:
                    continue
                radius, score, moved_ligand, scored = best_candidate
            else:
                radius, score, moved_ligand, scored = accepted_candidate

            if self.cfg.score_cutoff is not None and score > self.cfg.score_cutoff:
                continue

            pose_path = poses_dir / f"pose_{pose_id:03d}.pdb"
            write_complex_pdb(receptor_atoms, moved_ligand, pose_path)

            generated_poses.append(
                DockingPose(
                    pose_id=pose_id,
                    score=score,
                    rmsd=rmsd(ligand_atoms, moved_ligand),
                    pose_file=pose_path,
                    metadata={
                        "backend": "placeholder",
                        "method": self.cfg.method,
                        "scientific_validity": "placeholder_not_physical",
                        "score_semantics": "proxy_lower_is_better",
                        "pose_representation": "complex_pdb",
                        "seed": self.cfg.random_seed,
                        "radius_angstrom": radius,
                        "min_distance_angstrom": scored.min_distance_angstrom,
                        "contact_count": scored.contact_count,
                        "clash_count": scored.clash_count,
                        "proxy_vdw_score": scored.vdw_like_energy,
                        "proxy_electrostatic_score": scored.electrostatic_like_energy,
                        "proxy_distance_penalty": scored.distance_penalty,
                    },
                )
            )

        if not generated_poses:
            raise ValueError("No poses passed score_cutoff in placeholder docking")

        # Keep stable deterministic ordering by score for easy downstream consumption.
        generated_poses.sort(key=lambda p: p.score)

        with open(pose_table, "w", newline="", encoding="utf-8") as handle:
            writer = DictWriter(
                handle,
                fieldnames=[
                    "pose_id",
                    "score",
                    "rmsd",
                    "pose_file",
                    "backend",
                    "method",
                    "scientific_validity",
                    "score_semantics",
                    "seed",
                    "radius_angstrom",
                    "min_distance_angstrom",
                    "contact_count",
                    "clash_count",
                    "proxy_vdw_score",
                    "proxy_electrostatic_score",
                    "proxy_distance_penalty",
                ],
            )
            writer.writeheader()
            for pose in generated_poses:
                writer.writerow(
                    {
                        "pose_id": pose.pose_id,
                        "score": f"{pose.score:.8f}",
                        "rmsd": f"{pose.rmsd:.6f}" if pose.rmsd is not None else "",
                        "pose_file": str(pose.pose_file) if pose.pose_file else "",
                        "backend": pose.metadata.get("backend", "placeholder"),
                        "method": pose.metadata.get("method", ""),
                        "scientific_validity": pose.metadata.get(
                            "scientific_validity",
                            "placeholder_not_physical",
                        ),
                        "score_semantics": pose.metadata.get("score_semantics", "proxy_lower_is_better"),
                        "seed": pose.metadata.get("seed", ""),
                        "radius_angstrom": f"{pose.metadata.get('radius_angstrom', 0.0):.6f}",
                        "min_distance_angstrom": f"{pose.metadata.get('min_distance_angstrom', 0.0):.6f}",
                        "contact_count": pose.metadata.get("contact_count", 0),
                        "clash_count": pose.metadata.get("clash_count", 0),
                        "proxy_vdw_score": f"{pose.metadata.get('proxy_vdw_score', 0.0):.8f}",
                        "proxy_electrostatic_score": f"{pose.metadata.get('proxy_electrostatic_score', 0.0):.8f}",
                        "proxy_distance_penalty": f"{pose.metadata.get('proxy_distance_penalty', 0.0):.8f}",
                    }
                )

        return DockingResult(
            poses=generated_poses,
            ranked_pose_table=pose_table,
            selected_pose=None,
        )
