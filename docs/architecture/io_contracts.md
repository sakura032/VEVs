# VEVs Route A I/O Contracts

更新时间：2026-03-13

本文档定义当前 Route A 主链中关键输入、跨层契约、输出 artifact 的字段和语义边界。  
以 `src/interfaces/contracts.py` 与当前可运行代码为准。

## 1. Input Contracts

### 1.1 `InputManifest`

字段：
- `receptor_path: Path`
- `ligand_path: Path`
- `membrane_template_path: Path | None`
- `metadata: dict[str, str]`

生产方：
- `BindingWorkflow.build_manifest()`

消费方：
- `StructureRepository.validate_input_files()`
- `StructurePreprocessor.preprocess()`

### 1.2 Configuration Objects (`src/configs`)

#### `SystemConfig`
核心字段：
- `receptor_path`, `ligand_path`
- `forcefield_name`, `water_model`
- `temperature_kelvin`, `pressure_bar`, `ionic_strength_molar`, `ph`
- `has_membrane`
- `replace_nonstandard_residues`（新增，默认 `False`，execution 层 PDBFixer 是否替换非标准残基）

#### `MDConfig`
核心字段：
- `platform`, `precision`
- `timestep_fs`, `friction_per_ps`
- `minimize_*`, `nvt_equilibration_ns`, `npt_equilibration_ns`, `production_ns`
- `save_interval_steps`, `state_interval_steps`, `checkpoint_interval_steps`
- `random_seed`, `use_barostat`

新增字段：
- `device_index: str | None`（可选平台设备索引）
- `cpu_threads: int | None`（可选 CPU 线程数）
- `enable_pdbfixer_fix: bool`（新增，默认 `True`，execution 层 post-fix 开关）

#### `MembraneConfig`
- Route A 当前通常 `enabled=False`。

## 2. Workflow Internal Contracts

### 2.1 `PreparedStructures`
- `receptor_clean: Path`
- `ligand_prepared: Path`
- `preprocess_report: Path | None`

### 2.2 `DockingResult`
- `poses: list[DockingPose]`
- `ranked_pose_table: Path | None`
- `selected_pose: DockingPose | None`

语义边界：
- placeholder backend 的评分是 `proxy_*`，仅用于 pipeline ranking，不是发表级物理能量。

### 2.3 `AssembledComplex`
- `complex_structure: Path`
- `mode: str`（Route A 当前为 `solution`）
- `metadata: dict[str, Any]`

### 2.4 `SimulationArtifacts`
- `system_xml`
- `initial_state_xml`
- `minimized_structure`
- `nvt_last_structure`
- `npt_last_structure`
- `trajectory`
- `final_state_xml`
- `log_csv`
- `checkpoint`

## 3. Output Contracts (run_id scoped)

### 3.1 work outputs: `work/runs/<run_id>/`

- `preprocessed/receptor_clean.pdb`
- `preprocessed/ligand_prepared.pdb`
- `assembled/complex_initial.pdb`
- `md/complex_fixed.pdb`（execution-layer PDBFixer post-fix，开关开启时生成）
- `md/solvated.pdb`（solvated initial anchor）
- `md/system.xml`
- `md/state_init.xml`
- `md/minimized.pdb`
- `md/equil_nvt_last.pdb`
- `md/equil_npt_last.pdb`
- `md/production.dcd`
- `md/md_log.csv`
- `md/production.chk`
- `md/final_state.xml`

### 3.2 result outputs: `outputs/runs/<run_id>/`

- `docking/poses.csv`
- `docking/poses/pose_*.pdb`
- `analysis/binding/metrics.json`
- `analysis/binding/rmsd.csv`（trajectory 模式）
- `analysis/binding/figures/*.png`
- `metadata/preprocess_report.json`
- `metadata/md_pdbfixer_report.json`（新增，execution-layer post-fix 报告）
- `metadata/run_manifest.json`
- `reports/route_a_summary.md`

## 4. Naming and Boundary Rules

1. placeholder 分数字段必须显式使用 `proxy_*`。  
2. fallback 分析必须携带诊断标记（如 `diagnostic=true`）。  
3. `work/` 与 `outputs/` 不混用。  
4. 新增字段或新增 artifact 时，必须同步更新：
- `docs/architecture/io_contracts.md`
- `docs/architecture/route_a_workflow.md`
- `README.md`
- `TREE_3_12.md`

