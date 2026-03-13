# VEVs Project Tree (Updated 2026-03-13)

目标：给首次接手同伴快速建立“目录-职责-入口-产物”的对应关系。

## 1. Top-Level Tree

```text
VEVs/
├─ src/
│  ├─ configs/
│  ├─ interfaces/
│  ├─ models/
│  │  ├─ all_atom/
│  │  ├─ docking/
│  │  └─ workflows/
│  ├─ utils/
│  └─ analysis/
├─ scripts/
│  ├─ cleanup_pytest_temp.sh
│  ├─ run_binding_route_a.py
│  └─ run_minimal_openmm_validation.py
├─ tests/
├─ docs/architecture/
├─ data/
├─ work/
│  ├─ runs/<run_id>/
│  └─ archive/legacy_*/
├─ outputs/
│  ├─ runs/<run_id>/
│  └─ archive/legacy_*/
├─ casetwo.md
├─ deepresearch3_10.md
├─ ONBOARDING.md
└─ README.md
```

## 2. Directory Responsibility

- `src/configs`：参数定义与校验。
- `src/interfaces/contracts.py`：跨层 I/O 契约与 Protocol。
- `src/models/workflows`：流程编排（orchestration）。
- `src/models/all_atom`：OpenMM 执行（prepare/minimize/equilibrate/production）。
- `src/models/docking`：docking 子模块（当前 backend 为 placeholder）。
- `src/utils`：输入校验、预处理、组装。
- `src/analysis`：轨迹分析与结果导出。
- `work/runs/<run_id>`：过程产物。
- `outputs/runs/<run_id>`：结果产物。

## 3. Runtime Entrypoints

1. Route A 主入口  
`python scripts/run_binding_route_a.py --run-id <run_id> --receptor <pdb> --ligand <pdb>`

2. OpenMM 主链验证入口  
`python scripts/run_minimal_openmm_validation.py --run-id <run_id>`

3. 关键回归  
`python -m pytest -q -rs tests/test_route_a_workflow_smoke.py tests/test_run_manifest_smoke.py tests/test_binding_analyzer_smoke.py`

## 4. New MD Artifacts (2026-03-13)

在 `work/runs/<run_id>/md/` 新增：
- `complex_fixed.pdb`（execution-layer PDBFixer post-fix）
- `solvated.pdb`（加溶剂后初态结构锚点）

在 `outputs/runs/<run_id>/metadata/` 新增：
- `md_pdbfixer_report.json`（post-fix 报告）

## 5. 输出结构对比（你要求的两个 TREE）

### 5.1 `run_binding_route_a.py` 运行成功后的输出

```text
work/runs/<run_id>/
├─ preprocessed/
│  ├─ receptor_clean.pdb
│  └─ ligand_prepared.pdb
├─ assembled/
│  └─ complex_initial.pdb
└─ md/
   ├─ complex_fixed.pdb
   ├─ solvated.pdb
   ├─ system.xml
   ├─ state_init.xml
   ├─ minimized.pdb
   ├─ equil_nvt_last.pdb
   ├─ equil_npt_last.pdb
   ├─ production.dcd
   ├─ md_log.csv
   ├─ production.chk
   └─ final_state.xml
```

```text
outputs/runs/<run_id>/
├─ docking/
│  ├─ poses.csv
│  └─ poses/
│     └─ pose_*.pdb
├─ analysis/
│  └─ binding/
│     ├─ metrics.json
│     ├─ rmsd.csv
│     └─ figures/
│        └─ rmsd.png
├─ metadata/
│  ├─ preprocess_report.json
│  ├─ md_pdbfixer_report.json
│  └─ run_manifest.json
├─ reports/
│  └─ route_a_summary.md
└─ logs/
   └─ (可能为空)
```

### 5.2 `run_minimal_openmm_validation.py` 运行成功后的输出

```text
work/runs/<run_id>/
└─ md/
   ├─ complex_fixed.pdb
   ├─ solvated.pdb
   ├─ system.xml
   ├─ state_init.xml
   ├─ minimized.pdb
   ├─ equil_nvt_last.pdb
   ├─ equil_npt_last.pdb
   ├─ production.dcd
   ├─ md_log.csv
   ├─ production.chk
   └─ final_state.xml
```

```text
outputs/runs/<run_id>/
├─ metadata/
│  └─ md_pdbfixer_report.json
├─ reports/
│  └─ (通常为空)
└─ logs/
   └─ (通常为空)
```

### 5.3 两者差异总结（快速对照）

- `run_binding_route_a.py`：完整 workflow，包含 preprocessed/docking/analysis/summary 全链路产物。  
- `run_minimal_openmm_validation.py`：只验证 OpenMM 主链，主要产物是 `work/.../md/*` + `outputs/.../metadata/md_pdbfixer_report.json`。  
- 两者都遵守 run_id 规范：只写 `work/runs/<run_id>` 与 `outputs/runs/<run_id>`。
