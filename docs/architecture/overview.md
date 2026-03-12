# VEVs Architecture Overview

更新时间：2026-03-11

本文件把 `casetwo.md` 的顶层设计转成“当前仓库可执行现实”的工程说明，避免设计信息散落在对话与提交记录里。

## 1. 当前阶段定位

- 当前主线：`Phase 1`（Route A 最小可运行闭环）。
- 已具备：`BindingWorkflow` 编排 + `AllAtomSimulation` 真实 OpenMM 执行 + 最小分析 + 结果边界标记。
- 未具备：`MembraneBindingWorkflow`、`EndpointFreeEnergyEstimator`、`UmbrellaSamplingWorkflow` 的真实实现。

## 2. 分层边界（Layer Boundaries）

1. Structure Preparation（结构准备层）
- 目录：`src/utils/`
- 组件：`StructureRepository`、`StructurePreprocessor`、`ComplexAssembler`
- 职责：输入校验、结构清洗、复合体组装、预处理元数据产出
- 禁止：写 OpenMM 积分与分析统计逻辑

2. MD Execution（模拟执行层）
- 目录：`src/models/all_atom/`
- 组件：`AllAtomSimulation`
- 职责：`prepare_system -> minimize -> equilibrate -> production`，生成 MD artifacts
- 禁止：承担 workflow 编排与科学结论解释

3. Scientific Workflow（工作流编排层）
- 目录：`src/models/workflows/`
- 组件：`BindingWorkflow`
- 职责：串联 repository/preprocessor/docking/assembler/MD/analyzer，产出 run manifest 与 summary
- 禁止：重写第二套 OpenMM engine

4. Trajectory / Analysis（分析层）
- 目录：`src/analysis/`
- 组件：`BindingAnalyzer`
- 职责：优先基于真实轨迹分析；必要时进入 log fallback，并显式标记 `diagnostic`
- 禁止：伪造物理结果、隐藏 fallback 语义

## 3. 目录约定（Directory Conventions）

顶层代码目录：

- `src/configs`：配置 dataclass
- `src/interfaces`：数据契约与 Protocol 接口
- `src/models`：工作流与执行器
- `src/utils`：结构准备组件
- `src/analysis`：分析组件

运行产物目录（run_id 隔离）：

- `work/runs/<run_id>/...`：过程产物（preprocessed、assembled、md）
- `outputs/runs/<run_id>/...`：结果产物（docking、analysis、metadata、reports、logs）

## 4. 核心抽象（Core Abstractions）

核心数据契约位于 `src/interfaces/contracts.py`：

- `InputManifest`
- `PreparedStructures`
- `DockingPose` / `DockingResult`
- `AssembledComplex`
- `SimulationArtifacts`
- `BindingWorkflowResult`

核心接口（Protocol）：

- `StructureRepositoryProtocol`
- `StructurePreprocessorProtocol`
- `DockingEngineProtocol`
- `ComplexAssemblerProtocol`
- `SimulationRunnerProtocol`
- `BindingAnalyzerProtocol`

## 5. Route A 到 Route B 的可升级性约束

- 当前 Route A 为 `solution mode` 主线。
- `SystemConfig.has_membrane`、`MembraneConfig` 已存在，作为 Phase 2 的扩展锚点。
- 当前 `AllAtomSimulation` 对 membrane mode 明确抛 `NotImplementedError`，属于“边界诚实”而非“假实现”。

## 6. Scientific Honesty（科学边界声明）

当前仓库允许 placeholder，但必须显式标记，且不得冒充真实 scientific evidence：

- docking 产物需携带 `scientific_validity` 与 `score_semantics`
- proxy 指标采用 `proxy_*` 命名
- fallback 分析必须写入 `metrics_semantics=diagnostic_not_physical`

