from __future__ import annotations

from dataclasses import dataclass
import logging

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
    BindingAnalyzerProtocol,
    BindingWorkflowResult,
    ComplexAssemblerProtocol,
    DockingEngineProtocol,
    DockingPose,
    DockingResult,
    InputManifest,
    PreparedStructures,
    SimulationRunnerProtocol,
    StructurePreprocessorProtocol,
    StructureRepositoryProtocol,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BindingWorkflowContext:
    """案例二 workflow 上下文（binding workflow context）。"""

    system_config: SystemConfig
    md_config: MDConfig
    docking_config: DockingConfig
    endpoint_fe_config: EndpointFreeEnergyConfig
    membrane_config: MembraneConfig
    paths: ProjectPaths


class BindingWorkflow:
    """案例二主工作流（case-2 binding workflow orchestrator）。

    这个类只负责“流程编排（workflow orchestration）”，
    不直接承担真实 OpenMM 计算，也不直接承担真实 docking backend 细节。

    它的核心职责是：
    1. 组织输入检查。
    2. 组织结构预处理。
    3. 组织 docking / pose ranking / pose selection。
    4. 组织复合体系组装。
    5. 调用 AA-MD runner。
    6. 汇总分析与报告。
    """

    def __init__(
        self,
        context: BindingWorkflowContext,
        repository: StructureRepositoryProtocol,
        preprocessor: StructurePreprocessorProtocol,
        docking_engine: DockingEngineProtocol,
        assembler: ComplexAssemblerProtocol,
        simulation_runner: SimulationRunnerProtocol,
        analyzer: BindingAnalyzerProtocol | None = None,
    ):
        self.context = context
        self.repository = repository
        self.preprocessor = preprocessor
        self.docking_engine = docking_engine
        self.assembler = assembler
        self.simulation_runner = simulation_runner
        self.analyzer = analyzer

    def build_manifest(self) -> InputManifest:
        """构建统一输入清单（input manifest）。"""
        cfg = self.context.system_config
        return InputManifest(
            receptor_path=cfg.receptor_path,
            ligand_path=cfg.ligand_path,
            membrane_template_path=cfg.membrane_template_path,
            metadata={
                "forcefield": cfg.forcefield_name,
                "water_model": cfg.water_model,
                "has_membrane": str(cfg.has_membrane),
            },
        )

    def validate_inputs(self, manifest: InputManifest) -> None:
        self.context.system_config.validate()
        self.context.md_config.validate()
        self.context.docking_config.validate()
        self.context.endpoint_fe_config.validate()
        self.context.membrane_config.validate()
        self.repository.validate_input_files(manifest)

    def prepare_inputs(self, manifest: InputManifest) -> PreparedStructures:
        """执行结构预处理（structure preprocessing）。"""
        logger.info("Preparing receptor/ligand input structures")
        return self.preprocessor.preprocess(manifest)

    def dock(self, prepared: PreparedStructures) -> DockingResult:
        """执行 docking。"""
        logger.info("Launching docking backend")
        return self.docking_engine.dock(prepared)

    def rank_poses(self, docking_result: DockingResult) -> DockingResult:
        """按 score 进行 pose 排序。"""
        docking_result.poses.sort(key=lambda p: p.score)
        return docking_result

    def select_pose(self, docking_result: DockingResult) -> DockingPose:
        """选择最优 pose（Phase 0 默认取 score 最低者）。

        未来 Phase 1/2 应扩展为多标准选择：
        - docking score
        - 几何合理性（geometric plausibility）
        - 生物学界面一致性（biological plausibility）
        """
        if not docking_result.poses:
            raise ValueError("No docking poses available for selection")
        best_pose = docking_result.poses[0]
        docking_result.selected_pose = best_pose
        return best_pose

    def build_complex(self, prepared: PreparedStructures, pose: DockingPose) -> AssembledComplex:
        """组装初始复合物体系。"""
        logger.info("Assembling complex structure using selected docking pose")
        return self.assembler.assemble(prepared, pose)

    def run_refinement_md(self, assembled: AssembledComplex):
        """调用 AA-MD runner 执行 refinement MD。"""
        logger.info("Running all-atom refinement MD")
        return self.simulation_runner.run_full_protocol(assembled)

    def summarize(self, result: BindingWorkflowResult) -> BindingWorkflowResult:
        """汇总 workflow 结果。

        Phase 0 只做最简占位汇总。
        未来应写入 JSON/Markdown 报告，并串联 endpoint FE 与 PMF。
        """
        if result.docking.selected_pose is not None:
            result.summary_metrics["best_docking_score"] = result.docking.selected_pose.score
        return result

    def run(self) -> BindingWorkflowResult:
        """执行完整案例二 workflow。"""
        manifest = self.build_manifest()
        self.validate_inputs(manifest)

        prepared = self.prepare_inputs(manifest)
        docking_result = self.dock(prepared)
        docking_result = self.rank_poses(docking_result)
        selected_pose = self.select_pose(docking_result)
        assembled = self.build_complex(prepared, selected_pose)
        simulation = self.run_refinement_md(assembled)

        analysis_outputs = {}
        if self.analyzer is not None:
            analysis_outputs = self.analyzer.analyze(simulation)

        result = BindingWorkflowResult(
            manifest=manifest,
            prepared=prepared,
            docking=docking_result,
            assembled=assembled,
            simulation=simulation,
            analysis_outputs=analysis_outputs,
        )
        return self.summarize(result)
