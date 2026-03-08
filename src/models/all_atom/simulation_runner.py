from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging

from src.configs import MDConfig, MembraneConfig, ProjectPaths, SystemConfig
from src.interfaces.contracts import AssembledComplex, SimulationArtifacts

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SimulationContext:
    """AA-MD 运行上下文（simulation context）。

    作用：
    1. 把 runner 运行时需要的配置打包。
    2. 避免 prepare/minimize/equilibrate/production 每一步都传散乱参数。
    """

    system_config: SystemConfig
    md_config: MDConfig
    membrane_config: MembraneConfig
    paths: ProjectPaths


class AllAtomSimulation:
    """全原子模拟执行器（AA-MD execution façade）。

    Phase 0 的职责不是实现完整 OpenMM，而是把调用边界先钉死：
    - prepare_system()
    - minimize()
    - equilibrate()
    - production()

    到 Phase 1 时，再把这些方法内部替换为真实 OpenMM 代码。
    """

    def __init__(self, context: SimulationContext):
        self.context = context
        self.paths = context.paths
        self.paths.ensure_dirs()

    def prepare_system(self, assembled: AssembledComplex) -> SimulationArtifacts:
        """准备 OpenMM 体系（prepare OpenMM system）。

        Phase 0:
        - 只生成标准输出路径与占位工件（artifacts）。
        - 不做真实 system building。

        Phase 1:
        - 读入 PDB/complex structure。
        - 调用 OpenMM Modeller / ForceField / System builder。
        - 输出 system.xml 与 initial_state.xml。
        """
        logger.info("Preparing OpenMM system for %s", assembled.complex_structure)

        md_dir = self.paths.work_dir / "md"
        md_dir.mkdir(parents=True, exist_ok=True)

        return SimulationArtifacts(
            system_xml=md_dir / "system.xml",
            initial_state_xml=md_dir / "state_init.xml",
            minimized_structure=md_dir / "minimized.pdb",
            nvt_last_structure=md_dir / "equil_nvt_last.pdb",
            npt_last_structure=md_dir / "equil_npt_last.pdb",
            trajectory=md_dir / "production.dcd",
            final_state_xml=md_dir / "final_state.xml",
            log_csv=md_dir / "md_log.csv",
            checkpoint=md_dir / "production.chk",
        )

    def minimize(self, artifacts: SimulationArtifacts) -> SimulationArtifacts:
        """能量最小化（energy minimization）。"""
        logger.info(
            "Minimization placeholder: will later write minimized structure to %s",
            artifacts.minimized_structure,
        )
        return artifacts

    def equilibrate(self, artifacts: SimulationArtifacts) -> SimulationArtifacts:
        """平衡阶段（equilibration）。

        这里明确分成 NVT 和 NPT 两个产物路径，
        是为了后续 membrane protocol 可以替换为更复杂的约束释放与半各向异性压强方案。
        """
        logger.info(
            "Equilibration placeholder: NVT -> %s, NPT -> %s",
            artifacts.nvt_last_structure,
            artifacts.npt_last_structure,
        )
        return artifacts

    def production(self, artifacts: SimulationArtifacts) -> SimulationArtifacts:
        """生产模拟（production MD）。"""
        logger.info(
            "Production placeholder: trajectory -> %s, final state -> %s",
            artifacts.trajectory,
            artifacts.final_state_xml,
        )
        return artifacts

    def run_full_protocol(self, assembled: AssembledComplex) -> SimulationArtifacts:
        """执行完整 AA-MD protocol。"""
        artifacts = self.prepare_system(assembled)
        artifacts = self.minimize(artifacts)
        artifacts = self.equilibrate(artifacts)
        artifacts = self.production(artifacts)
        return artifacts
