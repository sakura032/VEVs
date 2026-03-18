"""
run_minimal_openmm_validation.py

Minimum runnable OpenMM validation entry.

This script validates the AA-MD engine path directly:
prepare_system -> minimize -> equilibrate -> production

It intentionally bypasses BindingWorkflow orchestration and is not a scientific
claim workflow.
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

from openmm import app

from src.configs import MDConfig, MembraneConfig, ProjectPaths, SystemConfig
from src.interfaces.contracts import AssembledComplex, SimulationArtifacts
from src.models.all_atom.simulation_runner import AllAtomSimulation, SimulationContext
from src.models.docking.pdb_utils import read_pdb_atoms, write_complex_pdb

try:
    import MDAnalysis as mda
except ImportError:
    mda = None


def resolve_input_pdb(project_root: Path, raw_path: str | Path) -> Path:
    """
    Resolve receptor/ligand input path.

    Accepted forms:
    - absolute path
    - project-root relative path
    - data-dir relative path
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run minimum OpenMM validation "
            "(prepare -> minimize -> equilibrate -> production)."
        )
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Run identifier. Default: openmm_validation_YYYYmmdd_HHMMSS",
    )
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
    return parser.parse_args()


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


def build_configs(
    receptor_path: Path,
    ligand_path: Path,
) -> tuple[SystemConfig, MDConfig, MembraneConfig]:
    system_config = SystemConfig(
        receptor_path=receptor_path,
        ligand_path=ligand_path,
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
        random_seed=20260309,
        use_barostat=True,
        use_semiisotropic_barostat=False,
    )

    membrane_config = MembraneConfig(
        enabled=False,
        lipid_composition={"POPC": 1.0},
        bilayer_size_nm=(10.0, 10.0),
        protein_orientation="auto",
        leaflet_asymmetry=False,
        water_padding_nm=1.5,
        ion_concentration_molar=0.15,
    )

    return system_config, md_config, membrane_config


def clean_component_pdb(
    input_pdb: Path,
    output_pdb: Path,
    remove_heterogens: bool,
) -> None:
    """Clean one component with role-specific heterogen handling."""
    try:
        from pdbfixer import PDBFixer
    except ImportError as exc:
        raise ImportError(
            "pdbfixer is required for test-input cleaning but is not installed."
        ) from exc

    fixer = PDBFixer(filename=str(input_pdb))
    if remove_heterogens:
        fixer.removeHeterogens(keepWater=False)
    fixer.findMissingResidues()
    fixer.findMissingAtoms()
    fixer.addMissingAtoms()

    output_pdb.parent.mkdir(parents=True, exist_ok=True)
    with open(output_pdb, "w", encoding="utf-8") as handle:
        app.PDBFile.writeFile(fixer.topology, fixer.positions, handle)


def build_test_complex(
    paths: ProjectPaths,
    receptor_path: Path,
    ligand_path: Path,
) -> AssembledComplex:
    prep_dir = paths.work_dir / "validation_inputs"
    receptor_clean = prep_dir / "receptor_validation_clean.pdb"
    ligand_prepared = prep_dir / "ligand_validation_prepared.pdb"

    clean_component_pdb(
        input_pdb=receptor_path,
        output_pdb=receptor_clean,
        remove_heterogens=True,
    )
    clean_component_pdb(
        input_pdb=ligand_path,
        output_pdb=ligand_prepared,
        remove_heterogens=False,
    )

    receptor_atoms = read_pdb_atoms(receptor_clean)
    ligand_atoms = read_pdb_atoms(ligand_prepared)

    complex_pdb = paths.work_dir / "assembled" / "complex_validation_initial.pdb"
    write_complex_pdb(receptor_atoms, ligand_atoms, complex_pdb)

    return AssembledComplex(
        complex_structure=complex_pdb,
        mode="solution",
        metadata={
            "purpose": "minimum_runnable_validation",
            "system_type": "protein_ligand_complex",
            "receptor_input": str(receptor_path),
            "ligand_input": str(ligand_path),
            "receptor_clean": str(receptor_clean),
            "ligand_prepared": str(ligand_prepared),
            "note": "Not for scientific interpretation",
        },
    )


def build_runner(
    paths: ProjectPaths,
    system_config: SystemConfig,
    md_config: MDConfig,
    membrane_config: MembraneConfig,
) -> AllAtomSimulation:
    context = SimulationContext(
        system_config=system_config,
        md_config=md_config,
        membrane_config=membrane_config,
        paths=paths,
    )
    return AllAtomSimulation(context=context)


def validate_outputs(artifacts: SimulationArtifacts) -> None:
    required = {
        "system_xml": artifacts.system_xml,
        "initial_state_xml": artifacts.initial_state_xml,
        "minimized_structure": artifacts.minimized_structure,
        "nvt_last_structure": artifacts.nvt_last_structure,
        "npt_last_structure": artifacts.npt_last_structure,
        "trajectory": artifacts.trajectory,
        "log_csv": artifacts.log_csv,
        "checkpoint": artifacts.checkpoint,
        "final_state_xml": artifacts.final_state_xml,
    }

    missing_or_empty: list[str] = []
    for name, path in required.items():
        if path is None:
            missing_or_empty.append(f"{name}: <None>")
            continue
        if not path.exists():
            missing_or_empty.append(f"{name}: {path} (missing)")
            continue
        if path.stat().st_size <= 0:
            missing_or_empty.append(f"{name}: {path} (empty)")

    if missing_or_empty:
        details = "\n".join(missing_or_empty)
        raise RuntimeError(f"Artifacts validation failed:\n{details}")


def sanity_check_trajectory(artifacts: SimulationArtifacts) -> None:
    if mda is None:
        print("MDAnalysis is not installed; skip trajectory sanity check.")
        return

    if artifacts.npt_last_structure is None or artifacts.trajectory is None:
        raise RuntimeError("Missing topology or trajectory artifact for sanity check.")

    universe = mda.Universe(str(artifacts.npt_last_structure), str(artifacts.trajectory))
    n_frames = len(universe.trajectory)
    print(f"Trajectory sanity check: n_frames = {n_frames}")
    if n_frames <= 0:
        raise RuntimeError("Trajectory sanity check failed: no frames found in DCD.")


def main() -> None:
    args = parse_args()
    project_root = PROJECT_ROOT
    run_id = args.run_id or datetime.now().strftime("openmm_validation_%Y%m%d_%H%M%S")

    receptor = resolve_input_pdb(project_root, args.receptor)
    ligand = resolve_input_pdb(project_root, args.ligand)

    print(f"Project root: {project_root}")
    print(f"Run ID: {run_id}")
    print(f"Receptor input: {receptor}")
    print(f"Ligand input: {ligand}")

    paths = build_paths(project_root, run_id=run_id)
    print(f"Work dir: {paths.work_dir}")
    print(f"Output dir: {paths.output_dir}")

    system_config, md_config, membrane_config = build_configs(receptor, ligand)
    assembled = build_test_complex(paths, receptor, ligand)
    runner = build_runner(paths, system_config, md_config, membrane_config)

    artifacts = runner.run_full_protocol(assembled=assembled, run_production=True)
    validate_outputs(artifacts)
    sanity_check_trajectory(artifacts)

    print("\nValidation succeeded. Key artifacts:")
    print(f"- system_xml: {artifacts.system_xml}")
    print(f"- initial_state_xml: {artifacts.initial_state_xml}")
    print(f"- minimized_structure: {artifacts.minimized_structure}")
    print(f"- nvt_last_structure: {artifacts.nvt_last_structure}")
    print(f"- npt_last_structure: {artifacts.npt_last_structure}")
    print(f"- trajectory: {artifacts.trajectory}")
    print(f"- log_csv: {artifacts.log_csv}")
    print(f"- checkpoint: {artifacts.checkpoint}")
    print(f"- final_state_xml: {artifacts.final_state_xml}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Validation failed: {exc}")
        traceback.print_exc()
        sys.exit(1)
