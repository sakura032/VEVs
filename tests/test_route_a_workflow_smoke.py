from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from src.analysis import BindingAnalyzer
from src.configs import (
    DockingConfig,
    EndpointFreeEnergyConfig,
    MDConfig,
    MembraneConfig,
    ProjectPaths,
    SystemConfig,
)
from src.interfaces.contracts import AssembledComplex, BindingWorkflowResult, SimulationArtifacts
from src.models.docking import PlaceholderDockingEngine
from src.models.workflows import BindingWorkflow, BindingWorkflowContext
from src.utils import ComplexAssembler, StructurePreprocessor, StructureRepository


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


class FakeSimulationRunner:
    """Route A wiring smoke: avoid OpenMM dependency during unit-level integration test."""

    def __init__(self, paths: ProjectPaths):
        self.paths = paths
        self.paths.ensure_dirs()

    def run_full_protocol(self, assembled: AssembledComplex) -> SimulationArtifacts:
        md_dir = self.paths.work_dir / "md"
        md_dir.mkdir(parents=True, exist_ok=True)
        npt_last = md_dir / "equil_npt_last.pdb"
        traj = md_dir / "production.dcd"
        log_csv = md_dir / "md_log.csv"

        shutil.copy2(assembled.complex_structure, npt_last)
        traj.write_bytes(b"DCD")
        log_csv.write_text(
            "step,time,temperature,potentialEnergy\n"
            "0,0.0,300.0,-100.0\n"
            "100,0.2,300.5,-99.0\n",
            encoding="utf-8",
        )

        return SimulationArtifacts(
            npt_last_structure=npt_last,
            trajectory=traj,
            log_csv=log_csv,
        )


def test_route_a_workflow_smoke() -> None:
    pytest.importorskip("pdbfixer")
    pytest.importorskip("openmm")

    root = _new_temp_root("route_a_workflow_smoke")
    receptor = root / "data" / "receptor.pdb"
    ligand = root / "data" / "ligand.pdb"
    _write_pdb(receptor, "A")
    _write_pdb(ligand, "L")

    paths = ProjectPaths.from_root(root)
    system_config = SystemConfig(
        receptor_path=receptor,
        ligand_path=ligand,
        has_membrane=False,
    )
    md_config = MDConfig(platform="CPU", production_ns=0.001, save_interval_steps=10, state_interval_steps=10)
    docking_config = DockingConfig(backend="placeholder", n_poses=4, random_seed=20260310)
    endpoint_fe = EndpointFreeEnergyConfig(method="placeholder")
    membrane = MembraneConfig(enabled=False)

    context = BindingWorkflowContext(
        system_config=system_config,
        md_config=md_config,
        docking_config=docking_config,
        endpoint_fe_config=endpoint_fe,
        membrane_config=membrane,
        paths=paths,
    )

    workflow = BindingWorkflow(
        context=context,
        repository=StructureRepository(paths=paths),
        preprocessor=StructurePreprocessor(paths=paths),
        docking_engine=PlaceholderDockingEngine(docking_config=docking_config, paths=paths),
        assembler=ComplexAssembler(paths=paths),
        simulation_runner=FakeSimulationRunner(paths=paths),
        analyzer=BindingAnalyzer(paths=paths),
    )
    result = workflow.run()

    assert isinstance(result, BindingWorkflowResult)
    assert result.assembled.complex_structure.exists()
    assert len(result.docking.poses) > 0
    assert "best_docking_score" in result.summary_metrics
    assert "metrics_json" in result.analysis_outputs
    assert result.analysis_outputs["metrics_json"].exists()
    assert "run_manifest_path" in result.summary_metrics

    run_manifest_path = Path(str(result.summary_metrics["run_manifest_path"]))
    assert run_manifest_path.exists()
    payload = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    assert payload["backend"] == "placeholder"
    assert payload["scientific_validity"] == "placeholder_not_physical"
    assert payload["analysis_mode"] in {
        "trajectory",
        "log_fallback_after_trajectory_error",
        "log_fallback_missing_trajectory",
        "not_available",
    }
