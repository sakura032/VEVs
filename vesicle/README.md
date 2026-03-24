# 囊泡模块说明

> 更新时间：2026-03-24  
> 核心技术栈：MARTINI 粗粒度模型 + Python 几何组装 + GROMACS 后续弛豫

## 1. 模块目标

`vesicle/` 目前仅实现“干态囊泡几何组装”这一阶段，未添加后续的水化、离子化、能量最小化、平衡和 PMF。

当前主目标是稳定输出一个可复现的外泌体粗粒度初始结构，流程包括：

1. 读取并标准化脂质模板与蛋白模板。
2. 以 TEM 岛屿化方式放置 `CD9 / CD81 / CD63`。
3. 在蛋白排斥半径存在的前提下铺设外叶与内叶脂质。
4. 输出 `vesicle.gro` 与 `topol.top`，供后续 GROMACS 使用。

默认输出目录是 `vesicle/outputs/basic_vesicle/`，也支持写到任意命名 `vesicle/outputs/<dataset_name>/` 数据集目录。

## 2. 当前目录结构与职责

### `vesicle/models/lipid.py`

职责：

- 定义脂质蓝图 `LipidBlueprint`
- 定义运行时三维脂质对象 `Lipid3D`
- 维护项目当前使用的 `LIPID_LIBRARY`
- 提供 `build_lipid_3d(...)`，把原始模板转成 builder 可直接放置的局部刚体

当前实现要点：

- 脂质头部中心会被平移到局部原点
- 本征方向统一定义为“头部中心 -> 尾部中心”
- `CHOL` 使用硬编码模板
- 其他脂质通过固定列宽 `.gro` 解析得到

### `vesicle/models/protein.py`

职责：

- 定义蛋白模板对象 `Protein`
- 从单分子 CG `.gro` 文件读取 bead 坐标
- 计算放置时常用的几何量：
  - 膜平面投影半径
  - 跨膜中心
  - 包围盒
- 提供 `prepared_for_placement()`，把模板整理到适合球面放置的局部坐标系

当前实现要点：

- `Protein.from_gro(...)` 是蛋白模板标准入口
- `prepared_for_placement()` 会先把 `tm_center` 平到 `z=0`，再把 `xy` 几何中心平到原点
- `copy_template()` 用于复用已加载模板，避免重复读取同一份 `.gro`

### `vesicle/utils/geometry.py`

职责：

- 提供球面布点
- 提供局部模板到球面的刚体对齐
- 提供 TEM 岛屿内部的局部角扰动

当前公开接口：

- `generate_fibonacci_sphere(...)`
- `align_template_to_sphere(...)`
- `align_lipid_to_sphere(...)`
- `apply_local_axis_angle_perturbation(...)`

说明：

- `apply_local_axis_angle_perturbation(...)` 采用“随机轴 + 均匀角度”的局部角扰动
- 该算法故意保留中心更密、边缘更疏的局部分布，用于模拟 TEM 微结构域聚簇

### `vesicle/utils/collision.py`

职责：

- 维护蛋白 bead 的绝对坐标
- 构建 KD-tree
- 判断候选点是否落入蛋白排斥壳内

当前实现要点：

- 该模块已收敛为纯工具层
- 不再负责蛋白放置策略
- builder 当前把 `CD9 / CD81 / CD63` 都按 `surface_transmembrane` 处理

### `vesicle/models/vesicle_builder.py`

职责：

- 定义输出账本记录 `AtomRecord`
- 定义核心总装器 `VesicleBuilder`
- 串联蛋白放置、双叶铺脂和 `.gro/.top` 写出

当前主流程：

1. `place_proteins_clustered(...)`
2. `detector.build_trees()`
3. `_fill_lipid_leaflet(self.R_out, self.comp_out, False)`
4. `_fill_lipid_leaflet(self.R_in, self.comp_in, True)`
5. `write_outputs(...)`

额外入口：

- `VesicleBuilder.make_protein_clusters(...)`
  - 直接生成默认三岛、45 蛋白输入

## 3. 当前默认生物学设定

### 蛋白三岛

默认三岛45蛋白异质性布局为：

- 岛 0：`8 x CD9 + 7 x CD81`
- 岛 1：`7 x CD9 + 8 x CD81`
- 岛 2：`15 x CD63`

对应当前项目的假设：

- `CD9 / CD81` 偏向质膜来源，倾向混居
- `CD63` 偏向晚期内体来源，更接近独居岛

### 脂质双叶配方

外叶：

- `CHOL`：45%
- `POPC`：35%
- `DPSM`：20%

内叶：

- `CHOL`：45%
- `POPE`：35%
- `POPS`：15%
- `POP2`：5%

builder 采用“先转精确整数个数，再打乱脂质序列”的做法，而不是逐点概率抽样。
计数分配使用最大余数法，以保证中等规模体系下配方更稳定、可复现。

## 4. 输出文件与前端同步

### 一条命令生成基础囊泡

推荐直接运行：

```bash
python -m vesicle.scripts.build_default_basic_vesicle
```

默认行为：

- 使用 `VesicleBuilder.make_protein_clusters(...)` 构造默认 45 蛋白三岛输入
- 默认固定随机种子为 `11`
- 脚本层把岛内角半径放宽到 `0.60 rad`
- 脚本层把蛋白落位最大尝试次数提高到 `200`
- 组装基础囊泡
- 写出到 `vesicle/outputs/basic_vesicle/`
- 自动同步到 `frontend/visualization/vesicle/basic_vesicle/`
- 更新前端数据集索引 `frontend/visualization/vesicle/index.json`

Whole Vesicle Explorer 会从 `frontend/visualization/vesicle/index.json` 读取可用数据集，并默认选择最近一次同步成功的数据集。

### 写到新的数据集目录

如果你要把默认构建逻辑写到新的数据集目录，可指定output-dir,例如 `vesicle3_24`，运行：

```bash
python -m vesicle.scripts.build_default_basic_vesicle --output-dir vesicle/outputs/vesicle3_24
```

这条命令会：

- 生成 `vesicle/outputs/vesicle3_24/vesicle.gro`
- 生成 `vesicle/outputs/vesicle3_24/topol.top`
- 自动同步到 `frontend/visualization/vesicle/vesicle3_24/`
- 更新 `frontend/visualization/vesicle/index.json`

如果你只想写本地输出、不进入前端可视化列表，运行：

```bash
python -m vesicle.scripts.build_default_basic_vesicle --output-dir vesicle/outputs/<dataset_name> --no-sync-frontend
```

自动同步只支持 `vesicle/outputs/<dataset_name>/` 这一层级。  
如果开启同步但输出目录不在这个根下，脚本会先给出警告，再报错退出。

### 手动同步

通用同步脚本是：

```bash
python -m vesicle.scripts.sync_vesicle_to_frontend --source-dir vesicle/outputs/<dataset_name>
```

它会把 `vesicle/outputs/<dataset_name>/` 镜像到
`frontend/visualization/vesicle/<dataset_name>/`，并维护 `index.json`。

### `vesicle.gro`

当前约定：

- 使用 GROMACS 固定列宽格式输出
- `res_id` 与 `atom_id` 回绕到 `1..99999`
- 输出前把体系整体平移到正坐标区域
- 最外层默认保留 5 nm padding
- 默认输出位置为 `vesicle/outputs/basic_vesicle/vesicle.gro`
- 也可通过 `--output-dir` 改成 `vesicle/outputs/<dataset_name>/vesicle.gro`

### `topol.top`

当前约定：

- 所有力场与分子 `itp` 统一从 `vesicle/data/forcefields/` 目录相对引入
- 始终 include `vesicle/data/forcefields/martini_v2.2.itp`
- 自动 include 本次体系中实际出现的官方脂质 `itp`
- 自动 include 本次体系中实际出现的蛋白 `itp`
- `[ molecules ]` 中蛋白名使用 martinize 输出的 moleculetype 名：
  - `CD9_0`
  - `CD63_0`
  - `CD81_0`
- 脂质直接使用 MARTINI 力场中已有的分子名
- 默认输出位置为 `vesicle/outputs/basic_vesicle/topol.top`
- 也可通过 `--output-dir` 改成 `vesicle/outputs/<dataset_name>/topol.top`

## 5. 测试体系

`vesicle/test/` 目前全部采用 pytest 回归测试，覆盖：

- 脂质模板标准化
- 球面布点与对齐
- 局部角扰动
- 蛋白模板读取与放置前整理
- 默认三岛构造器
- builder 总装
- `.gro` / `.top` 输出
- 多数据集输出与前端同步索引

从仓库根目录运行：

```bash
python -m pytest -q -p no:cacheprovider vesicle/test
```

## 6. 当前边界

`vesicle/` 当前只负责“结构初始组装”和“拓扑写出”。

暂不负责：

- 水化
- 离子化
- 能量最小化
- NVT / NPT 平衡
- 对接、SMD、US、PMF 等后续流程

这些内容属于下游模拟阶段，不在本目录当前实现范围内。
