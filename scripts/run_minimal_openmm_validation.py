"""
run_minimal_openmm_validation.py

目的：
1. 对 simulation_runner.py 做 minimum runnable validation。
2. 不经过 BindingWorkflow，直接测试 OpenMM 主链：
   prepare_system -> minimize -> equilibrate -> production
3. 仅支持 CPU / solution mode / toy peptide complex。
4. 这是 engine validation，不是 scientific validation。
"""

from pathlib import Path
import sys
import traceback


# 允许从项目根目录导入 src 包（python scripts/xxx.py 时默认路径是 scripts/）
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.configs import MDConfig, MembraneConfig, ProjectPaths, SystemConfig
from src.interfaces.contracts import AssembledComplex, SimulationArtifacts
from src.models.all_atom.simulation_runner import AllAtomSimulation, SimulationContext
from openmm import app

try:
    import MDAnalysis as mda
except ImportError:
    mda = None


def build_paths(project_root: Path) -> ProjectPaths:
    """构造项目路径对象并确保目录存在。"""
    paths = ProjectPaths.from_root(project_root)
    paths.ensure_dirs()
    return paths


def build_configs(project_root: Path) -> tuple[SystemConfig, MDConfig, MembraneConfig]:
    """构造最小验证配置（minimum runnable validation configs）。"""
    minimal_pdb = (
        project_root
        / "data"
        / "test_systems"
        / "minimal_complex"
        / "minimal_complex.pdb"
    )
    if not minimal_pdb.exists():
        raise FileNotFoundError(f"Test PDB not found: {minimal_pdb}")

    # 说明：当前脚本不走 docking/workflow，但 SystemConfig 需要 receptor/ligand 两个字段；
    # 这里临时都指向同一个 minimal complex，作为 contract placeholder。
    system_config = SystemConfig(
        receptor_path=minimal_pdb,
        ligand_path=minimal_pdb,
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


def prepare_clean_test_input(project_root: Path) -> Path:
    """用 pdbfixer 对测试输入做最小预清洗，输出 clean PDB 路径。"""
    raw_pdb = (
        project_root
        / "data"
        / "test_systems"
        / "minimal_complex"
        / "minimal_complex.pdb"
    )
    clean_pdb = (
        project_root
        / "data"
        / "test_systems"
        / "minimal_complex"
        / "minimal_complex_clean.pdb"
    )

    if not raw_pdb.exists():
        raise FileNotFoundError(f"Test PDB not found: {raw_pdb}")

    try:
        from pdbfixer import PDBFixer
    except ImportError as exc:
        raise ImportError(
            "pdbfixer is required for test-input cleaning but is not installed."
        ) from exc

    fixer = PDBFixer(filename=str(raw_pdb))
    fixer.removeHeterogens(keepWater=False)
    fixer.findMissingResidues()
    fixer.findMissingAtoms()
    fixer.addMissingAtoms()

    clean_pdb.parent.mkdir(parents=True, exist_ok=True)
    with open(clean_pdb, "w", encoding="utf-8") as handle:
        app.PDBFile.writeFile(fixer.topology, fixer.positions, handle)

    return clean_pdb


def build_test_complex(project_root: Path) -> AssembledComplex:
    """构造 solution mode 的最小 AssembledComplex。"""
    minimal_pdb = prepare_clean_test_input(project_root)
    return AssembledComplex(
        complex_structure=minimal_pdb,
        mode="solution",
        metadata={
            "purpose": "minimum_runnable_validation",
            "system_type": "toy_peptide_complex",
            "note": "Not for scientific interpretation",
        },
    )


def build_runner(
    paths: ProjectPaths,
    system_config: SystemConfig,
    md_config: MDConfig,
    membrane_config: MembraneConfig,
) -> AllAtomSimulation:
    """构造 SimulationContext 和 AllAtomSimulation。"""
    context = SimulationContext(
        system_config=system_config,
        md_config=md_config,
        membrane_config=membrane_config,
        paths=paths,
    )
    return AllAtomSimulation(context=context)


def validate_outputs(artifacts: SimulationArtifacts) -> None:
    """验证关键 artifacts 是否存在且非空。"""
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
    """做轨迹 sanity check：确认 DCD 可读且帧数 > 0。"""
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
    """按固定顺序执行 minimum runnable validation。"""
    project_root = Path(__file__).resolve().parents[1]
    print(f"Project root: {project_root}")

    paths = build_paths(project_root)
    system_config, md_config, membrane_config = build_configs(project_root)
    assembled = build_test_complex(project_root)
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
