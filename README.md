# VEVs 项目状态说明（实时快照）

更新时间：2026-03-12  
适用对象：第一次接触本仓库的新协作者（算法/接口实现同学）

---

## 1. 当前项目到底到哪一步了

本仓库已经从“骨架阶段”进入“Route A 最小闭环可运行阶段”：

- 已有可运行链路：`validate -> preprocess -> dock -> assemble -> AA-MD -> analyze -> summarize`
- 已接入 OpenMM 主链（`prepare_system -> minimize -> equilibrate -> production`）
- 当前只支持：`CPU`、`solution mode`、`placeholder docking`
- 当前定位是 **engine/workflow validation**，不是最终 scientific validation

结论：工程链路可跑通，科研级方法（真实 docking backend / endpoint FE / membrane / umbrella）尚未完成。

---

## 2. 代码分层（对齐 casetwo.md）

```text
src/
├─ configs/                    # 配置层 dataclass + validate
├─ interfaces/contracts.py     # 数据契约 + Protocol 接口
├─ models/
│  ├─ workflows/               # 编排层（BindingWorkflow）
│  ├─ all_atom/                # 执行层（AllAtomSimulation）
│  └─ docking/                 # placeholder docking + scoring + validation
├─ utils/                      # repository / preprocessor / assembler
└─ analysis/                   # BindingAnalyzer
```

### 2.1 配置层（`src/configs/`）

- `SystemConfig`：输入结构路径、力场、水模型、温压、pH、是否 membrane
- `MDConfig`：平台、积分参数、最小化/平衡/生产时长与输出频率
- `DockingConfig`：backend、pose 数、seed、cutoff
- `EndpointFreeEnergyConfig` / `UmbrellaSamplingConfig`：已定义，当前 Route A 未真正实现
- `MembraneConfig`：已定义，当前 Route A 不启用

### 2.2 契约层（`src/interfaces/contracts.py`）

统一了关键 I/O 对象：

- `InputManifest`
- `PreparedStructures`
- `DockingPose` / `DockingResult`
- `AssembledComplex`
- `SimulationArtifacts`
- `BindingWorkflowResult`

并定义了 Protocol 接口（repository/preprocessor/docking/assembler/runner/analyzer）。

### 2.3 编排层（`src/models/workflows/binding_workflow.py`）

`BindingWorkflow` 负责 orchestration，不承载 OpenMM 细节。

当前 `run()` 顺序：

1. `build_manifest`
2. `validate_inputs`
3. `prepare_inputs`
4. `dock`
5. `rank_poses`
6. `select_pose`
7. `build_complex`
8. `run_refinement_md`
9. `analyze`（可选）
10. `summarize`

`summarize()` 当前还会写出：

- `outputs/runs/<run_id>/metadata/run_manifest.json`
- `outputs/runs/<run_id>/reports/route_a_summary.md`

### 2.4 执行层（`src/models/all_atom/simulation_runner.py`）

`AllAtomSimulation` 已实现完整主链：

- `prepare_system`
- `minimize`
- `equilibrate`
- `production`
- `run_full_protocol`

已输出标准 MD artifacts（`system.xml`, `state_init.xml`, `production.dcd`, `md_log.csv`, ...）。

### 2.5 工具层与分析层

- `StructureRepository`：输入文件校验，支持 manifest 导出（哈希、大小、mtime）
- `StructurePreprocessor`：基于 `pdbfixer` 最小清洗（当前 `.pdb`）
- `ComplexAssembler`：兼容 placeholder pose 输出组装 `complex_initial.pdb`
- `BindingAnalyzer`：
  - 优先 trajectory 分析（MDAnalysis RMSD）
  - 无法分析时 fallback 到 log 诊断图
  - 输出 `metrics.json` + `csv` + `png`

### 2.6 Docking 层（`src/models/docking/`）

- `PlaceholderDockingEngine`：固定 seed、可重复、CPU 友好
- 评分是 proxy，不是物理可发表能量
- 在 `poses.csv` 中显式写入边界字段：
  - `scientific_validity=placeholder_not_physical`
  - `score_semantics=proxy_lower_is_better`
  - `proxy_*` 指标

---

## 3. 运行入口

### 3.1 Route A 主入口

`scripts/run_binding_route_a.py`

```bash
python scripts/run_binding_route_a.py \
  --receptor data/test_systems/minimal_complex/minimal_complex.pdb \
  --ligand data/test_systems/minimal_complex/minimal_complex.pdb
```

更推荐：指定run-id：

```bash
python scripts/run_binding_route_a.py \
  --run-id routeA_YYYYmmdd_HHMMSS \
  --receptor data/test_systems/minimal_complex/minimal_complex.pdb \
  --ligand data/test_systems/minimal_complex/minimal_complex.pdb
```

### 3.2 OpenMM 主链单独验证入口

`scripts/run_minimal_openmm_validation.py`

用途：只验证 AA-MD engine，不经过 `BindingWorkflow`。

---

## 4. 输出目录规范（当前真实状态）

已采用 run_id 隔离：

- `work/runs/<run_id>/...`：过程产物
- `outputs/runs/<run_id>/...`：结果产物

旧根目录产物已迁入归档：

- `work/archive/legacy_20260310/`
- `outputs/archive/legacy_20260310/`

当前可见示例 run：

- `work/runs/routeA_demo_20260310/`
- `outputs/runs/routeA_demo_20260310/`

注意：`routeA_demo_20260310` 是旧一次运行结果，里面当前只有：

- `metadata/preprocess_report.json`

还没有 `run_manifest.json` 与 `route_a_summary.md`。  
这是因为该 run 发生在 workflow 新增自动写报告之前；重新运行一次 Route A 即会生成这两类文件。

---

## 5. 测试现状

`tests/` 当前文件：

- `test_docking_placeholder_engine.py`
- `test_structure_preprocessor_and_assembler.py`
- `test_binding_analyzer_smoke.py`
- `test_route_a_workflow_smoke.py`
- `test_run_manifest_smoke.py`

这些测试的目的：

- 保证 placeholder docking 的可重复性与边界语义
- 保证 preprocessor + assembler 可联通
- 保证 analyzer 在 trajectory 与 fallback 场景都有最小产出
- 保证 workflow 在注入组件后能跑通，并写出 run manifest / summary

---

## 6. 目前明确未完成项（避免误解）

1. 真实 docking backend（当前仅 placeholder）
2. endpoint free energy 真正计算（当前仅配置与占位）
3. membrane mode 真正构建与执行
4. umbrella sampling / PMF 工作流
5. 科研级统计稳健性与不确定性评估链

---

## 7. 给后续算法/细节开发同学的协作规则

按 `casetwo.md` 边界推进：

1. 不要把 OpenMM 实现细节写回 `BindingWorkflow`
2. 新 backend 必须对齐 `DockingEngineProtocol`
3. 新分析器必须对齐 `BindingAnalyzerProtocol`
4. 优先扩展 `src/models/docking/`、`src/analysis/`、`src/utils/`，避免跨层污染
5. 新增输出必须放进 `outputs/runs/<run_id>/...`，不要再回写根目录旧路径

---

## 8. 推荐任务（工程优先级）

1. 重新执行一次 Route A，产出完整新格式 run（含 `run_manifest.json` 与 `route_a_summary.md`）
2. 将 `StructureRepository.export_manifest()` 正式接入 workflow 主链（当前代码有实现，默认链路未显式调用）
3. 确定真实 docking backend 适配契约（输入格式、评分语义、失败策略）
4. 把 `docs/architecture/*` 与本 README 同步为同一版本描述

