# VEVs 结构导航（给第一次接手的搭档）

更新时间：2026-03-12  
目标：一眼看懂“代码在哪里、谁负责什么、结果去哪里”

---

## 1. 顶层目录速览

```text
VEVs/
├─ src/                  # 核心代码（分层架构）
├─ scripts/              # 运行入口（Route A / OpenMM 验证）
├─ tests/                # smoke 与接口回归测试
├─ docs/                 # 架构与 I/O 说明文档
├─ data/                 # 输入数据（示例结构）
├─ work/                 # 过程产物（运行中间文件）
├─ outputs/              # 结果产物（docking/analysis/report）
├─ README.md             # 项目状态说明（实况）
├─ TREE_3_12.md          # 本文件
├─ casetwo.md            # 目标架构规范
└─ deepresearch3_10.md   # 深度研究参考
```

---

## 2. `src/` 分层地图

```text
src/
├─ configs/
│  ├─ system_config.py
│  ├─ md_config.py
│  ├─ docking_config.py
│  ├─ free_energy_config.py
│  └─ membrane_config.py
│
├─ interfaces/
│  └─ contracts.py
│
├─ models/
│  ├─ workflows/
│  │  └─ binding_workflow.py
│  ├─ all_atom/
│  │  └─ simulation_runner.py
│  └─ docking/
│     ├─ pdb_utils.py
│     ├─ scoring.py
│     ├─ placeholder_engine.py
│     └─ result_validation.py
│
├─ utils/
│  ├─ structure_repository.py
│  ├─ structure_preprocessor.py
│  └─ complex_assembler.py
│
└─ analysis/
   └─ binding_analyzer.py
```

### 分层职责一句话

- `configs`：定义参数空间和校验
- `interfaces/contracts`：统一 I/O 契约和 Protocol 接口
- `models/workflows`：只做 orchestration
- `models/all_atom`：只做 OpenMM 执行
- `models/docking`：docking 相关逻辑（当前 placeholder）
- `utils`：输入校验、预处理、组装
- `analysis`：轨迹/日志分析和结果导出

---

## 3. 运行入口与用途

```text
scripts/
├─ run_binding_route_a.py
└─ run_minimal_openmm_validation.py
```

- `run_binding_route_a.py`：当前主入口，走完整 Route A 最小闭环
- `run_minimal_openmm_validation.py`：只验证 OpenMM 主链，不经过 workflow

---

## 4. 流程顺序（docking 和 binding 的关系）

`binding workflow` 包含 `docking`，但不等于 `docking`。

执行顺序：

1. validate input  
2. preprocess  
3. docking（产出 poses + score）  
4. select pose  
5. assemble complex  
6. run MD（OpenMM）  
7. analyze  
8. summarize + report

---

## 5. 输出目录规则（已切换为 run_id）

### `work/`：过程产物

```text
work/
├─ runs/
│  └─ <run_id>/
│     ├─ preprocessed/
│     ├─ assembled/
│     └─ md/
└─ archive/
   └─ legacy_20260310/
```

### `outputs/`：结果产物

```text
outputs/
├─ runs/
│  └─ <run_id>/
│     ├─ docking/
│     ├─ analysis/
│     ├─ metadata/
│     ├─ logs/
│     └─ reports/
└─ archive/
   ├─ routeA_key_artifacts_20260310_185021.zip
   └─ legacy_20260310/
```

说明：

- `runs/<run_id>/` 是当前唯一推荐路径，避免覆盖
- `archive/legacy_*` 是历史根目录产物搬迁

---

## 6. 关键文件看哪里

### 想改接口

- `src/interfaces/contracts.py`

### 想改工作流步骤

- `src/models/workflows/binding_workflow.py`

### 想改 OpenMM 参数或阶段逻辑

- `src/models/all_atom/simulation_runner.py`

### 想改 docking 逻辑

- `src/models/docking/placeholder_engine.py`
- `src/models/docking/scoring.py`

### 想改预处理/组装

- `src/utils/structure_preprocessor.py`
- `src/utils/complex_assembler.py`
- `src/utils/structure_repository.py`

### 想改分析输出

- `src/analysis/binding_analyzer.py`

---

## 7. 测试文件与覆盖点

```text
tests/
├─ test_docking_placeholder_engine.py
├─ test_structure_preprocessor_and_assembler.py
├─ test_binding_analyzer_smoke.py
├─ test_route_a_workflow_smoke.py
└─ test_run_manifest_smoke.py
```

建议：这些测试保留，不要删。它们是后续改算法时防回归的最低保障。

---

## 8. 当前边界（必须明确）

当前结论边界：

- placeholder docking 结果只用于工程链路验证
- 不能当作真实物理/生物结论
- membrane 与 umbrella 目前还没进入真实执行链

如果你要继续写真实算法，优先从 backend 适配和分析严谨性入手，不要破坏现有分层。
