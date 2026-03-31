# VEVs

VEVs 是一个面向囊泡建模、数据整理和可视化展示的持续演进项目。当前阶段，我们优先把 vesicle 基础链路打磨稳定，包括模板管理、结构组装、结果导出和前端浏览；后续新的建模、分析或模拟模块，会继续接入这套已经规范下来的项目框架，而不是再回到早期那种实验脚本散落、目录职责不清的状态。

这份 README 现在承担三个角色：

- 解释项目当前的背景和边界
- 给出最常用的运行方式
- 作为仓库结构的总索引，帮助后续继续扩展时保持目录清晰

## Background

这个仓库经历过一次比较大的收敛整理。旧的蛋白对接路线和与之绑定的前端页面已经移除，主干只保留当前仍有价值、且能够稳定演进的 vesicle 相关能力。与此同时，前端被重组为 feature-first 结构，日志、文档、配置和数据目录也开始按照长期项目的方式预留位置。

因此，VEVs 当前不是“只做 vesicle 的单功能仓库”，而是一个已经有清晰主干的项目工作区：

- `src/vesicle/` 提供当前稳定的 Python 核心能力
- `frontend/` 提供当前唯一真实业务页 `Whole Vesicle Explorer`
- `docs/`、`logs/`、`config/`、`data/` 预留了后续扩展所需要的组织结构

## Current Capabilities

当前主干已经稳定保留的能力包括：

- 基于模板的囊泡粗粒度结构构建
- 囊泡结构输出到 `outputs/vesicle/`
- 囊泡数据集同步到前端可视化目录
- 前端对 vesicle 数据集的浏览、筛选和显示模式切换

当前前端只认一套 vesicle 数据契约：

- `frontend/visualization/vesicle/index.json`
- `frontend/visualization/vesicle/<dataset_id>/vesicle.gro`
- `frontend/visualization/vesicle/<dataset_id>/topol.top`
- `frontend/visualization/vesicle/<dataset_id>/meta.json`

## Quick Start

### 1. Python Environment

建议先创建虚拟环境，再安装 Python 依赖：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` 当前包含：

- `numpy`
- `scipy`
- `pytest`

### 2. Build A Vesicle Dataset

生成默认基础囊泡：

```bash
python scripts/vesicle_build.py
```

写入自定义输出目录：

```bash
python scripts/vesicle_build.py --output-dir outputs/vesicle/<dataset_id>
```

默认情况下，这个脚本会：

1. 读取 `data/vesicle/` 下的模板
2. 构建一套基础囊泡体系
3. 写出 `vesicle.gro` 和 `topol.top`
4. 自动同步到 `frontend/visualization/vesicle/<dataset_id>/`

如果只想保留后端输出，不做前端同步：

```bash
python scripts/vesicle_build.py --no-sync-frontend
```

### 3. Sync An Existing Dataset To The Frontend

如果已经有 `outputs/vesicle/<dataset_id>/`，可以单独同步：

```bash
python scripts/vesicle_sync_frontend.py --source-dir outputs/vesicle/<dataset_id>
```

### 4. Start The Frontend

```bash
cd frontend
npm install
npm run dev
```

常用检查命令：

```bash
cd frontend
npm run lint
npm run build
```

## Project Structure

下面这份结构说明按“目录 -> 子目录 / 关键文件 -> 作用定位”组织。它不是简单罗列文件，而是把当前仓库的职责边界写清楚，方便以后继续增加模块时不把代码再写乱。

```text
.
├─ README.md
├─ requirements.txt
├─ config/
├─ data/
│  ├─ vesicle/
│  │  ├─ forcefields/
│  │  ├─ lipids/
│  │  └─ proteins/
│  ├─ raw/
│  ├─ processed/
│  ├─ external/
│  └─ interim/
├─ docs/
│  ├─ introduction/
│  ├─ design/
│  │  └─ frontend_architecture.md
│  ├─ user_guide/
│  │  ├─ frontend_usage.md
│  │  └─ skills_usage.md
│  ├─ development/
│  └─ testing/
│     └─ pytest_temp_directory_policy.md
├─ logs/
│  ├─ system_logs/
│  ├─ debug_logs/
│  └─ error_logs/
├─ outputs/
│  └─ vesicle/
├─ scripts/
│  ├─ __init__.py
│  ├─ vesicle_build.py
│  └─ vesicle_sync_frontend.py
├─ src/
│  ├─ __init__.py
│  └─ vesicle/
│     ├─ __init__.py
│     ├─ models/
│     │  ├─ __init__.py
│     │  ├─ lipid.py
│     │  ├─ protein.py
│     │  └─ vesicle_builder.py
│     └─ utils/
│        ├─ __init__.py
│        └─ placement.py
├─ tests/
│  └─ vesicle/
│     ├─ test_builder.py
│     ├─ test_factory.py
│     ├─ test_placement.py
│     └─ test_protein.py
└─ frontend/
   ├─ README.md
   ├─ package.json
   ├─ vite.config.js
   ├─ src/
   │  ├─ app/
   │  ├─ pages/
   │  ├─ features/
   │  ├─ shared/
   │  └─ lib/
   └─ visualization/
      └─ vesicle/
```

### Root-Level Files And Directories

- `README.md`
  - 项目总览、上手方式、当前架构说明
- `requirements.txt`
  - Python 运行与测试所需的基础依赖
- `config/`
  - 预留给项目级配置文件的目录
  - 当前保持为空，后续统一存放集中式配置

### `data/`

`data/` 现在分成两种性质不同的内容：

- 一类是当前已经稳定使用的领域模板目录
- 一类是为后续数据流水线预留的分层目录

具体如下：

- `data/vesicle/`
  - 当前 vesicle 模块使用的静态模板数据根目录
  - 放置的是可直接参与构建流程的已整理模板，而不是临时中间结果
- `data/vesicle/forcefields/`
  - MARTINI 力场片段、蛋白相关 `.itp` 和拓扑片段
- `data/vesicle/lipids/`
  - 脂质 `.gro` 模板
- `data/vesicle/proteins/`
  - 蛋白模板、参考 PDB 与 CG 输入结构
- `data/raw/`
  - 预留给未经处理的原始数据
  - 例如下载得到的原始数据集、初始实验导出文件
- `data/processed/`
  - 预留给清洗或标准化后的数据
  - 适合放后续模块正式消费的处理中间产物
- `data/external/`
  - 预留给从外部来源获得的数据
  - 例如 API 拉取文件、数据库导出结果、第三方工具产物
- `data/interim/`
  - 预留给临时中间文件
  - 例如阶段性缓存、调试过程中的一次性结果、临时模型权重

### `docs/`

`docs/` 是当前项目的正式文档根目录，按照用途拆分为五类：

- `docs/introduction/`
  - 项目背景、术语说明、快速引导
- `docs/design/`
  - 架构设计与模块边界说明
  - 当前已经包含 `frontend_architecture.md`
- `docs/user_guide/`
  - 使用说明、典型流程、命令示例
  - 当前已经包含 `frontend_usage.md` 和 `skills_usage.md`
- `docs/development/`
  - 开发规范、目录约定、演进记录
- `docs/testing/`
  - 测试策略、验证方法和验收记录
  - 当前已经包含 `pytest_temp_directory_policy.md`

目前前端细节说明已经迁入 `docs/`，`frontend/README.md` 只保留导航作用。

### `logs/`

`logs/` 是日志目录骨架，当前先把长期项目需要的三类日志位置固定下来：

- `logs/system_logs/`
  - 系统运行日志
- `logs/debug_logs/`
  - 调试过程日志
- `logs/error_logs/`
  - 错误日志与失败记录

### `src/vesicle/`

这是当前 Python 主代码的核心目录，也是目前仓库中最稳定的一块实现。

- `src/vesicle/__init__.py`
  - 对外导出当前最常用的核心对象
- `src/vesicle/models/lipid.py`
  - 定义脂质蓝图与 3D 模板构建逻辑
  - 把原始模板标准化为 builder 能直接使用的局部刚体表示
- `src/vesicle/models/protein.py`
  - 负责读取蛋白 CG 模板、计算半径、跨膜中心等几何缓存
- `src/vesicle/models/vesicle_builder.py`
  - 当前囊泡总装主流程
  - 串联蛋白放置、双叶铺脂与 `.gro/.top` 输出
- `src/vesicle/utils/placement.py`
  - 空间放置原语模块
  - 统一收纳球面布点、球面对齐、局部扰动和碰撞检测

### `scripts/`

这是项目级脚本入口层。当前只保留两条已经稳定下来的 vesicle CLI：

- `scripts/vesicle_build.py`
  - 一键生成默认基础囊泡
  - 负责构建、写出输出、并可选同步前端
- `scripts/vesicle_sync_frontend.py`
  - 把 `outputs/vesicle/<dataset_id>/` 同步到前端数据目录
  - 同时维护 `frontend/visualization/vesicle/index.json`

### `outputs/`

- `outputs/vesicle/`
  - 当前项目唯一保留的输出根目录
  - 每个数据集位于 `outputs/vesicle/<dataset_id>/`
- `outputs/vesicle/<dataset_id>/vesicle.gro`
  - 组装完成后的结构文件
- `outputs/vesicle/<dataset_id>/topol.top`
  - 与结构对应的拓扑文件

### `tests/vesicle/`

这是当前 Python 回归测试目录。

- `tests/vesicle/test_builder.py`
  - 验证 builder 主流程、输出写出与前端同步链路
- `tests/vesicle/test_factory.py`
  - 验证脂质模板构建和标准化流程
- `tests/vesicle/test_placement.py`
  - 验证空间放置层，包括球面布点、对齐、扰动和碰撞查询
- `tests/vesicle/test_protein.py`
  - 验证蛋白模板读取与几何缓存

### `frontend/`

前端已经整理成 feature-first 结构，并且只保留 vesicle 真实业务。

- `frontend/package.json`
  - 前端依赖和 `dev` / `lint` / `build` 命令入口
- `frontend/src/app/`
  - 应用壳、路由和全局装配
- `frontend/src/pages/`
  - 路由级页面装配层
- `frontend/src/features/`
  - 业务模块层
  - 当前包含 `vesicle-explorer` 和 `workspace`
- `frontend/src/shared/`
  - 通用 UI 和样式
- `frontend/src/lib/`
  - 通用 loader 与底层读写能力
- `frontend/visualization/vesicle/`
  - 前端运行时读取的数据集根目录
- `frontend/README.md`
  - 前端文档导航入口，详细说明已经迁移到 `docs/`

当前前端双路由分别是：

- `Whole Vesicle Explorer`
  - 当前唯一真实业务页
- `Workspace`
  - 未来模块占位页

## Typical Workflow

一个完整的当前主干工作流通常是：

1. 准备 `data/vesicle/` 中的模板
2. 运行 `python scripts/vesicle_build.py`
3. 在 `outputs/vesicle/<dataset_id>/` 得到结构和拓扑
4. 把数据同步到 `frontend/visualization/vesicle/<dataset_id>/`
5. 启动前端，在 `Whole Vesicle Explorer` 中浏览数据集

如果只做后端结构生成，可以停在第 3 步；如果已经有现成输出，则可以从第 4 步开始。

## Development Notes

当前这套结构有几个明确约束：

- 新的 Python 功能优先放进 `src/`，不要回到根目录脚本散落的方式
- 新的前端功能优先以 `features/<feature-name>/` 组织，不要把业务逻辑直接堆进 `pages/`
- 新的文档应优先写入 `docs/` 对应分类，而不是继续在根目录散落多个说明文件
- 临时过程数据放进 `data/interim/`，正式模板与领域输入再决定是否提升到 `data/vesicle/` 或其他稳定位置

## Validation

当前推荐的基本检查方式：

```bash
python -m pytest tests/vesicle
```

```bash
cd frontend
npm run lint
npm run build
```

如果本地 Python 环境尚未安装依赖，请先执行：

```bash
pip install -r requirements.txt
```
