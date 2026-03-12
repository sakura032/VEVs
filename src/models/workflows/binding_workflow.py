from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path

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
        run_manifest_path = self._write_run_manifest(result)
        self._write_route_a_summary(result, run_manifest_path)
        return result

    def _resolve_analysis_mode(self, result: BindingWorkflowResult) -> str:
        """解析 analysis_mode。

        设计说明：
        1. analysis_mode 由分析层产物 metrics.json 决定，避免 workflow 猜测分析策略。
        2. 若分析层未产出该字段，回退为 not_available，保持 I/O 契约稳定。
        """
        metrics_path = result.analysis_outputs.get("metrics_json")
        if metrics_path is None or not metrics_path.exists():
            return "not_available"

        try:
            payload = json.loads(metrics_path.read_text(encoding="utf-8"))
        except Exception:
            return "not_available"
        return str(payload.get("analysis_mode", "not_available"))

    def _resolve_scientific_validity(self, result: BindingWorkflowResult) -> str:
        """解析 scientific_validity。

        设计说明：
        1. 优先读取 selected pose metadata，确保与真实 backend 输出对齐。
        2. 若 metadata 缺失且 backend=placeholder，强制给出 placeholder_not_physical。
        3. 其余 backend 默认标注 unspecified，避免伪造科学有效性结论。
        """
        selected = result.docking.selected_pose
        if selected is not None:
            value = selected.metadata.get("scientific_validity")
            if value:
                return str(value)
            backend = str(selected.metadata.get("backend", ""))
            if backend == "placeholder":
                return "placeholder_not_physical"

        if self.context.docking_config.backend == "placeholder":
            return "placeholder_not_physical"
        return "unspecified"

    def _write_run_manifest(self, result: BindingWorkflowResult) -> Path:
        """写出每次 run 的边界与可追踪清单（run_manifest.json）。"""
        metadata_dir = self.context.paths.output_dir / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        output_path = metadata_dir / "run_manifest.json"

        selected = result.docking.selected_pose
        backend = (
            str(selected.metadata.get("backend", self.context.docking_config.backend))
            if selected is not None
            else str(self.context.docking_config.backend)
        )

        payload = {
            "backend": backend,
            "analysis_mode": self._resolve_analysis_mode(result),
            "scientific_validity": self._resolve_scientific_validity(result),
        }
        output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        result.summary_metrics["run_manifest_path"] = str(output_path)
        return output_path

    def _write_route_a_summary(self, result: BindingWorkflowResult, run_manifest_path: Path) -> Path:
        """写出 Route A 人类可读总结（route_a_summary.md）。

        设计说明：
        1. 报告属于结果层，固定写到 outputs/runs/<run_id>/reports。
        2. 报告显式声明 placeholder 边界，防止误读为最终 scientific evidence。
        """
        report_dir = self.context.paths.report_dir
        report_dir.mkdir(parents=True, exist_ok=True)
        output_path = report_dir / "route_a_summary.md"

        manifest_payload = json.loads(run_manifest_path.read_text(encoding="utf-8"))
        backend = str(manifest_payload.get("backend", "unknown"))
        analysis_mode = str(manifest_payload.get("analysis_mode", "not_available"))
        scientific_validity = str(
            manifest_payload.get("scientific_validity", "unspecified")
        )

        lines = [
            "# Route A Summary",
            "",
            "## Run Scope",
            f"- mode: {result.assembled.mode}",
            f"- backend: {backend}",
            f"- analysis_mode: {analysis_mode}",
            f"- scientific_validity: {scientific_validity}",
            "",
            "## Key Outputs",
            f"- run_manifest: {run_manifest_path}",
            f"- docking_ranked_poses: {result.docking.ranked_pose_table}",
            f"- assembled_complex: {result.assembled.complex_structure}",
            f"- trajectory: {result.simulation.trajectory}",
            f"- analysis_metrics: {result.analysis_outputs.get('metrics_json')}",
            "",
            "## Boundary Statement",
        ]

        if scientific_validity == "placeholder_not_physical":
            lines.append(
                "- This run uses placeholder components and is for engine/workflow validation only."
            )
            lines.append(
                "- Scores and proxy fields must not be interpreted as publication-grade physical evidence."
            )
        else:
            lines.append(
                "- Scientific validity is backend-dependent. Check run_manifest and method details before interpretation."
            )

        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result.summary_metrics["route_a_summary_path"] = str(output_path)
        return output_path

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
