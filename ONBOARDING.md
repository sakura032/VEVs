# VEVs Onboarding (1-Page)

本文档是README.md的重点介绍，阅读后再精读README.md
更新时间：2026-03-12  
目标：拿到仓库后，快速跑通并看懂主链。

---

## 1. 先知道你在做什么

当前项目的完成进度是 **Route A 最小可运行闭环**（不是最终科研版）：

1. 输入校验  
2. 结构预处理  
3. placeholder docking 
4. 组装复合体  
5. OpenMM 全原子 MD  
6. 分析与汇总

当前边界：`CPU + solution mode + placeholder docking`。
placeholder docking里面是占位符，并未真正实现docking过程
---

## 2. 目录从哪里看

先了解这 4 个位置：

1. `src/interfaces/contracts.py`：数据契约和接口（最重要）  
2. `src/models/workflows/binding_workflow.py`：最上层，总编排（流程入口）  
3. `src/models/all_atom/simulation_runner.py`：OpenMM 主链实现（被2.调用）
4. `scripts/run_binding_route_a.py`：可执行入口  （你可以直接运行的代码，调用了1.2.3.）

辅助文档，帮助你详细了解项目架构：

- `README.md`：当前状态与边界
- `TREE_3_12.md`：目录导航
- `docs/architecture/*`：架构/I/O补充说明

---

## 3. 环境继续使用赵老师发的代码中wsl中的conda环境

推荐统一使用：

- conda 环境名：`vesicle_sim`
- Python 版本：`3.10`（我目前用的python环境）

### 3.1 一次性创建环境

```bash
conda create -n vesicle_sim -c conda-forge python=3.10 -y
conda activate vesicle_sim
```

### 3.2 安装依赖库

```bash
conda install -c conda-forge \
  openmm \
  pdbfixer \
  mdanalysis \
  numpy \
  pandas \
  matplotlib \
  pytest -y
```

说明：

- `openmm`：MD 执行主引擎
- `pdbfixer`：输入结构最小清洗
- `MDAnalysis`：轨迹读取和分析
- `numpy/pandas/matplotlib`：数值分析与图表输出
- `pytest`：测试与回归检查

---

## 4. 第一步先跑测试（确认环境可用）

在仓库根目录执行：

```bash
python -m pytest -q -rs \
  tests/test_docking_placeholder_engine.py \
  tests/test_structure_preprocessor_and_assembler.py \
  tests/test_binding_analyzer_smoke.py \
  tests/test_route_a_workflow_smoke.py \
  tests/test_run_manifest_smoke.py
```

说明：

- 这是 smoke + 组件测试，不是完整 scientific benchmark。
- 如果缺 `pdbfixer` / `openmm` / `MDAnalysis`，部分测试会 skip 或失败，先补环境。

---

## 4. 第二步跑主入口（Route A）
routeA_dev_001是由你命名的，也可以换成别的名字

```bash
python scripts/run_binding_route_a.py \
  --run-id routeA_dev_001 \   
  --receptor data/test_systems/minimal_complex/minimal_complex.pdb \
  --ligand data/test_systems/minimal_complex/minimal_complex.pdb
```

运行后重点检查，work和outputs目录下都放的是输出，两者区别见6.：
work/ 文件通常更“技术内部化”、体积更大、用于继续计算
outputs/ 文件通常更“结果导向”、用于查看/汇报/归档。
例如，在run_id设为routeA_dev_001时：
- `work/runs/routeA_dev_001/`（过程产物）
- `outputs/runs/routeA_dev_001/`（结果产物）

---

## 5. 第二步跑主入口（Route A）

### 项目中的先后顺序是（对于4.第二步跑主入口（Route A）代码的流程概括）
启动run_binding_route_a.py的运行顺序是：
1. 输入校验/预处理
2. docking（生成 poses）
3. 选 pose + 组装 complex
4. MD 精修（AllAtomSimulation）
5. 分析（RMSD/metrics）
6. 汇总为 binding workflow 结果

---

## 6. 为什么有两个输出目录？结果该怎么看？

### 过程产物（work）偏“计算过程文件,流水线加工车间

- `preprocessed/`：预处理，清洗后的 receptor/ligand
- `assembled/`：`complex_initial.pdb` 组装后的复合体初始结构
- `md/`：`system.xml`, `minimized.pdb`, `production.dcd`, `md_log.csv` 等MD 运行核心产物
- `docking_validation_case/, routea_component_smoke/`：测试/验证时生成的临时工作目录
- `runs/<run_id>/...`：按 run_id 隔离后的过程产物（推荐使用）

### 结果产物（outputs） 结果交付文件,对外可读的结果仓

- `docking/poses.csv` + `poses/*.pdb` docking 结果表和 pose 文件
- `analysis/binding/metrics.json`, `rmsd.csv`, `figures/*.png` 分析结果
- `metadata/run_manifest.json` 预处理/输入记录
- `reports/route_a_summary.md` 生成.md运行报告（后续会更完整）
- `archive/`：（可选）把已经跑出来的输出文件打包归档（.zip）
- `runs/<run_id>/...`：按 run_id 隔离后的过程产物（推荐使用）
---

## 7. 如果你不懂“接口/契约”，先记这条

`contracts.py` 定义了每一层之间传什么对象。  
你写新算法时，不要先改 workflow，先对齐这些对象：

1. `PreparedStructures`（预处理输出）  
2. `DockingResult`（docking 输出）  
3. `AssembledComplex`（组装输出）  
4. `SimulationArtifacts`（MD 输出）  
5. `BindingWorkflowResult`（总结果）

只要输入输出契约不破，替换内部算法通常不影响全链路。

---

## 8. 常见开发入口（按目标选）

1. 想换 docking backend：改 `src/models/docking/`，对齐 `DockingEngineProtocol`  
2. 想加强预处理：改 `src/utils/structure_preprocessor.py`  
3. 想加强分析指标：改 `src/analysis/binding_analyzer.py`  
4. 想调 MD 参数：改 `src/configs/md_config.py` 或脚本中的配置构造  
5. 想加新流程步骤：先改 contracts，再改 workflow，最后补 tests

---

## 9. 不要踩的坑

1. 不要把 OpenMM 细节塞进 `BindingWorkflow`  
2. 不要把 placeholder 分数当科学结论  
3. 不要再写回旧路径（`work/md`, `outputs/docking` 根级），统一用 `runs/<run_id>`  
4. 改接口时必须同步更新测试
5. docking 和 binding 的区别：docking：是“找姿势”（给 ligand/receptor 生成候选结合构象并打分）。binding：是“整个结合研究任务”，包含 docking 但不止 docking

---

## 10. 你接手后的建议顺序

1. 跑 tests  
2. 跑 `run_binding_route_a.py`  
3. 打开一次 `outputs/runs/<run_id>/reports/route_a_summary.md`，以及work/
4. 开始替换具体算法（docking/analysis/FE）
