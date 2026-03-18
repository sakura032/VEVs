# VEVs Frontend 设计规范 v1（与当前实现同步）

更新时间：2026-03-15  
适用范围：`frontend/` 当前单页可视化工作台（Route A / receptor-ligand complex）

## 0. 文档定位与边界

本文件是“当前已实现前端”的设计与实现规范同步文档，不是理想稿。

硬边界（必须保持）：
- 当前仅服务 `receptor-ligand complex`，不是 whole vesicle。
- `docking backend` 仍为 `placeholder`，不得将结果包装成发表级科学结论。
- UI 必须显式暴露 `run_id / backend / scientific_validity / analysis_mode`。
- 前端只消费产物，不改 scientific workflow。

## 1. 当前页面架构（真实实现）

当前页面是单页 scientific workspace：
- `TopHeader`
- `LeftControlPanel`（Accordion，多开）
- `Center Area`（在同一中区切换 `3D` 与 `Analytics Panel`）
- `RightInsightPanel`（可开关的悬浮侧栏，Accordion，多开）

说明：
- 组件名仍为 `BottomAnalyticsPanel`，但在布局上已不作为“固定底栏”，而是中区可切换内容之一。
- 右侧洞察栏为悬浮抽屉式区域，通过按钮显示/隐藏。

## 2. 布局规范

### 2.1 根布局
- 根容器：`.app-shell`
- 采用 `100dvh` 视口高度，Header + 主工作区两行。
- 主工作区 `.workspace-layout` 默认两列：左栏 + 中区。
- 右栏为绝对定位悬浮层：`.workspace-area-right`。

### 2.2 中区
- `center-area` 内含工具条与内容区。
- 内容区 `center-view-content` 根据状态切换：
  - `structure` -> `MolecularCanvas`
  - `analytics` -> `BottomAnalyticsPanel`
- 切换含轻量淡入动画（`center-view-fade`）。

### 2.3 响应式
- `<= 1024px`：主区改单列，顺序为 `center -> left -> right`。
- 小屏下右栏不再绝对悬浮，改为块级区域按开关显示。

## 3. 组件职责与代码位置

- 页面入口：`frontend/src/pages/StructureExplorerPage.jsx`
- 顶栏：`frontend/src/components/layout/TopHeader.jsx`
- 左栏：`frontend/src/components/layout/LeftControlPanel.jsx`
- 右栏：`frontend/src/components/layout/RightInsightPanel.jsx`
- 分析面板：`frontend/src/components/layout/BottomAnalyticsPanel.jsx`
- 3D 画布：`frontend/src/components/scene/MolecularCanvas.jsx`
- 场景 overlay：`frontend/src/components/scene/SelectionOverlay.jsx`
- 手风琴：`frontend/src/components/common/AccordionGroup.jsx`

## 4. 数据契约与文件映射

前端统一通过 `/visualization/<run_id>/...` 访问数据。

### 4.1 结构阶段（MainScene）
- `work/preprocessed/receptor_clean.pdb`
- `work/preprocessed/ligand_prepared.pdb`
- `work/assembled/complex_initial.pdb`
- `work/md/complex_fixed.pdb`
- `work/md/solvated.pdb`
- `work/md/minimized.pdb`
- `work/md/equil_nvt_last.pdb`
- `work/md/equil_npt_last.pdb`
- `sampled_frames.json`（trajectory 抽样入口）

### 4.2 右栏与分析
- `outputs/docking/poses.csv` -> Pose Table
- `outputs/docking/poses/pose_*.pdb` -> pose 结构切换
- `outputs/analysis/binding/metrics.json` -> Metrics Cards
- `outputs/analysis/binding/rmsd.csv` -> RMSD
- `work/md/md_log.csv` -> MD Log
- `outputs/metadata/preprocess_report.json` -> Provenance
- `outputs/metadata/md_pdbfixer_report.json` -> Provenance
- `outputs/metadata/run_manifest.json` -> Header + Provenance
- `outputs/reports/route_a_summary.md` -> Report Viewer

### 4.3 角色派生数据
- `derived/structure_roles.json`
- schema：
  - `run_id`
  - `resolution_status` (`resolved|ambiguous|missing`)
  - `resolution_notes`
  - `source`
  - `atom_roles`（key=`serial|chainId|residueId|residue|atomName`）

### 4.4 角色分辨质量门槛（必须纳入验收）
- 若 receptor 与 ligand 输入文件相同，或原子键集合高度重叠，会触发 `ambiguous`。
- `ambiguous` 时，重叠原子会被标记为 `unresolved`，前端必须显示边界警告，不得伪装为可区分 ligand。
- 典型触发案例：`minimal_complex` 数据只有单链蛋白原子（无独立 ligand 集合），导致 receptor/ligand 完全重叠。
- 消除方式必须在数据侧完成：
  - 输入拆分为可区分的 receptor 与 ligand 源文件
  - 保证 `atom_key` 可分离
  - 重新运行预处理与 bundle 导出

## 5. 运行数据组织（symlink-only）

### 5.1 目标目录
- 运行数据放在：`frontend/visualization/<run_id>/`
- `frontend/public/visualization/` 不再存放 run 数据，仅保留轻量静态占位（如 `.gitkeep`）。

### 5.2 导出脚本
- 脚本：`scripts/export_visualization_bundle.py`
- 输入：`--run-id <run_id>`
- 行为：
  - 建立 `work`、`outputs` 符号链接（Windows 下可能回退 junction/hardlink）
  - 链接 `sampled_frames.json` 与 `frame_pdb/*`
  - 生成 `derived/structure_roles.json`
  - 更新 `frontend/visualization/index.json`
  - 清理 `frontend/public/visualization/` 的运行数据

## 6. 3D 渲染语义（当前实现）

### 6.1 模式语义
- `cartoon`：按链 C-alpha trace 线条 + 关键原子 focus spheres
- `sticks`：原子球 + 键圆柱（优先 CONECT，缺失时在阈值内自动推断）
- `spheres`：按元素半径缩放的 instanced 球

说明：三种模式切换的是几何实现，不是仅改点大小。

### 6.2 颜色语义
- 角色主色：`receptor / ligand / water / unresolved`
- 元素色：`C/N/O/S/P/H/金属`
- `sticks`/`spheres` 中会做角色色与元素色混合；因此视觉上可能同属冷色系，但语义仍由 role 与元素共同决定。
- 除离散 token 色外，混色与光照会产生连续中间色；这属于正常渲染结果。

### 6.3 科学边界展示
- 若 `resolution_status=ambiguous`，场景 overlay 顶部显示强提醒：
  - 当前数据无法可靠区分 receptor/ligand，仅供流程验证。
- Header 与 Provenance 同步展示 placeholder 边界字段。

### 6.4 性能分层策略
- `<= 8k atoms`：全功能
- `8k~20k`：降低几何细分，禁用大规模自动键推断
- `>20k`：强制 `cartoon` 并给可见说明

### 6.5 颜色全集（审计口径）
离散色源必须完整记录于文档与 token：

- 场景角色色：`--accent-receptor`, `--accent-ligand`, `--accent-water`, `--accent-unresolved`
- 元素色：`--element-carbon`, `--element-nitrogen`, `--element-oxygen`, `--element-sulfur`, `--element-phosphorus`, `--element-hydrogen`, `--element-metal`
- 图表与交互色：`--accent-blue`, `--accent-cyan`, `--accent-selected`
- 状态色：`--status-success`, `--status-warning`, `--status-danger`, `--status-info`, `--status-reserved`
- 背景/边框色：`--bg-*`, `--border-*`, `--text-*`

派生色规则也必须被说明：

- `cartoon` 焦点球：`roleColor` 与 `elementColor` 线性插值（0.22）
- `sticks` 原子球：`blend(role, element, 0.40)`
- `spheres` 原子球：`blend(role, element, 0.42)`
- `sticks` 键：两端角色色取中值
- 选中高亮：`accent-unresolved` + 透明度 + 发光

### 6.6 状态全集（审计口径）
前端说明书必须覆盖以下全部状态枚举：

- 角色解析：`resolved | ambiguous | missing`
- 原子角色：`receptor | ligand | water | unresolved`
- 角色置信：`mapped | fallback | conflict`
- 渲染模式（请求/生效）：`cartoon | sticks | spheres`
- 性能分层：`full | reduced | huge`
- 可见性过滤：`all | receptor | ligand`
- 阶段可用性：`Ready | Missing`
- 轨迹可用性：`available=true/false`
- 通用数据加载：`idle | loading | loaded | error`
- 中区视图：`structure | analytics`
- 右侧洞察栏：`is-open | is-closed`
- Badge 视觉变体：`info | success | warning | danger | reserved`

## 7. 样式与命名规范

- 样式 token 统一定义：`frontend/src/styles/tokens.css`
- 全局样式：`frontend/src/styles/globals.css`
- 布局与组件样式：`frontend/src/styles/layout.css`
- 命名要求：语义化组件名，不使用弱命名（如 `Panel1`, `TempCard`）。

## 8. 已保留的 Reserved 模块

### 左侧 Future Modules
- `Membrane Mode`
- `Endpoint FE`
- `PMF / Umbrella`
- `Multi-run Comparison`
- `Whole Vesicle Explorer`

### 分析面板 Reserved Tabs
- `H-bond`
- `Contacts`
- `Interface Map`
- `Endpoint FE`
- `PMF`

## 9. 验收标准（当前版本）

- 页面能加载 run，stage 可切换。
- pose 表与 3D 联动可用。
- 中区可无刷新切换 `3D <-> Analytics`。
- 右侧洞察栏可开可关。
- Header 显示边界字段。
- ambiguous/missing 情况有明确提示。
- Reserved 区域完整保留且清晰标注。

## 10. 不得做的事情

- 不得把 placeholder 结果叙述成真实 binding affinity 结论。
- 不得宣称当前页面是 whole vesicle explorer。
- 不得绕过 `/visualization/<run_id>/` 契约直接依赖散乱路径。
- 不得把 `work/outputs` 全量复制到 `frontend/public/visualization/`。
