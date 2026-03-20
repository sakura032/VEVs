# 虚拟细胞囊泡对接 MD 模拟工程蓝图（`vesicle/`）

> 更新时间：2026-03-20
> 核心架构：MARTINI CG + 纯 Python 几何组装 + GROMACS 物理弛豫
> 核心战略：方案 B（独立建膜 -> 独立预平衡 -> 脱水对接 -> 整体拉伸动力学）

---

## 1. 项目目标与执行原则

### 1.1 总目标
构建一条可复现的全流程：
1. 纯 Python 生成大尺度 CG 囊泡/膜片干态初始结构。
2. 用 GROMACS 完成物理弛豫与稳定化。
3. 进入对接、SMD 与 US，输出可分析的 PMF 曲线。

### 1.2 执行原则
- 先蛋白，后脂质：先占坑再填膜，减少后期重排成本。
- 几何与物理分层：Python 做几何初构，GROMACS 做真实动力学。
- 参数必须可追溯：关键参数落地前必须二次核验官方来源。
- 统一数据接口：下游模块只消费标准化实体，不接触原始脏数据。

---

## 2. 最新状态快照（截至 2026-03-20）

### 2.1 已完成
1. Phase 1 脂质基础能力完成：
- `vesicle/models/lipid.py` 已整合蓝图、实体、脂质库、解析器、构建器；
- 通过锚点法统一方向定义，支持 CHOL 特例（硬编码构象）；
- 脂质工厂测试通过：`vesicle/test/test_factory.py`。

2. Phase 2（任务调换后）已完成前两算法：
- `vesicle/utils/geometry.py`
  - `generate_fibonacci_sphere(...)`
  - `align_lipid_to_sphere(...)`
- 几何测试通过：`vesicle/test/test_geometry.py`。

### 2.2 结构调整（已生效）
- 删除：`vesicle/utils/lipid_factory.py`
- 删除：`vesicle/utils/lipid_gro_parser.py`
- 现状：脂质能力以 `vesicle/models/lipid.py` 为唯一主入口。

---

## 3. 分工更新（A/B 已调换，避免冲突）

## 3.1 Phase 2 当前分工
- Person B（你）：
  - 负责几何内核前两算法（Fibonacci 球面布点 + 脂质对齐旋转平移）
  - 当前状态：已完成并测试通过

- Person A：
  - 接手 KD-Tree 空间约束、蛋白先放置逻辑、碰撞接口
  - 当前状态：待实现

## 3.2 后续阶段默认分工（建议保持）
- Person A：蛋白链路、KD-Tree/Builder 主循环、GROMACS 参数与流程联调
- Person B：脂质数据治理、几何算子、输出器与数据标准化、接口稳定性测试

---

## 4. 核心算法总表（按模块）

## 4.1 脂质标准化（已完成）
文件：`vesicle/models/lipid.py`
- 锚点法方向定义：
  - `head_center = mean(head_anchors)`
  - `tail_center = mean(tail_anchors)`
  - `vector = normalize(tail_center - head_center)`
- 坐标归一：`coords -= head_center`
- CHOL 特例：硬编码 `ROH -> C2` 主轴

## 4.2 球面布点（已完成）
文件：`vesicle/utils/geometry.py`
- Fibonacci + 黄金角
- 面积补偿：`z = 1 - 2*(i+0.5)/N`
- 支持任意球心平移

## 4.3 脂质对齐（已完成）
文件：`vesicle/utils/geometry.py`
- 目标法线：`n = normalize(target - center)`
- 外叶：`v_target = -n`；内叶：`v_target = n`
- 角度：`angle = arccos(clip(dot(v_intrinsic, v_target), -1, 1))`
- 奇点处理：
  - `angle < eps` 直接平移
  - `angle -> pi` 动态构造正交旋转轴

## 4.4 KD-Tree 碰撞过滤（阶段二待完成）
建议文件：`vesicle/utils/collision.py`
- 构建：`scipy.spatial.cKDTree`
- 查询：`min_dist < threshold` 判碰
- 阈值默认：`0.5 nm`（0.5为ai给出不要太信任，最好先按官方参数核验）

## 4.5 总装循环（阶段三待完成）
建议文件：`vesicle/models/vesicle_builder.py`
- 先放蛋白并构建障碍树
- 内外叶按比例布脂，碰撞即跳过
- 输出组装统计与异常报告

## 4.6 `.gro` 写出（阶段三待完成）
建议文件：`vesicle/utils/gro_writer.py`
- 严格列宽格式
- 原子序号溢出循环编号（`% 100000`）
- 大体系一次性缓冲写出（`list + ''.join`）

---

## 5. 六阶段细化计划（统筹版）

## 阶段一：核心数据类与砖块准备（已完成）
目标：脂质数据、模板解析、方向标准化。
完成标志：`lipid.py + test_factory.py` 可稳定构建 POPC/CHOL。

## 阶段二：核心 3D 几何引擎（进行中）
目标：形成可复用无状态数学内核。
- 已完成：
  1. Fibonacci 球面点云
  2. 脂质对齐旋转平移（含奇点防护）
- 待完成：
  3. KD-Tree 碰撞过滤
  4. 蛋白占位与障碍初始化

## 阶段三：囊泡与膜片总装（待启动）
目标：输出可读 `.gro` 干态大体系。
核心：先蛋白后脂质、内外叶不对称配比、碰撞拒绝。

## 阶段四：独立组件物理弛豫（待启动）
目标：EM + NVT/NPT 消除几何拼装伪影。
核心：自动化脚本、去水与拓扑一致性。

## 阶段五：精准脱水对接（待启动）
目标：囊泡与膜片在安全临界距离组装为复合体。
核心：bbox 间距控制、干态合并与 top 同步。

## 阶段六：整体再平衡与 SMD/US（待启动）
目标：获得可解释 PMF 曲线。
核心：Pull groups 定义、SMD 抽窗、WHAM 重建。

---

## 6. 里程碑与验收门槛

- M1（已达成）：脂质工厂稳定输出 `Lipid3D`。
- M2（进行中）：几何内核可完成无奇点对齐与球面布点。
- M3（下一目标）：KD-Tree 接入后可无碰撞种膜并输出 `.gro`。
- M4：组件弛豫收敛且无明显结构崩坏。
- M5：对接复合体稳定并可进入 SMD。
- M6：US 全窗口完成并输出 PMF。

---

## 7. 未来 72 小时建议执行序列（按依赖顺序）

1. Person A 完成 `collision.py`（KD-Tree 构建 + 判碰接口）
2. Person A 完成蛋白占位原型（先放置 + 障碍树初始化）
3. Person B 输出几何接口文档（函数输入输出、单位、异常）
4. A/B 合并联调 `vesicle_builder.py` 雏形
5. 增加阶段二回归测试（几何 + 判碰组合测试）

---

## 8. 文档维护约定

- 每次阶段性交付后，必须同步更新：
  - “最新状态快照”
  - “分工更新”
  - “里程碑状态”
- 当参数发生变更时，必须在提交说明中写明：
  - 变更原因
  - 来源依据
  - 验证结果

（完）

