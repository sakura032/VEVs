"""
run_binding_route_a.py

Minimum runnable Route A workflow entry.

This script wires concrete components into BindingWorkflow and executes:
validate -> preprocess -> dock -> select pose -> assemble -> run MD -> analyze -> summarize.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys
import traceback


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import BindingAnalyzer
from src.configs import (
    DockingConfig,
    EndpointFreeEnergyConfig,
    MDConfig,
    MembraneConfig,
    ProjectPaths,
    SystemConfig,
)
from src.models.docking import PlaceholderDockingEngine, summarize_docking_result, validate_docking_result
from src.models.workflows import BindingWorkflow, BindingWorkflowContext
from src.utils import ComplexAssembler, StructurePreprocessor, StructureRepository


def resolve_input_pdb(project_root: Path, raw_path: str | Path) -> Path:
    """
    Resolve user-provided receptor/ligand path with data-relative convenience.

    Accepted forms:
    - absolute path
    - project-root relative path (for example: data/test_systems/xxx.pdb)
    - data-dir relative path (for example: test_systems/test_3_15/receptor_one.pdb)
    """
    path = Path(raw_path)
    if path.is_absolute():
        resolved = path.resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Input PDB not found: {resolved}")
        return resolved

    candidates = [
        (project_root / path).resolve(),
        (project_root / "data" / path).resolve(),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    candidate_text = "\n".join(f"- {candidate}" for candidate in candidates)
    raise FileNotFoundError(
        "Input PDB not found. Tried:\n"
        f"{candidate_text}\n"
        f"raw input: {raw_path}"
    )


def build_paths(project_root: Path, run_id: str) -> ProjectPaths:
    run_work_dir = project_root / "work" / "runs" / run_id
    run_output_dir = project_root / "outputs" / "runs" / run_id
    paths = ProjectPaths(
        project_root=project_root,
        data_dir=project_root / "data",
        work_dir=run_work_dir,
        output_dir=run_output_dir,
        log_dir=run_output_dir / "logs",
        report_dir=run_output_dir / "reports",
    )
    paths.ensure_dirs()
    return paths


def build_configs(project_root: Path, receptor: Path, ligand: Path) -> tuple[
    SystemConfig,
    MDConfig,
    DockingConfig,
    EndpointFreeEnergyConfig,
    MembraneConfig,
]:
    system_config = SystemConfig(
        receptor_path=receptor,
        ligand_path=ligand,
        forcefield_name="amber14sb",
        water_model="tip3p",
        temperature_kelvin=300.0,
        pressure_bar=1.0,
        ionic_strength_molar=0.1,
        ph=7.0,
        has_membrane=False,
    )
    md_config = MDConfig(
        platform="CPU",
        precision="single",
        timestep_fs=2.0,
        friction_per_ps=1.0,
        minimize_max_iterations=200,
        minimize_tolerance_kj_mol_nm=10.0,
        nvt_equilibration_ns=0.005,
        npt_equilibration_ns=0.005,
        production_ns=0.01,
        save_interval_steps=1000,
        state_interval_steps=100,
        checkpoint_interval_steps=1000,
        random_seed=20260310,
        use_barostat=True,
        use_semiisotropic_barostat=False,
    )
    docking_config = DockingConfig(
        backend="placeholder",
        method="rigid",
        n_poses=10,
        random_seed=20260310,
    )
    endpoint_fe_config = EndpointFreeEnergyConfig(method="placeholder", frame_stride=10)
    membrane_config = MembraneConfig(enabled=False)
    return system_config, md_config, docking_config, endpoint_fe_config, membrane_config


def build_workflow(
    paths: ProjectPaths,
    system_config: SystemConfig,
    md_config: MDConfig,
    docking_config: DockingConfig,
    endpoint_fe_config: EndpointFreeEnergyConfig,
    membrane_config: MembraneConfig,
) -> BindingWorkflow:
    from src.models.all_atom import AllAtomSimulation, SimulationContext

    context = BindingWorkflowContext(
        system_config=system_config,
        md_config=md_config,
        docking_config=docking_config,
        endpoint_fe_config=endpoint_fe_config,
        membrane_config=membrane_config,
        paths=paths,
    )
    repository = StructureRepository(paths=paths)
    preprocessor = StructurePreprocessor(paths=paths, keep_water=False)
    docking_engine = PlaceholderDockingEngine(docking_config=docking_config, paths=paths)
    assembler = ComplexAssembler(paths=paths)
    simulation_runner = AllAtomSimulation(
        context=SimulationContext(
            system_config=system_config,
            md_config=md_config,
            membrane_config=membrane_config,
            paths=paths,
        )
    )
    analyzer = BindingAnalyzer(paths=paths)
    return BindingWorkflow(
        context=context,
        repository=repository,
        preprocessor=preprocessor,
        docking_engine=docking_engine,
        assembler=assembler,
        simulation_runner=simulation_runner,
        analyzer=analyzer,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run minimum Route A binding workflow")
    parser.add_argument(
        "--receptor",
        type=str,
        default="test_systems/test_3_15/receptor_one.pdb",
        help=(
            "Receptor PDB path. Supports absolute path, project-root relative path, "
            "or data-dir relative path."
        ),
    )
    parser.add_argument(
        "--ligand",
        type=str,
        default="test_systems/test_3_15/ligand_one.pdb",
        help=(
            "Ligand PDB path. Supports absolute path, project-root relative path, "
            "or data-dir relative path."
        ),
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Run identifier. Default: routeA_YYYYmmdd_HHMMSS",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = PROJECT_ROOT
    receptor = resolve_input_pdb(project_root, args.receptor)
    ligand = resolve_input_pdb(project_root, args.ligand)
    run_id = args.run_id or datetime.now().strftime("routeA_%Y%m%d_%H%M%S")

    paths = build_paths(project_root, run_id=run_id)
    system_config, md_config, docking_config, endpoint_fe_config, membrane_config = build_configs(
        project_root=project_root,
        receptor=receptor,
        ligand=ligand,
    )
    workflow = build_workflow(
        paths=paths,
        system_config=system_config,
        md_config=md_config,
        docking_config=docking_config,
        endpoint_fe_config=endpoint_fe_config,
        membrane_config=membrane_config,
    )

    result = workflow.run()
    validate_docking_result(result.docking, require_pose_files=True)
    docking_summary = summarize_docking_result(result.docking)

    print("Route A workflow finished successfully.")
    print(f"- run_id: {run_id}")
    print(f"- run work dir: {paths.work_dir}")
    print(f"- run output dir: {paths.output_dir}")
    print(f"- manifest receptor: {result.manifest.receptor_path}")
    print(f"- manifest ligand: {result.manifest.ligand_path}")
    print(f"- docking poses: {len(result.docking.poses)}")
    print(f"- docking summary: {docking_summary}")
    if result.assembled.complex_structure:
        print(f"- assembled complex: {result.assembled.complex_structure}")
    if result.simulation.trajectory:
        print(f"- production trajectory: {result.simulation.trajectory}")
    if result.analysis_outputs:
        for name, path in result.analysis_outputs.items():
            print(f"- analysis {name}: {path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Route A workflow failed: {exc}")
        traceback.print_exc()
        sys.exit(1)
