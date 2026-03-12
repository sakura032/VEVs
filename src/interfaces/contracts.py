from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


# =========================
# Data Contracts（数据契约）
# =========================

@dataclass(slots=True)
class InputManifest:
    """输入清单（input manifest）。

    作用：
    1. 把 workflow 接收到的原始输入固定为一个标准对象。
    2. 避免函数之间传来传去一堆 Path 和零散参数。
    """

    receptor_path: Path
    ligand_path: Path
    membrane_template_path: Path | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class PreparedStructures:
    """结构准备层输出（prepared structures）。"""

    receptor_clean: Path
    ligand_prepared: Path
    preprocess_report: Path | None = None


@dataclass(slots=True)
class DockingPose:
    """单个对接姿势（single docking pose）。"""

    pose_id: int
    score: float
    rmsd: float | None = None
    pose_file: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DockingResult:
    """对接结果集合（docking result set）。"""

    poses: list[DockingPose]
    ranked_pose_table: Path | None = None
    selected_pose: DockingPose | None = None


@dataclass(slots=True)
class AssembledComplex:
    """组装后的复合体系（assembled complex artifact）。"""

    complex_structure: Path
    mode: str  # solution / membrane
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SimulationArtifacts:
    """MD 执行结果（simulation artifacts）。"""

    system_xml: Path | None = None
    initial_state_xml: Path | None = None
    minimized_structure: Path | None = None
    nvt_last_structure: Path | None = None
    npt_last_structure: Path | None = None
    trajectory: Path | None = None
    final_state_xml: Path | None = None
    log_csv: Path | None = None
    checkpoint: Path | None = None


@dataclass(slots=True)
class BindingWorkflowResult:
    """案例二 workflow 的统一输出对象。"""

    manifest: InputManifest
    prepared: PreparedStructures
    docking: DockingResult
    assembled: AssembledComplex
    simulation: SimulationArtifacts
    analysis_outputs: dict[str, Path] = field(default_factory=dict)
    summary_metrics: dict[str, float | str] = field(default_factory=dict)


# ========================================
# Protocol Contracts（面向实现的接口契约）
# ========================================

@runtime_checkable
class StructureRepositoryProtocol(Protocol):
    def validate_input_files(self, manifest: InputManifest) -> None: ...


@runtime_checkable
class StructurePreprocessorProtocol(Protocol):
    def preprocess(self, manifest: InputManifest) -> PreparedStructures: ...


@runtime_checkable
class DockingEngineProtocol(Protocol):
    def dock(self, prepared: PreparedStructures) -> DockingResult: ...


@runtime_checkable
class ComplexAssemblerProtocol(Protocol):
    def assemble(self, prepared: PreparedStructures, pose: DockingPose) -> AssembledComplex: ...


@runtime_checkable
class SimulationRunnerProtocol(Protocol):
    def prepare_system(self, assembled: AssembledComplex) -> SimulationArtifacts: ...
    def minimize(self, artifacts: SimulationArtifacts) -> SimulationArtifacts: ...
    def equilibrate(self, artifacts: SimulationArtifacts) -> SimulationArtifacts: ...
    def production(self, artifacts: SimulationArtifacts) -> SimulationArtifacts: ...
    def run_full_protocol(self, assembled: AssembledComplex) -> SimulationArtifacts: ...


@runtime_checkable
class BindingAnalyzerProtocol(Protocol):
    def analyze(self, simulation: SimulationArtifacts) -> dict[str, Path]: ...
