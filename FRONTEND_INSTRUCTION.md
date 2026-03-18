# VEVs 前端可视化说明书（FRONTEND_INSTRUCTION）

更新时间：2026-03-15  
适用目录：`frontend/`  
当前版本定位：Route A 第一版可视化工作台（工程验证导向，不是发表级科学可视化系统）

---

## 1. 这份网页到底是什么
 
当前网页是一个 **Route A receptor-ligand complex 可视化工作台**，目标是把已有产物可追踪地展示出来：

- 结构阶段文件（PDB）切换查看
- docking pose 列表与结构联动
- RMSD 与 MD 日志可视化
- provenance（来源与边界）显示
- 明确暴露 placeholder 边界

必须记住的科学边界：

- `backend=placeholder` 时，任何 score/排名都不能被解读为真实亲和力证据。
- `scientific_validity=placeholder_not_physical` 时，页面只用于流程验证/工程检查。
- 若角色映射状态（`role resolution`）为 `ambiguous`，表示 receptor 与 ligand 当前无法可靠区分。

---

## 2. 先用起来：从数据到页面的完整步骤

## 2.1 准备 run 数据（不复制原始产物）

在项目根目录执行：

```bash
python scripts/export_visualization_bundle.py --run-id <你的run_id>
```

示例：

```bash
python scripts/export_visualization_bundle.py --run-id binding_route_a_3_13
```

脚本会做的事：

- 在 `frontend/visualization/<run_id>/` 下创建运行 bundle。
- `work`、`outputs` 使用符号链接（或 Windows 下兼容链接），不复制原始大文件。
- 若存在抽样轨迹，链接 `sampled_frames.json` 与 `frame_pdb/*`。
- 生成前端派生元数据：`derived/structure_roles.json`。
- 更新 `frontend/visualization/index.json`（供前端 Run Selector 枚举）。
- 清理 `frontend/public/visualization/` 的运行数据，只保留轻量静态占位。

## 2.2 启动前端

```bash
cd frontend
npm install   （只需运行第一次即可，后续启动不用重复）
npm run dev
```

默认访问本地 Vite 地址（例如 `http://localhost:5173`）。

## 2.3 构建验收

```bash
npm run lint
npm run build
```

`npm run build` 会生成 `frontend/dist/`，用于生产部署静态产物。

---

## 3. 页面结构总览（你看到的每个区）

当前页面分为四个核心区域：

1. `TopHeader` 顶部信息条
2. `LeftControlPanel` 左侧控制栏（Accordion）
3. `Center Area` 中央主区（3D 与 Analytics 二者切换）
4. `RightInsightPanel` 右侧洞察栏（可开关悬浮）

注意：

- 历史设计里有“底部固定分析面板”，当前实现已调整为“中区切换Analytics分析面板”。
- 组件名仍叫 `BottomAnalyticsPanel`，但布局位置是中区。

---

## 4. 页面英文逐词解释（按区域）

## 4.1 顶部 Header 词典

| 页面文字 | 中文含义 | 实际数据来源 | 代码位置 |
|---|---|---|---|
| `VEVs Route A Structure Explorer` | 页面主标题：VEVs Route A 结构浏览器 | 固定文案 | `src/components/layout/TopHeader.jsx` |
| `Receptor-Ligand Complex Visualization` | 副标题：受体-配体复合体可视化 | 固定文案 | 同上 |
| `run_id` | 当前加载的 run 标识符 | 选中的 run id | 同上 + `src/pages/StructureExplorerPage.jsx` |
| `backend` | 后端语义标签 | `outputs/metadata/run_manifest.json` | `TopHeader.jsx` + `hooks/useRunManifest.js` |
| `scientific_validity` | 科学有效性边界标签 | `run_manifest.json` | 同上 |
| `analysis_mode` | 分析模式标签 | `run_manifest.json` | 同上 |
| `multi-run: Reserved` | 多 run 功能预留 | 固定 Reserved | `TopHeader.jsx` |

---

## 4.2 左侧控制栏词典

### A. Run Selector

| 页面文字 | 中文含义 | 行为 |
|---|---|---|
| `Run Selector` | 运行选择器 | 输入 run_id 并加载 |
| `Load a run_id visualization bundle` | 读取前端可视化 bundle | 提示文案 |
| 输入框 placeholder `binding_route_a_3_13` | run_id 样例 | 支持 datalist 补全 |
| `Load` | 执行加载 | 重置 stage/pose/frame 相关状态 |

代码位置：`src/components/layout/LeftControlPanel.jsx`

### B. Stage Selector

| 页面文字 | 中文含义 | 数据 |
|---|---|---|
| `Stage Selector` | 阶段选择器 | 来自 `STRUCTURE_STAGES` |
| `Route A structural stages` | Route A 结构阶段说明 | 固定文案 |
| `Ready` | 该阶段文件可访问 | 通过 HEAD/GET 检测 |
| `Missing` | 该阶段文件缺失/不可访问 | 同上 |

阶段名对应：

| 阶段名 | 含义 | 文件路径（相对 `/visualization/<run_id>/`） |
|---|---|---|
| `receptor_clean` | 预处理受体 | `work/preprocessed/receptor_clean.pdb` |
| `ligand_prepared` | 预处理配体 | `work/preprocessed/ligand_prepared.pdb` |
| `complex_initial` | 组装初始复合体 | `work/assembled/complex_initial.pdb` |
| `complex_fixed` | MD 前修复结构 | `work/md/complex_fixed.pdb` |
| `solvated` | 加水后结构 | `work/md/solvated.pdb` |
| `minimized` | 最小化后结构 | `work/md/minimized.pdb` |
| `equil_nvt_last` | NVT 末帧结构 | `work/md/equil_nvt_last.pdb` |
| `equil_npt_last` | NPT 末帧结构 | `work/md/equil_npt_last.pdb` |
| `trajectory` | 抽样轨迹入口 | `sampled_frames.json` |

### C. Display Controls

| 页面文字 | 中文含义 | 行为 |
|---|---|---|
| `Mode` | 渲染模式 | `cartoon/sticks/spheres` |
| `cartoon (chain trace)` | 主链轨迹线模式 | 线条+焦点球 |
| `sticks (atom + bond)` | 原子+键棒模式 | 球+圆柱 |
| `spheres (vdw)` | 范德华球模式 | 实例化球 |
| `Filter` | 显示过滤器 | 全部/仅受体/仅配体 |
| `all` | 全部（默认会隐藏水） | `shouldIncludeAtomByFilter` |
| `show ligand only` | 仅显示 ligand | 同上 |
| `show receptor only` | 仅显示 receptor | 同上 |
| `reset camera` | 重置相机到自适应 framing | `CameraResetController` |
| `show waters nearby (Reserved)` | 近邻水分子预留功能 | 当前禁用 |

### D. Future Modules（现阶段未实现，全部预留）

| 页面文字 | 中文含义 |
|---|---|
| `Membrane Mode` | 膜模式预留 |
| `Endpoint FE` | 端点自由能预留 |
| `PMF / Umbrella` | PMF/伞采样预留 |
| `Multi-run Comparison` | 多 run 对比预留 |
| `Whole Vesicle Explorer` | 全囊泡浏览预留 |

---

## 4.3 中区工具条词典

| 页面文字 | 中文含义 | 行为 |
|---|---|---|
| `Switch to Analytics Panel` | 切到分析面板 | 中区内容由 3D 切换为 Analytics |
| `Switch to 3D View` | 切回 3D 视图 | 中区内容切回 `MolecularCanvas` |
| `Show Insight Panel` | 显示右侧洞察栏 | 打开右侧悬浮侧栏 |
| `Hide Insight Panel` | 隐藏右侧洞察栏 | 关闭右侧悬浮侧栏 |
| `Close Insight Panel` | 关闭右侧栏（右栏内按钮） | 强制关闭右侧栏 |

---

## 4.4 3D 叠加层（Overlay）逐词解释

| 页面文字 | 中文含义 | 数据来源 |
|---|---|---|
| `current stage` | 当前阶段 | 选中 stage |
| `current pose` | 当前 pose | 选中 pose id（无则 `none`） |
| `current frame` | 当前帧号 | 仅 trajectory 有效 |
| `file source` | 当前显示文件路径 | stage/pose/frame 对应 URL |
| `render mode` | 实际渲染模式 | 可能与请求模式不同（性能降级时） |
| `requested` | 用户请求模式 | 显示为附加说明 |
| `role counts` | 各角色计数 | receptor/ligand/water/unresolved 统计 |
| `role resolution` | 角色解析状态 | `resolved/ambiguous/missing` |
| `legend` | 图例 | 颜色与形态解释 |
| `selection` | 当前选中原子摘要 | 点击原子后显示 |
| `serial` | PDB 原子序号 | `loadPdb` 解析字段 |
| `chain` | 链标识 | `chainId` |
| `role` | 当前原子角色 | role + confidence |
| `trajectory disabled` | 轨迹不可用提示 | sampled frames 缺失或无效 |
| `prev/next` | 上一帧/下一帧 | trajectory 抽样帧切换 |

ambiguous 红色警示文案的含义：

- 当前数据无法可靠区分 receptor 与 ligand
- 仅能用于流程验证，不可作为物理论证

---

## 4.5 右侧洞察栏词典

### A. Current Object Overview

| 字段 | 含义 | 来源 |
|---|---|---|
| `stage` | 当前阶段 | 页面状态 |
| `pose` | 当前 pose | 页面状态 |
| `frame` | 当前帧 | 页面状态 |
| `render mode` | 当前实际渲染模式 | scene context |
| `counts by role` | 角色计数摘要 | scene context |
| `role resolution` | 角色解析状态 | `structure_roles.json` |
| `role note` | 角色解析说明 | `resolution_notes[0]` |
| `atom count` | 当前原子总数 | PDB 解析结果 |
| `performance mode` | 性能策略说明 | 原子阈值降级策略 |
| `source file` | 当前源文件 URL | stage/pose/frame |
| `quick notes` | 快速边界说明 | manifest + role status 组合 |

### B. Pose Table

| 列名 | 含义 | 来源 |
|---|---|---|
| `pose_id` | pose 编号 | `outputs/docking/poses.csv` |
| `score` | pose 分数字段 | 同上（仅字段展示，不宣称物理意义） |
| `rmsd` | docking 表内 rmsd 字段 | 同上 |
| `backend` | 该行后端标记 | 同上 |
| `scientific_validity` | 该行有效性标记 | 同上 |

点击某一行行为：

- 设置 `selectedPoseId`
- 强制 stage 回到 `complex_initial`
- 中区显示对应 `pose_XXX.pdb`

### C. Metrics Cards

默认读取字段：

- `n_frames`
- `rmsd_mean_angstrom`
- `rmsd_max_angstrom`
- `rmsd_min_angstrom`
- `analysis_mode`
- `metrics_semantics`

数据文件：`outputs/analysis/binding/metrics.json`

### D. Provenance & Boundary

字段：

- `backend`
- `analysis_mode`
- `scientific_validity`
- `preprocess summary`
- `md_pdbfixer summary`

数据文件：

- `outputs/metadata/run_manifest.json`
- `outputs/metadata/preprocess_report.json`
- `outputs/metadata/md_pdbfixer_report.json`

### E. Report Viewer

- 显示 `outputs/reports/route_a_summary.md` 原文
- 当前是 `<pre>` 文本显示（不是 markdown 富渲染）

### F. Roadmap Boundary

- `Whole Vesicle Explorer` + `Status: Coming later`
- 明确告诉用户当前版本范围边界

---

## 4.6 Analytics Panel（中区切换后的分析面板）词典

| 页面文字 | 中文含义 | 状态 |
|---|---|---|
| `Analytics Panel` | 分析面板标题 | 已启用 |
| `RMSD` | RMSD 曲线页签 | 已启用 |
| `MD Log` | MD 日志页签 | 已启用 |
| `H-bond (Reserved)` | 氢键分析预留 | 预留 |
| `Contacts (Reserved)` | 接触分析预留 | 预留 |
| `Interface Map (Reserved)` | 界面图预留 | 预留 |
| `Endpoint FE (Reserved)` | 端点自由能预留 | 预留 |
| `PMF (Reserved)` | PMF 预留 | 预留 |

RMSD 图点击行为：

- 若 trajectory 抽样帧可用，点击点会切回 3D 并跳到对应帧。

---

## 5. 3D 粒子/形态/颜色为什么现在这样

## 5.1 你看到的“粒子”本体是什么

你看到的点或球，基本单位是 **原子（atom）**，不是“无意义特效粒子”。  
数据来自 PDB 的 `ATOM/HETATM` 记录，经 `loadPdb.js` 解析得到：

- 坐标：`x, y, z`
- 原子名：`atomName`
- 残基：`residue`
- 链：`chainId`
- 序号：`serial`
- 元素：`element`
- 原子键：`atomKey`

## 5.2 为什么会“看起来都差不多”

常见原因有四类：

1. 当前 run 的 `structure_roles.json` 是 `ambiguous`，大量原子角色为 `unresolved`。  
2. `complex_initial` 本身可能体量不大且空间分布紧，默认缩放下视觉细节有限。  
3. 如果你处于 `cartoon` 模式，焦点球是抽样显示，不是每个原子都放大。  
4. 颜色是“角色色 + 元素色”混合，整体风格是 calm scientific，不会用强烈霓虹对比。

## 5.2.1 `binding_route_a_3_13` 当前 `ambiguous` 的直接成因（基于原始输入溯源）

这个 run 的 `ambiguous` 不是前端渲染 bug，而是输入与预处理语义层面的客观结果。证据链如下：

1. `preprocess_report.json` 里 receptor 与 ligand 的输入路径完全相同，都是：  
`data/test_systems/minimal_complex/minimal_complex.pdb`
2. `minimal_complex_clean.pdb`、`receptor_clean.pdb`、`ligand_prepared.pdb` 的 SHA256 完全一致。
3. 该结构文件只有 `ATOM=327`，`HETATM=0`，且仅 `chain A`，本质上是单一蛋白链数据，不存在可独立识别的 ligand 原子集合。
4. `derived/structure_roles.json` 显示：  
`receptor_keys=327, ligand_keys=327, overlap=327`，重叠率 100%。
5. `scripts/export_visualization_bundle.py` 的角色解析规则在高重叠时会判定 `resolution_status=ambiguous`，重叠原子全部标记为 `unresolved`。

结论：你现在“几乎看不懂 ligand”，是因为当前输入并没有提供可区分的 ligand 语义，前端只能诚实显示 `unresolved`。

## 5.2.2 如何消除 `ambiguous`

要消除 `ambiguous`，核心不是调前端颜色，而是保证 receptor 与 ligand 数据源可区分。

1. 准备不同的 receptor 与 ligand 输入。  
receptor 输入应只包含受体；ligand 输入应只包含配体（可为独立小分子 PDB/MOL2/SDF，或从复合体中先拆分）。
2. 若只能拿到一个 complex 文件，先离线拆分再进入 Route A。  
按链 ID、残基名、配体残基列表等规则拆分，避免 receptor/ligand 使用同一文件。
3. 保持原子键（`atom_key`）稳定且可回链。  
`serial|chainId|residueId|residue|atomName` 需在受体与配体间形成可分离集合。
4. 重新跑预处理与导出 bundle。  
重新生成 `work/runs/<run_id>/preprocessed/*` 与 `frontend/visualization/<run_id>/derived/structure_roles.json`。
5. 验收标准：  
`resolution_status=resolved`，且 `unresolved` 计数接近 0（除非确有真实冲突原子）。

## 5.2.3 什么叫“理想的精确效果”

在当前架构下，理想效果不是“炫技渲染”，而是“结构语义可解释”：

1. `role resolution` 为 `resolved`。  
2. `show ligand only` 后画面应呈现清晰、体量较小且边界明确的 ligand 几何。  
3. `counts by role` 中 `ligand` 与 `receptor` 均有非零计数，`unresolved` 极低。  
4. 点击 ligand 原子时，`role=ligand (mapped)`，而不是 `unresolved (conflict)`。  
5. `cartoon / sticks / spheres` 三种模式都能呈现一致的 ligand 空间位置，仅几何表达不同。

## 5.3 三种渲染模式真实差异

### `cartoon`

- 主体：按链的 C-alpha 轨迹线（`Line`）
- 焦点：CA / ligand / unresolved 的实例化球
- 适合：先看整体形态与链走向

### `sticks`

- 主体：原子球 + 键圆柱
- 键来源优先级：
  - 先用 PDB 的 `CONECT`
  - 无 `CONECT` 且允许时，按共价半径阈值自动推断
- 适合：看局部拓扑连接关系

### `spheres`

- 主体：按元素半径缩放的范德华球（InstancedMesh）
- 适合：看体积占据与空间拥挤关系

## 5.4 颜色语义与色值

角色色（来自 `styles/tokens.css`）：

- receptor：`--accent-receptor: #4f6d8a`
- ligand：`--accent-ligand: #2a927a`
- water：`--accent-water: #5f7fa0`
- unresolved：`--accent-unresolved: #c84b31`

元素色：

- C：`#6f7e8e`
- N：`#2f6fed`
- O：`#c84b31`
- S：`#c99000`
- P：`#ad6f17`
- H：`#d7dee8`
- 金属：`#9b6ad4`

混色规则：

- `sticks/spheres` 模式下，会做角色色与元素色混合（blend）。
- 所以“颜色看起来接近”并不等于“数据无差别”；区别需结合 role、element 与 overlay 信息一起读。

## 5.6 颜色全集（当前实现中“可能出现”的颜色来源）

说明：渲染中存在光照、材质、透明度、抗锯齿与色彩插值，所以屏幕上的最终像素颜色是连续变化的。  
下面给出“全部离散颜色源 + 全部派生规则”，这才是可审计的完整颜色集合。

### A. 全局 Design Token 色（`src/styles/tokens.css`）

| 变量 | 色值 | 用途 |
|---|---|---|
| `--bg-canvas` | 非常浅蓝灰（近白） | 页面底色 |
| `--bg-panel` | 纯白 | 卡片底色 |
| `--bg-subtle` | 浅灰蓝 | 次级背景 |
| `--bg-scene` | 淡紫蓝 | 3D 场景背景 |
| `--border-default` | 淡灰蓝 | 默认边框/坐标轴网格 |
| `--border-strong` | 中性灰蓝 | 强边框/虚线边框 |
| `--text-primary` | 深海军蓝（接近墨蓝） | 主文本 |
| `--text-secondary` | 暗淡蓝灰 | 次文本 |
| `--text-muted` | 灰蓝 | 辅助文本 |
| `--accent-blue` | 亮天蓝 | 主强调色、RMSD 线 |
| `--accent-cyan` | 青绿色（湖蓝） | 点标记色 |
| `--accent-receptor` | 钢蓝 | receptor 主色 |
| `--accent-ligand` | 松石绿 | ligand 主色 |
| `--accent-water` | 灰蓝水色 | water 主色 |
| `--accent-unresolved` | 砖红 | unresolved 主色/警示高亮 |
| `--accent-selected` | 森林绿 | 选中强调（含图表） |
| `--element-carbon` | 灰蓝 | 元素 C |
| `--element-nitrogen` | 亮蓝 | 元素 N |
| `--element-oxygen` | 橙红 | 元素 O |
| `--element-sulfur` | 金黄 | 元素 S |
| `--element-phosphorus` | 棕黄 | 元素 P |
| `--element-hydrogen` | 浅灰 | 元素 H |
| `--element-metal` | 紫罗兰 | 金属元素（FE/ZN/MG/CA） |
| `--status-success` | 深绿 | 成功态文字/徽标 |
| `--status-warning` | 琥珀黄 | 警告态 |
| `--status-danger` | 橙红（警示红） | 危险态 |
| `--status-info` | 亮蓝 | 信息态 |
| `--status-reserved` | 灰蓝（Reserved） | Reserved 态 |

### B. 3D 角色与元素离散色

| 维度 | 枚举值 | 颜色来源 |
|---|---|---|
| 角色色 | `receptor/ligand/water/unresolved` | `buildRoleColorMap()` |
| 元素色 | `C/N/O/S/P/H/FE/ZN/MG/CA` | `buildElementColorMap()` |

### C. 3D 派生色规则（会产生很多“说明书未写到的中间色”）

| 场景 | 规则 |
|---|---|
| `cartoon` 焦点球 | `roleColor.lerp(elementColor, 0.22)` |
| `sticks` 原子球 | `blendColor(roleColor, elementColor, 0.40)` |
| `spheres` 原子球 | `blendColor(roleColor, elementColor, toneWeight=0.42)` |
| `sticks` 键圆柱 | `leftRoleColor.lerp(rightRoleColor, 0.5)` |
| 选中高亮球 | `accent-unresolved` + `opacity` + `emissive`（0.32~0.35） |

因此：你会看到比 token 表更多的中间色，这是算法性混色和光照导致的正常表现。

### D. 非 3D 组件颜色来源

| 位置 | 颜色来源 |
|---|---|
| Header/Badge | `badge--info/success/warning/danger/reserved` |
| Stage active | `accent-blue` 半透明背景 |
| Pose selected row | `accent-selected` 半透明背景 |
| RMSD 线与点 | `accent-blue` + `accent-cyan` |
| MD Log 线 | `accent-selected` |
| overlay warning | `accent-unresolved` 半透明边框与底色 |

## 5.7 状态全集（当前前端可出现的全部状态语义）

| 状态类别 | 可出现值 | 说明 |
|---|---|---|
| `resolution_status` | `resolved`, `ambiguous`, `missing` | 角色解析状态 |
| 原子 `role` | `receptor`, `ligand`, `water`, `unresolved` | 原子角色 |
| 原子 `roleConfidence` | `mapped`, `fallback`, `conflict` | 角色置信来源 |
| 渲染请求模式 | `cartoon`, `sticks`, `spheres` | 用户选择 |
| 渲染生效模式 | `cartoon`, `sticks`, `spheres` | 性能策略后实际模式 |
| 性能分层 | `full`, `reduced`, `huge` | 原子数量分层 |
| 可见性过滤 | `all`, `receptor`, `ligand` | 左栏 Filter |
| Stage 可用性 | `Ready`, `Missing` | 文件存在性检测 |
| Trajectory 可用性 | `available=true/false` | 抽样帧是否可用 |
| 数据加载状态 | `idle`, `loading`, `loaded`, `error` | 各 hook 通用状态 |
| 中区视图模式 | `structure`, `analytics` | 中区切换 |
| 右栏状态 | `is-open`, `is-closed` | 洞察侧栏开关 |
| Badge 变体 | `info`, `success`, `warning`, `danger`, `reserved` | 徽标视觉语义 |

## 5.8 选中高亮

点击原子后：

- 场景内显示一层半透明警示色高亮球（`accent-unresolved` 风格）
- overlay 显示 `selection / serial / chain / role(confidence)`
- 右侧概览同步对应上下文

---

## 6. 页面状态与 React 运行机制（开发者视角）

主要状态集中在 `src/pages/StructureExplorerPage.jsx`：

- `selectedRunId`
- `selectedStage`
- `selectedPoseId`
- `selectedFrameIndex`
- `displayMode`
- `visibilityFilter`
- `selectedAtomIndex`
- `centerViewMode`（`structure | analytics`）
- `isInsightPanelVisible`
- `sceneContext`（有效渲染模式、角色统计、性能说明等）

Hook 分工：

- `useRunArtifacts`：run 列表、阶段可用性、provenance 文本、trajectory frames
- `useRunManifest`：header 边界字段
- `usePoseTable`：pose 表格
- `useMetrics`：指标卡
- `useRmsdSeries`：RMSD 点序列
- `useMdLogSeries`：MD 日志序列
- `useStructureRoles`：role 映射与状态

数据流大意：

1. 选 run -> hooks 拉取该 run 的各类 artifact。  
2. 选 stage/pose/frame -> `MolecularCanvas` 解析对应 PDB。  
3. `mergeStructureRoles` 把 `structure_roles.json` 合并进每个 atom。  
4. 渲染器根据 `displayMode + performancePlan` 决定几何输出。  
5. 交互结果回写 `sceneContext`，供右侧概览显示。  

---

## 7. 数据来源总表（按 UI 模块）

| UI 模块 | 数据文件（相对 `/visualization/<run_id>/`） |
|---|---|
| Header badges | `outputs/metadata/run_manifest.json` |
| Run 列表 | `index.json`（位于 `/visualization/index.json`） |
| Stage 切换 | `work/preprocessed/*.pdb`, `work/assembled/*.pdb`, `work/md/*.pdb` |
| Pose Table | `outputs/docking/poses.csv` |
| Pose 结构切换 | `outputs/docking/poses/pose_*.pdb` |
| Metrics Cards | `outputs/analysis/binding/metrics.json` |
| RMSD | `outputs/analysis/binding/rmsd.csv` |
| MD Log | `work/md/md_log.csv` |
| Provenance | `outputs/metadata/preprocess_report.json`, `outputs/metadata/md_pdbfixer_report.json` |
| Report Viewer | `outputs/reports/route_a_summary.md` |
| 角色映射 | `derived/structure_roles.json` |
| 轨迹抽样 | `sampled_frames.json` + `frame_pdb/*.pdb`（若有） |

---

## 8. 如何做一次完整“功能验收”

## 8.1 数据准备验收

1. 执行 `export_visualization_bundle.py`。  
2. 检查 `frontend/visualization/<run_id>/work` 和 `outputs` 是链接。  
3. 检查 `derived/structure_roles.json` 已生成。  
4. 检查 `frontend/public/visualization/` 无运行数据。  

## 8.2 页面功能验收

1. Header 有 `run_id/backend/scientific_validity/analysis_mode`。  
2. 左栏 stage 可切换，`Missing` 阶段不可点击。  
3. 中区可在 3D 与 Analytics 间切换。  
4. 右栏可打开并可关闭。  
5. Pose Table 点击能联动 3D pose。  
6. RMSD 与 MD Log 可显示，Reserved tabs 存在。  
7. `ambiguous` 时出现显著边界提示。  

## 8.3 构建验收

1. `npm run lint` 通过。  
2. `npm run build` 通过并产出 `dist/`。  

---

## 9. 常见问题与排查

## 9.1 看不到 run 列表

排查：

- 是否执行了导出脚本并生成 `/visualization/index.json`
- run_id 目录是否在 `frontend/visualization/` 下
- Vite dev server 是否正常运行

## 9.2 3D 一片空白或无法加载

排查：

- 当前 stage 文件是否 `Missing`
- 浏览器网络面板是否 404 对应 PDB URL
- `sampled_frames.json` 是否存在但 `pdb_file` 不可解析

## 9.3 为什么我感觉 receptor/ligand 没区别

排查：

- 看 overlay 的 `role resolution` 是否 `ambiguous`
- 看 `derived/structure_roles.json` 的 `resolution_notes`
- 如果角色本身不可分，前端会诚实显示 `unresolved`，不会伪造差异

## 9.4 为什么切换模式后还是不够直观

建议顺序：

1. 先 `cartoon` 看全局形态。  
2. 再 `sticks` 看连接关系。  
3. 配合 `show receptor only / show ligand only`。  
4. 点击关键原子看 overlay 的 `selection` 字段。  

---

## 10. 核心代码索引（快速定位）

页面与布局：

- `src/pages/StructureExplorerPage.jsx`
- `src/components/layout/TopHeader.jsx`
- `src/components/layout/LeftControlPanel.jsx`
- `src/components/layout/RightInsightPanel.jsx`
- `src/components/layout/BottomAnalyticsPanel.jsx`

3D 渲染：

- `src/components/scene/MolecularCanvas.jsx`
- `src/components/scene/MolecularRepresentation.jsx`
- `src/components/scene/CartoonRepresentation.jsx`
- `src/components/scene/SticksRepresentation.jsx`
- `src/components/scene/SpheresRepresentation.jsx`
- `src/components/scene/SelectionOverlay.jsx`
- `src/components/scene/sceneRoles.js`

数据与加载：

- `src/services/artifactRegistry.js`
- `src/services/loaders/loadPdb.js`
- `src/services/loaders/loadCsv.js`
- `src/services/loaders/loadJson.js`
- `src/services/loaders/loadTrajectoryFrames.js`
- `src/services/adapters/visualizationBundleAdapter.js`
- `src/hooks/useRunArtifacts.js`
- `src/hooks/useRunManifest.js`
- `src/hooks/usePoseTable.js`
- `src/hooks/useMetrics.js`
- `src/hooks/useRmsdSeries.js`
- `src/hooks/useMdLogSeries.js`
- `src/hooks/useStructureRoles.js`

样式：

- `src/styles/tokens.css`
- `src/styles/globals.css`
- `src/styles/layout.css`

bundle 导出：

- `scripts/export_visualization_bundle.py`

---

## 11. 关于 frontend/public/visualization 的定位

当前建议是：

- `frontend/visualization/`：运行数据入口（可包含 symlink/junction/hardlink + 派生轻量文件）
- `frontend/public/visualization/`：非运行数据区，仅保留静态占位（例如 `.gitkeep`）

为什么还保留 `frontend/public/visualization/` 目录：

- 兼容历史路径和团队习惯，不会影响现在的运行契约。
- 未来若要放极轻量、非 run 绑定静态资源，也有固定位置。
- 当前实现已通过脚本清理该目录，避免误放运行数据。

---

## 12. 结论：你应如何解读当前页面

正确解读方式：

- 把它当作“结构与流程可视化工作台”，不是“科学结论生成器”。
- 先看 Header 与 Provenance 的边界标签，再看 3D/指标。
- 若看到 `ambiguous`，就按“不可靠区分 receptor/ligand”解释。
- Reserved 区域存在是为了架构可扩展，不代表功能已完成。

这套页面的价值在于：**结构清晰、命名规范、边界诚实、可继续扩展**。
