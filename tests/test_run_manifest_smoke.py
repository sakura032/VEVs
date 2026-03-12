from __future__ import annotations

import json
from pathlib import Path
import shutil

from src.configs import (
    DockingConfig,
    EndpointFreeEnergyConfig,
    MDConfig,
    MembraneConfig,
    ProjectPaths,
    SystemConfig,
)
from src.interfaces.contracts import (
    AssembledComplex,
    DockingPose,
    DockingResult,
    InputManifest,
    PreparedStructures,
    SimulationArtifacts,
)
from src.models.workflows import BindingWorkflow, BindingWorkflowContext


def _new_temp_root(test_name: str) -> Path:
    root = Path("work") / "pytest_temp" / test_name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_minimal_pdb(path: Path, chain: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"ATOM      1    N ALA {chain}   1       0.000   0.000   0.000  1.00  0.00           N\n"
        f"ATOM      2   CA ALA {chain}   1       1.400   0.000   0.000  1.00  0.00           C\n"
        "TER\nEND\n",
        encoding="utf-8",
    )


class FakeRepository:
    def validate_input_files(self, manifest: InputManifest) -> None:
        if not manifest.receptor_path.exists() or not manifest.ligand_path.exists():
            raise FileNotFoundError("input missing")


class FakePreprocessor:
    def preprocess(self, manifest: InputManifest) -> PreparedStructures:
        return PreparedStructures(
            receptor_clean=manifest.receptor_path,
            ligand_prepared=manifest.ligand_path,
            preprocess_report=None,
        )


class FakeDockingEngine:
    def __init__(self, paths: ProjectPaths):
        self.paths = paths

    def dock(self, prepared: PreparedStructures) -> DockingResult:
        pose_path = self.paths.output_dir / "docking" / "poses" / "pose_000.pdb"
        pose_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(prepared.receptor_clean, pose_path)
        pose = DockingPose(
            pose_id=0,
            score=-1.0,
            pose_file=pose_path,
            metadata={
                "backend": "placeholder",
                "scientific_validity": "placeholder_not_physical",
                "pose_representation": "complex_pdb",
            },
        )
        return DockingResult(poses=[pose], ranked_pose_table=None, selected_pose=None)


class FakeAssembler:
    def __init__(self, paths: ProjectPaths):
        self.paths = paths

    def assemble(self, prepared: PreparedStructures, pose: DockingPose) -> AssembledComplex:
        assembled = self.paths.work_dir / "assembled" / "complex_initial.pdb"
        assembled.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pose.pose_file, assembled)
        return AssembledComplex(complex_structure=assembled, mode="solution", metadata={})


class FakeSimulationRunner:
    def run_full_protocol(self, assembled: AssembledComplex) -> SimulationArtifacts:
        return SimulationArtifacts()


class FakeAnalyzer:
    def __init__(self, paths: ProjectPaths):
        self.paths = paths

    def analyze(self, simulation: SimulationArtifacts) -> dict[str, Path]:
        out_dir = self.paths.output_dir / "analysis" / "binding"
        out_dir.mkdir(parents=True, exist_ok=True)
        metrics_path = out_dir / "metrics.json"
        metrics_path.write_text(
            json.dumps(
                {
                    "analysis_mode": "log_fallback_missing_trajectory",
                    "metrics_semantics": "diagnostic_not_physical",
                    "diagnostic": "true",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return {"metrics_json": metrics_path}


def test_run_manifest_contains_required_boundary_fields() -> None:
    root = _new_temp_root("run_manifest_smoke")
    receptor = root / "data" / "receptor.pdb"
    ligand = root / "data" / "ligand.pdb"
    _write_minimal_pdb(receptor, "A")
    _write_minimal_pdb(ligand, "L")

    paths = ProjectPaths.from_root(root)
    context = BindingWorkflowContext(
        system_config=SystemConfig(receptor_path=receptor, ligand_path=ligand, has_membrane=False),
        md_config=MDConfig(platform="CPU", production_ns=0.001, save_interval_steps=10, state_interval_steps=10),
        docking_config=DockingConfig(backend="placeholder", n_poses=1, random_seed=20260310),
        endpoint_fe_config=EndpointFreeEnergyConfig(method="placeholder"),
        membrane_config=MembraneConfig(enabled=False),
        paths=paths,
    )
    workflow = BindingWorkflow(
        context=context,
        repository=FakeRepository(),
        preprocessor=FakePreprocessor(),
        docking_engine=FakeDockingEngine(paths=paths),
        assembler=FakeAssembler(paths=paths),
        simulation_runner=FakeSimulationRunner(),
        analyzer=FakeAnalyzer(paths=paths),
    )
    result = workflow.run()

    run_manifest_path = Path(str(result.summary_metrics["run_manifest_path"]))
    assert run_manifest_path.exists()
    payload = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    assert payload["backend"] == "placeholder"
    assert payload["analysis_mode"] == "log_fallback_missing_trajectory"
    assert payload["scientific_validity"] == "placeholder_not_physical"

    route_a_summary_path = Path(str(result.summary_metrics["route_a_summary_path"]))
    assert route_a_summary_path.exists()
    summary_text = route_a_summary_path.read_text(encoding="utf-8")
    assert "Route A Summary" in summary_text
    assert "scientific_validity: placeholder_not_physical" in summary_text
    assert "for engine/workflow validation only" in summary_text
