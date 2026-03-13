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
        """写出 Route A 的详细中文总结（route_a_summary.md）。

        输入：
        - `result`: 本次 workflow 运行结果对象。
        - `run_manifest_path`: 已写出的 run_manifest.json 路径。

        输出：
        - `outputs/runs/<run_id>/reports/route_a_summary.md`

        失败方式：
        - `json.JSONDecodeError`: run_manifest 或 metrics 不是合法 JSON（代码内做了容错兜底）。
        - `OSError`: 报告目录不可写时抛出。

        分层关系：
        - 该函数属于 workflow orchestration 层的“结果汇总职责”，
          不参与具体模拟与分析计算，只把跨层结果拼装成可读报告。
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

        metrics_path = result.analysis_outputs.get("metrics_json")
        metrics_payload: dict[str, object] = {}
        if metrics_path is not None and metrics_path.exists():
            try:
                metrics_payload = json.loads(metrics_path.read_text(encoding="utf-8"))
            except Exception:
                metrics_payload = {}

        run_id = self.context.paths.work_dir.name
        selected_pose = result.docking.selected_pose

        lines = [
            "# Route A Summary",
            "",
            "## 一、运行概览（Run Scope）",
            f"- run_id: {run_id}",
            f"- mode: {result.assembled.mode}",
            f"- backend: {backend}",
            f"- analysis_mode: {analysis_mode}",
            f"- scientific_validity: {scientific_validity}",
            f"- receptor_input: {result.manifest.receptor_path}",
            f"- ligand_input: {result.manifest.ligand_path}",
            "",
            "## 二、工作流流程图（Workflow Flowchart）",
            "```mermaid",
            "flowchart TD",
            "  A[输入: receptor/ligand PDB] --> B[build_manifest]",
            "  B --> C[StructureRepository.validate_input_files]",
            "  C --> D[StructurePreprocessor.preprocess]",
            "  D --> E[DockingEngine.dock]",
            "  E --> F[rank_poses + select_pose]",
            "  F --> G[ComplexAssembler.assemble]",
            "  G --> H[AllAtomSimulation.run_full_protocol]",
            "  H --> I[BindingAnalyzer.analyze]",
            "  I --> J[write run_manifest.json]",
            "  J --> K[write route_a_summary.md]",
            "```",
            "",
            "## 三、逐步执行说明（输入/调用模块/输出）",
            "",
            "| 步骤 | 调用模块 | 输入 | 输出 |",
            "| --- | --- | --- | --- |",
            "| 1. 构建清单 | `src/models/workflows/binding_workflow.py::build_manifest` | `SystemConfig` | `InputManifest`（内存对象） |",
            "| 2. 输入校验 | `src/utils/structure_repository.py::validate_input_files` | `InputManifest` | 输入文件存在性与格式检查结果 |",
            "| 3. 结构预处理 | `src/utils/structure_preprocessor.py::preprocess` | receptor/ligand 原始结构 | `work/runs/<run_id>/preprocessed/*` + `outputs/runs/<run_id>/metadata/preprocess_report.json` |",
            "| 4. docking | `src/models/docking/placeholder_engine.py::dock` | 预处理结构 | `outputs/runs/<run_id>/docking/poses.csv` + `outputs/runs/<run_id>/docking/poses/pose_*.pdb` |",
            "| 5. pose 排序/选择 | `binding_workflow.py::rank_poses/select_pose` | docking poses | `selected_pose`（内存对象） |",
            "| 6. complex 组装 | `src/utils/complex_assembler.py::assemble` | receptor + selected_pose | `work/runs/<run_id>/assembled/complex_initial.pdb` |",
            "| 7. MD 执行 | `src/models/all_atom/simulation_runner.py::run_full_protocol` | `AssembledComplex` | `work/runs/<run_id>/md/*` + `outputs/runs/<run_id>/metadata/md_pdbfixer_report.json` |",
            "| 8. 分析 | `src/analysis/binding_analyzer.py::analyze` | trajectory + topology/log | `outputs/runs/<run_id>/analysis/binding/*` |",
            "| 9. 汇总 | `binding_workflow.py::summarize` | 各阶段结果对象 | `metadata/run_manifest.json` + `reports/route_a_summary.md` |",
            "",
            "## 四、关键输出文件与作用",
            f"- run_manifest.json: {run_manifest_path}",
            "  - 作用：记录本次 run 的边界属性（backend / analysis_mode / scientific_validity），避免误读。",
            f"- metrics.json: {metrics_path}",
            "  - 作用：记录分析阶段核心指标（如 RMSD 统计、analysis_mode、metrics_semantics）。",
            f"- preprocess_report.json: {result.prepared.preprocess_report}",
            "  - 作用：记录预处理阶段清洗与输入校验信息。",
            f"- md_pdbfixer_report.json: {self.context.paths.output_dir / 'metadata' / 'md_pdbfixer_report.json'}",
            "  - 作用：记录 execution 层 PDBFixer 的修复行为，便于追踪潜在结构变化。",
            f"- assembled complex: {result.assembled.complex_structure}",
            "  - 作用：组装后的复合体初始结构，作为 MD 输入锚点。",
            f"- production trajectory: {result.simulation.trajectory}",
            "  - 作用：生产期轨迹（DCD），用于后续结构动力学分析。",
            f"- md_log.csv: {result.simulation.log_csv}",
            "  - 作用：记录 step 级温度/能量等时间序列，用于数值稳定性诊断。",
            "",
            "## 五、JSON 文件读法（本次 run 实例）",
            "### 1) run_manifest.json",
            "```json",
            json.dumps(manifest_payload, ensure_ascii=False, indent=2),
            "```",
            "- `backend`：本次 docking 后端标识。",
            "- `analysis_mode`：分析层实际采用的模式。",
            "- `scientific_validity`：科学有效性声明；`placeholder_not_physical` 代表不能作为发表级物理证据。",
            "",
            "### 2) metrics.json",
            "```json",
            json.dumps(metrics_payload, ensure_ascii=False, indent=2),
            "```",
            "- 常见字段解释：",
            "  - `n_frames`：读取到的轨迹帧数。",
            "  - `rmsd_mean_angstrom` / `rmsd_max_angstrom` / `rmsd_min_angstrom`：RMSD 统计量。",
            "  - `analysis_mode`：`trajectory` 表示指标由轨迹直接计算。",
            "  - `metrics_semantics`：指标语义声明，`physical_trajectory_derived` 表示来自真实轨迹。",
            "",
            "## 六、归档建议（Archive Recommendation）",
            "- 建议长期保留：",
            "  1. `outputs/runs/<run_id>/docking/`",
            "  2. `outputs/runs/<run_id>/analysis/binding/`",
            "  3. `outputs/runs/<run_id>/metadata/*.json`",
            "  4. `outputs/runs/<run_id>/reports/route_a_summary.md`",
            "  5. `work/runs/<run_id>/md/production.dcd` 与 `work/runs/<run_id>/md/md_log.csv`",
            "- WSL/Linux 打包示例：",
            "```bash",
            "tar -czf outputs/archive/route_a_<run_id>.tar.gz \\",
            "  outputs/runs/<run_id>/docking \\",
            "  outputs/runs/<run_id>/analysis/binding \\",
            "  outputs/runs/<run_id>/metadata \\",
            "  outputs/runs/<run_id>/reports \\",
            "  work/runs/<run_id>/md/production.dcd \\",
            "  work/runs/<run_id>/md/md_log.csv",
            "```",
            "- Windows PowerShell 打包示例：",
            "```powershell",
            "Compress-Archive -Path \\",
            "  outputs/runs/<run_id>/docking, \\",
            "  outputs/runs/<run_id>/analysis/binding, \\",
            "  outputs/runs/<run_id>/metadata, \\",
            "  outputs/runs/<run_id>/reports, \\",
            "  work/runs/<run_id>/md/production.dcd, \\",
            "  work/runs/<run_id>/md/md_log.csv \\",
            "  -DestinationPath outputs/archive/route_a_<run_id>.zip",
            "```",
            "",
            "## 七、Boundary Statement",
        ]

        if selected_pose is not None:
            lines.extend(
                [
                    f"- selected_pose_id: {selected_pose.pose_id}",
                    f"- selected_pose_score: {selected_pose.score}",
                    f"- selected_pose_file: {selected_pose.pose_file}",
                ]
            )

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

