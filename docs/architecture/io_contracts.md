# VEVs I/O Contracts

更新时间：2026-03-11

本文件定义当前仓库 Route A 主线的 I/O contract（字段、格式、示例），以 `src/interfaces/contracts.py` 与实际产物为准。

## 1. 输入契约（Input）

### 1.1 `InputManifest`

- 字段：
  - `receptor_path: Path`
  - `ligand_path: Path`
  - `membrane_template_path: Path | None`
  - `metadata: dict[str, str]`
- 生产者：`BindingWorkflow.build_manifest()`
- 消费者：`StructureRepository.validate_input_files()`、`StructurePreprocessor.preprocess()`

### 1.2 配置对象（`src/configs`）

- `SystemConfig`：体系与输入路径、力场、水模型、温压、`has_membrane`
- `MDConfig`：最小化/平衡/生产时长、平台、reporter 采样间隔
- `DockingConfig`：backend、n_poses、seed、score_cutoff
- `EndpointFreeEnergyConfig`：当前仅配置层，占位 method 可为 `placeholder`
- `MembraneConfig`：当前 Route A 中通常 `enabled=False`

## 2. 中间契约（Workflow Internal）

### 2.1 `PreparedStructures`

- 字段：
  - `receptor_clean: Path`
  - `ligand_prepared: Path`
  - `preprocess_report: Path | None`
- 约定输出：
  - `work/runs/<run_id>/preprocessed/receptor_clean.pdb`
  - `work/runs/<run_id>/preprocessed/ligand_prepared.pdb`
  - `outputs/runs/<run_id>/metadata/preprocess_report.json`

### 2.2 `DockingResult`

- 字段：
  - `poses: list[DockingPose]`
  - `ranked_pose_table: Path | None`
  - `selected_pose: DockingPose | None`
- placeholder 结果语义：
  - 分数为 proxy 排序分，不是发表级物理能量

### 2.3 `AssembledComplex`

- 字段：
  - `complex_structure: Path`
  - `mode: str`（当前 Route A 为 `solution`）
  - `metadata: dict[str, Any]`

### 2.4 `SimulationArtifacts`

- 关键路径字段：
  - `system_xml`
  - `initial_state_xml`
  - `minimized_structure`
  - `nvt_last_structure`
  - `npt_last_structure`
  - `trajectory`
  - `final_state_xml`
  - `log_csv`
  - `checkpoint`

## 3. 输出契约（Output）

### 3.1 Docking 结果表 `poses.csv`

路径：
- `outputs/runs/<run_id>/docking/poses.csv`

关键字段：
- `backend`
- `scientific_validity`
- `score_semantics`
- `proxy_vdw_score`
- `proxy_electrostatic_score`
- `proxy_distance_penalty`

说明：
- `proxy_*` 字段仅用于 pipeline validation 与相对排序，不可作为最终物理结论。

### 3.2 分析指标 `metrics.json`

路径：
- `outputs/runs/<run_id>/analysis/binding/metrics.json`

关键字段（轨迹成功时）：
- `analysis_mode=trajectory`
- `metrics_semantics=physical_trajectory_derived`

关键字段（fallback 时）：
- `analysis_mode=log_fallback_*`
- `metrics_semantics=diagnostic_not_physical`
- `diagnostic="true"`

### 3.3 运行清单 `run_manifest.json`

路径：
- `outputs/runs/<run_id>/metadata/run_manifest.json`

固定字段：
- `backend`
- `analysis_mode`
- `scientific_validity`

示例：

```json
{
  "backend": "placeholder",
  "analysis_mode": "log_fallback_missing_trajectory",
  "scientific_validity": "placeholder_not_physical"
}
```

### 3.4 人类可读总结 `route_a_summary.md`

路径：
- `outputs/runs/<run_id>/reports/route_a_summary.md`

固定内容：
- run scope（mode/backend/analysis_mode/scientific_validity）
- key outputs（manifest、poses、assembled、trajectory、metrics）
- boundary statement（placeholder 时强制写明非科学结论）

## 4. 命名与边界规则

- 规则 1：placeholder 指标必须显式命名为 `proxy_*`。
- 规则 2：fallback 指标必须带 `diagnostic` 标记。
- 规则 3：`work/` 与 `outputs/` 不混用（过程产物与结果产物分离）。
- 规则 4：新增结果字段时，必须同步更新本文件与 README/TREE。

