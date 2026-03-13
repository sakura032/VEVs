# ONBOARDING (1-Page)

更新时间：2026-03-13  
适用对象：第一次接手 VEVs 代码的开发同伴，本文是对README的精炼概括。

## 1. 你接手的是什么

当前仓库是 Route A（solution mode）最小可运行闭环，不是最终科学版本。

已打通：
- validate input
- preprocess
- docking (placeholder)
- assemble complex
- all-atom MD (OpenMM)
- analysis + summarize

未完成（结构性缺口）：
- 真实 docking backend
- endpoint FE 真正计算链
- membrane mode / Route B
- umbrella sampling / PMF

## 2. 先看哪里（按顺序）

1. 契约：`src/interfaces/contracts.py`  
2. 编排：`src/models/workflows/binding_workflow.py`  
3. 执行：`src/models/all_atom/simulation_runner.py`  
4. 入口：`scripts/run_binding_route_a.py`  
5. 文档：`README.md` + `TREE_3_12.md` + `docs/architecture/*`

## 3. 环境要求（WSL2 + conda）

推荐：
- conda env: `vesicle_sim`
- Python: `3.10`

创建环境（若未创建）：
```bash
conda create -n vesicle_sim -c conda-forge python=3.10 -y
conda activate vesicle_sim
```

安装依赖： openmm版本 8.4.0
```bash
conda install -c conda-forge openmm pdbfixer mdanalysis numpy pandas matplotlib pytest -y
```

## 4. 第一次运行（必须顺序）

1. 进入项目根目录并激活环境  
2. 跑关键回归：
```bash
python -m pytest -q -rs \
  tests/test_route_a_workflow_smoke.py \
  tests/test_run_manifest_smoke.py \
  tests/test_binding_analyzer_smoke.py
```

3. 跑 OpenMM 主链验证：
```bash
python scripts/run_minimal_openmm_validation.py \
  --run-id openmm_validation_dev_001
```

4. 跑 Route A 主入口：  run-id是自己命名的，routeA_dev_001可替换为任意！
```bash
python scripts/run_binding_route_a.py \
  --run-id routeA_dev_001 \
  --receptor data/test_systems/minimal_complex/minimal_complex.pdb \
  --ligand data/test_systems/minimal_complex/minimal_complex.pdb
```

## 5. 输出怎么看

过程产物：
- `work/runs/<run_id>/...`
- 重点：`md/complex_fixed.pdb`, `md/solvated.pdb`, `md/production.dcd`, `md/md_log.csv`

结果产物：
- `outputs/runs/<run_id>/...`
- 重点：`docking/poses.csv`, `analysis/binding/metrics.json`, `metadata/run_manifest.json`, `reports/route_a_summary.md`

## 6. 开发边界（必须遵守）

1. 不混层：workflow 不写 OpenMM 细节，analysis 不生成伪结构。  
2. 不把 placeholder 结果当 scientific conclusion。  
3. 新增产物必须落在 run_id 目录：`work/runs/<run_id>` 和 `outputs/runs/<run_id>`。  
4. 改契约或字段时，同步更新 tests 与 docs。  
