# Testing & Validation

更新时间：2026-03-11

本文件定义当前仓库测试分层、慢测试策略与产物验收清单。  
注意：本文件以当前代码现实为准，已覆盖近期新增的 `run_manifest`、`route_a_summary` 与 `diagnostic` 语义。

## 1. 测试分层（当前仓库）

### 1.1 快速单元/组件测试（默认）

- `tests/test_docking_placeholder_engine.py`
  - 验证 placeholder docking 的可复现性与 cutoff 行为
- `tests/test_structure_preprocessor_and_assembler.py`
  - 验证结构预处理与组装组件
- `tests/test_binding_analyzer_smoke.py`
  - 验证分析 fallback 可运行，且写入 diagnostic 标记
- `tests/test_run_manifest_smoke.py`
  - 验证 workflow 会写出 `run_manifest.json` 与 `route_a_summary.md`

### 1.2 环境依赖型 smoke（按依赖可用性运行）

- `tests/test_route_a_workflow_smoke.py`
  - 依赖 `pdbfixer`、`openmm`
  - 若依赖缺失会 `importorskip`（不是失败）

## 2. 慢测试策略（建议执行规范）

当前仓库尚未统一使用 `pytest -m slow` marker。  
建议后续补齐以下策略：

1. 对真实 OpenMM 运行链路打 `slow` marker（尤其生产步数 > 最小 smoke）。
2. CI 默认只跑快速测试；本地或夜间任务跑 `slow`。
3. 在 `pytest.ini` 统一注册 marker，避免隐藏规则分散在测试文件。

## 3. 推荐测试命令（当前可直接用）

1. 快速回归（不依赖 OpenMM）：

```bash
PYTHONPATH=. pytest -q \
  tests/test_docking_placeholder_engine.py \
  tests/test_binding_analyzer_smoke.py \
  tests/test_run_manifest_smoke.py
```

2. Route A smoke（依赖可用时）：

```bash
PYTHONPATH=. pytest -q tests/test_route_a_workflow_smoke.py
```

3. 全量当前测试：

```bash
PYTHONPATH=. pytest -q tests
```

## 4. 产物验收清单（Route A）

每次 run 至少验收以下项目：

### 4.1 路径与非空

- `work/runs/<run_id>/md/production.dcd`
- `work/runs/<run_id>/md/md_log.csv`
- `outputs/runs/<run_id>/docking/poses.csv`
- `outputs/runs/<run_id>/analysis/binding/metrics.json`
- `outputs/runs/<run_id>/metadata/run_manifest.json`
- `outputs/runs/<run_id>/reports/route_a_summary.md`

### 4.2 结果边界字段（防误读硬约束）

1. `poses.csv` 包含：
- `scientific_validity`
- `score_semantics`
- `proxy_vdw_score`
- `proxy_electrostatic_score`
- `proxy_distance_penalty`

2. `run_manifest.json` 包含：
- `backend`
- `analysis_mode`
- `scientific_validity`

3. `metrics.json` fallback 模式包含：
- `metrics_semantics=diagnostic_not_physical`
- `diagnostic="true"`

4. `route_a_summary.md` 包含：
- `scientific_validity` 行
- placeholder 时的边界声明（validation only）

## 5. 已知测试缺口（按当前进度）

1. endpoint FE 最小真实实现尚未开始，相关测试缺失。
2. membrane mode（Route B）未实现，缺少对应测试矩阵。
3. umbrella sampling / PMF 未实现，缺少统计重建与窗口覆盖测试。
4. 真实 docking backend 未接入，当前仅 placeholder 回归。

## 6. 变更时的测试同步规则

任何改动涉及以下内容时，必须补或更新测试：

1. 结果字段命名变化（CSV/JSON）  
2. workflow 汇总逻辑变化（manifest/summary）  
3. 分析 fallback 语义变化（diagnostic 标记）  
4. 目录结构变化（work/outputs 路径）  

