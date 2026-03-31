"""
vesicle.models.vesicle_builder
==============================

这是当前 `vesicle/` 目录里的总装核心。

它负责把前面几个底层模块真正串起来：

1. `protein.py`
   提供可放置的蛋白模板。
2. `geometry.py`
   提供球面布点、刚体对齐和局部岛屿扰动。
3. `collision.py`
   提供基于 KD-tree 的蛋白挖洞查询。
4. `lipid.py`
   提供可直接放置的脂质模板。

总流程固定为：
1. 放蛋白岛屿；
2. 建全局蛋白碰撞树；
3. 铺外叶；
4. 铺内叶；
5. 写出 `.gro` 和 `.top`。

不处理后续 GROMACS 物理弛豫，只负责干态组装。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np

from vesicle.models.lipid import LIPID_LIBRARY, build_lipid_3d
from vesicle.models.protein import Protein
from vesicle.utils.collision import CollisionDetector
from vesicle.utils.geometry import (
    align_lipid_to_sphere,
    align_template_to_sphere,
    apply_local_axis_angle_perturbation,
    generate_fibonacci_sphere,
)


@dataclass
class AtomRecord:
    """
    输出账本中的单条原子/bead 记录。

    这里的字段命名直接贴近 GROMACS `.gro` 的核心列：
    - `res_id` / `res_name`
    - `atom_id` / `atom_name`
    - `x, y, z`

    builder 不在生成阶段直接拼接字符串，而是先记结构化账本，
    这样后续无论要写 `.gro`、统计分子数、还是调试坐标，都更方便。
    计算和序列化是分开的。
    """

    res_id: int #这一行 bead 属于哪个分子，写进 .gro residue number 那一列的编号
    res_name: str #写进 .gro residue name 那一列的名字
    atom_name: str #写进 .gro atom name 那一列的名字
    atom_id: int #这一行 bead 在整个文件里是第几个粒子
    x: float
    y: float
    z: float


class VesicleBuilder:
    """
    外泌体囊泡组装器。
    本身不定义底层数据结构，而是把几个模块的功能串起来，完成从输入到输出的总装流程。

    这个类的设计目标不是“高度抽象的通用膜生成框架”，
    只是围绕当前项目需求，把以下几件事稳定做好：

    - 三个 TEM 岛屿的异质性蛋白聚簇；
    - 蛋白先放、脂质后铺；
    - 内外叶不对称真实配方；
    - 大体系账本和 `.gro/.top` 输出。
    """

    # 蛋白模板在局部坐标系下的本征法向，假设已经沿+z表示膜法线。
    # 当前假设 `prepared_for_placement()` 后的模板“膜法线方向”近似沿 +z。
    PROTEIN_ALIGNMENT_AXIS = np.array([0.0, 0.0, 1.0], dtype=np.float64)

    # 岛内扰动的最大角半径，单位为弧度。决定一个岛屿内蛋白离种子点能散多远。
    # 数值本身是当前项目建模约定，而不是通用真理。
    PROTEIN_CLUSTER_MAX_ANGLE = 0.26

    # 每个蛋白在一个岛屿中心附近最多尝试多少次候选落位。
    PROTEIN_PLACEMENT_MAX_TRIES = 100

    # 两个蛋白中心距离阈值的放大因子。 蛋白之间用投影半径和的1.25倍做安全距离。
    # 实际阈值 = 1.25 * (r_i + r_j)。
    PROTEIN_SPACING_FACTOR = 1.25

    # 铺脂时会多生成30%的球面候选点，用来抵消蛋白挖洞跳过太多可用点位的损失。固定配方总数，增加候选点冗余
    LIPID_POINT_OVERSAMPLE = 1.30

    # `.top` 里蛋白分子名与 builder 输入名并不完全一致。
    # 这里统一维护 name -> moleculetype ，把builder输入名映射到实际要写入topol.top的分子类型名。
    PROTEIN_MOLECULE_MAP = {"CD9": "CD9_0", "CD63": "CD63_0", "CD81": "CD81_0"}
    PROTEIN_ITP_MAP = {"CD9": "CD9_0.itp", "CD63": "CD63_0.itp", "CD81": "CD81_0.itp"}
    FORCEFIELD_DIR = Path("vesicle/data/forcefields")
    FORCEFIELD_INCLUDE = "martini_v2.2.itp"
    DEFAULT_OUTPUT_DIR = Path("vesicle/outputs/basic_vesicle")
    DEFAULT_GRO_NAME = "vesicle.gro"
    DEFAULT_TOP_NAME = "topol.top"

    # 这些是 Martini 官方 Martini 2 lipidome 页面给出的脂质 `.itp` 文件名。
    # builder 会把它们写成指向 `vesicle/data/forcefields/` 的相对 include 路径。
    LIPID_ITP_MAP = {
        "CHOL": "martini_v2.0_CHOL_02.itp",
        "POPC": "martini_v2.0_POPC_02.itp",
        "DPSM": "martini_v2.0_DPSM_01.itp",
        "POPE": "martini_v2.0_POPE_02.itp",
        "POPS": "martini_v2.0_POPS_02.itp",
        "POP2": "martini_v2.0_POP2_01.itp",
    }

    # 这个顺序决定 `[ molecules ]` 的输出展示顺序，
    # 目的是让文件更易读，而不是让 dict 的随机顺序直接落盘。
    MOLECULE_WRITE_ORDER = [
        "CD9_0",
        "CD63_0",
        "CD81_0",
        "CHOL",
        "POPC",
        "DPSM",
        "POPE",
        "POPS",
        "POP2",
    ]

    # 默认半径50nm的外泌体含45个蛋白，分居于三个蛋白质岛屿。
    # 这个布局直接编码了当前项目最关心的生物学异质性：
    # - 岛 0 / 岛 1：CD9 与 CD81 混居
    # - 岛 2：CD63 独居
    DEFAULT_THREE_ISLAND_LAYOUT = [
        {"CD9": 8, "CD81": 7},
        {"CD9": 7, "CD81": 8},
        {"CD63": 15},
    ]

    def __init__(
        self,
        radius_out: float = 50.0,
        thickness: float = 4.0,
        lipid_exclusion_radius: float = 0.8,
        lipid_area: float = 0.65,
    ) -> None:
        """
        初始化囊泡几何参数与默认脂质配方。

        参数
        ----
        radius_out
            外叶目标半径，单位 nm。
        thickness
            膜厚，单位 nm。
        lipid_exclusion_radius
            脂质头部点离蛋白 bead 的排斥半径，单位 nm。
        lipid_area
            估算脂质总数时使用的平均单分子面积，单位 nm^2。
        """
        self.R_out = float(radius_out)
        self.thickness = float(thickness)
        self.lipid_exclusion_radius = float(lipid_exclusion_radius)
        self.lipid_area = float(lipid_area)

        #合法性检查，尤其注意 thickness < R_out，不然内叶半径会变成负数。
        if not np.isfinite(self.R_out) or self.R_out <= 0.0:
            raise ValueError(f"radius_out must be a positive finite scalar, got {radius_out}")
        if not np.isfinite(self.thickness) or self.thickness <= 0.0:
            raise ValueError(f"thickness must be a positive finite scalar, got {thickness}")
        if self.thickness >= self.R_out:
            raise ValueError("thickness must be smaller than radius_out")
        if not np.isfinite(self.lipid_exclusion_radius) or self.lipid_exclusion_radius < 0.0:
            raise ValueError("lipid_exclusion_radius must be finite and non-negative")
        if not np.isfinite(self.lipid_area) or self.lipid_area <= 0.0:
            raise ValueError(f"lipid_area must be a positive finite scalar, got {lipid_area}")

        # 三层半径的角色必须分清：
        # - R_out：外叶头部近似所在球面
        # - R_in ：内叶头部近似所在球面
        # - R_mid：蛋白跨膜中心近似所在球面
        self.R_in = self.R_out - self.thickness
        self.R_mid = self.R_out - self.thickness / 2.0

        # 默认的建模配方：
        # 外叶偏刚性与保护层，内叶偏负电荷与信号层。
        self.comp_out = {"CHOL": 0.45, "POPC": 0.35, "DPSM": 0.20}
        self.comp_in = {"CHOL": 0.45, "POPE": 0.35, "POPS": 0.15, "POP2": 0.05}

        # 重要的性能优化：存“每种脂质的标准模板”
        # 同一种脂质会被放几百到几千次，没有必要每次都重新解析模板。
        self._lipid_templates: Dict[str, object] = {}
        self._reset_state()

    @classmethod
    def make_protein_clusters(
        cls,
        protein_dir: str | Path = "vesicle/data/proteins",
    ) -> List[List[Protein]]:
        """
        构造默认的 45 蛋白三岛输入。
        返回岛屿列表，每个岛屿里都是一串蛋白模板。
        返回值是 `build(cluster_assignments)` 需要的标准输入格式：
        `List[List[Protein]]`

        默认布局固定为：
        - 岛 0：8 x CD9 + 7 x CD81
        - 岛 1：7 x CD9 + 8 x CD81
        - 岛 2：15 x CD63
        """
        base_dir = Path(protein_dir)
        if not base_dir.exists():
            raise FileNotFoundError(f"protein template directory does not exist: {base_dir}")

        # 避免为了默认 45 蛋白布局反复读取同一个 `.gro` 文件。
        # 先把每种.gro蛋白模板各读一次，直接复制内存模板，反复copy_template()
        template_cache = {
            protein_name: Protein.from_gro(
                protein_name,
                base_dir / f"cg_{protein_name}_clean.gro",
            )
            for cluster_spec in cls.DEFAULT_THREE_ISLAND_LAYOUT
            for protein_name in cluster_spec
        }

        cluster_assignments: List[List[Protein]] = []
        for cluster_spec in cls.DEFAULT_THREE_ISLAND_LAYOUT:
            cluster: List[Protein] = []
            for protein_name, count in cluster_spec.items():
                for _ in range(count):
                    cluster.append(template_cache[protein_name].copy_template())
            cluster_assignments.append(cluster)

        return cluster_assignments

    def _reset_state(self) -> None:
        """
        清空一次 build 周期内的所有运行态。
        这样同一个 builder 对象可以重复用于不同体系，而不会把上一次的账本残留带进来。
        """
        self.atoms: List[AtomRecord] = []
        self.molecule_counts: Dict[str, int] = {}
        self.current_res_id = 0
        self.current_atom_id = 0
        self.detector = CollisionDetector()

        # 这两个缓存只服务于“蛋白中心级别的局部防撞”。
        # 它们比 bead 级 KD-tree 更轻，因此适合放在蛋白逐个落位的循环里快速使用。
        self._protein_centers: List[np.ndarray] = []
        self._protein_radii: List[float] = []

        # 保留一个公开可读别名，便于外部检查当前蛋白中心分布。
        self.protein_centers = self._protein_centers

    @staticmethod
    def _safe_gro_id(raw_id: int) -> int:
        """
        统一坐标合法性检查，确保整数编号都合 `.gro` 格式要求。
        把任意累计编号安全回绕到 `1..99999`。

        `.gro` 的 residue id 与 atom id 都是 5 列宽，
        所以不能把 100000 原样写进去，否则会直接破坏格式。
        """
        return ((int(raw_id) - 1) % 99999) + 1

    @staticmethod
    def _as_coords(name: str, coords: np.ndarray) -> np.ndarray:
        """统一检查坐标矩阵是否合法,即形状必须为 (N, 3)。"""
        arr = np.asarray(coords, dtype=np.float64)
        if arr.ndim != 2 or arr.shape[1] != 3:
            raise ValueError(f"{name} must have shape (N, 3), got {arr.shape}")
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{name} contains NaN or Inf")
        return arr

    def _molecule_name_for_counting(self, res_name: str) -> str:
        """
        把 builder 内部的残基名映射到 `.top` 里需要统计的分子名。

        脂质名通常可以直接使用；
        蛋白则需要映射到 martinize 生成的 `*_0` moleculetype 名。
        """
        return self.PROTEIN_MOLECULE_MAP.get(res_name, res_name)

    def _add_molecule_to_ledger(
        self,
        res_name: str,
        bead_names: List[str],
        coords: np.ndarray,
    ) -> None:
        """
        把一个分子整体写入账本。

        这是 builder 最底层的统一入账接口，所有蛋白和脂质最后都走这里。
        它同时负责：
        - 分子级 `res_id` 自增；
        - bead 级 `atom_id` 自增；
        - `.top` 用的 molecule 统计。
        """
        coords_arr = self._as_coords("coords", coords)
        if len(bead_names) != len(coords_arr):
            raise ValueError(
                f"bead_names and coords length mismatch: {len(bead_names)} != {len(coords_arr)}"
            )

        self.current_res_id += 1
        safe_res_id = self._safe_gro_id(self.current_res_id)

        molecule_name = self._molecule_name_for_counting(res_name)
        self.molecule_counts[molecule_name] = self.molecule_counts.get(molecule_name, 0) + 1

        # 把每个 bead 变成 AtomRecord，统一入账到 self.atoms 里。
        # `.gro` 里 res_name / atom_name 都是 5 列宽。
        # 超长名字这里直接截断，避免写文件时破坏定宽布局。
        gro_res_name = res_name[:5]
        for bead_name, coord in zip(bead_names, coords_arr):
            self.current_atom_id += 1
            safe_atom_id = self._safe_gro_id(self.current_atom_id)
            self.atoms.append(
                AtomRecord(
                    res_id=safe_res_id,
                    res_name=gro_res_name,
                    atom_name=bead_name[:5],
                    atom_id=safe_atom_id,
                    x=float(coord[0]),
                    y=float(coord[1]),
                    z=float(coord[2]),
                )
            )

    def _get_or_build_lipid_template(self, lipid_name: str):
        """
        从脂质模板复用表中拿模板；如果还没有，就即时构建并保存。
        不负责“计算怎么摆分子”，把“已经摆好的一个分子”登记到账本里。

        这里保存的是“该脂质的一份局部标准模板”，
        不是已经摆进囊泡里的脂质实例。
        后续每次落位，都是在这份标准模板基础上做刚体旋转和平移。
        """
        if lipid_name not in self._lipid_templates:
            self._lipid_templates[lipid_name] = build_lipid_3d(LIPID_LIBRARY[lipid_name])
        return self._lipid_templates[lipid_name]

    @staticmethod
    def _normalize_composition(composition: Dict[str, float]) -> Dict[str, float]:
        """
        把配方权重归一化到总和为 1。

        builder 对外并不强制要求传入精确和为 1 的字典；
        只要比例关系合理，都会自动归一。
        """
        total = float(sum(composition.values()))
        if not np.isfinite(total) or total <= 0.0:
            raise ValueError("composition must have a positive finite total weight")
        return {name: float(value) / total for name, value in composition.items()}

    def _build_exact_lipid_sequence(
        self,
        composition: Dict[str, float],
        total_count: int,
    ) -> List[str]:
        """
        根据比例配方构造“精确整数总数”的脂质名序列。

        若“每次按概率抽一种脂质”，则在中小体系中大，会导致比例不稳定。
        当前采用“最大余数法”：
        1. 先对每种脂质取 floor算出精确整数分子；
        2. 再把剩余名额按余数从大到小补齐；
        3. 最后把完整序列打乱。
        """
        weights = self._normalize_composition(composition)
        raw_counts = {name: weights[name] * total_count for name in weights}
        counts = {name: int(np.floor(raw_counts[name])) for name in weights}
        remaining = total_count - sum(counts.values())

        remainders = sorted(
            weights.keys(),
            key=lambda name: (raw_counts[name] - counts[name], weights[name], name),
            reverse=True,
        )
        for name in remainders[:remaining]:
            counts[name] += 1

        sequence: List[str] = []
        for name in weights:
            sequence.extend([name] * counts[name])

        if len(sequence) != total_count:
            raise RuntimeError("failed to build an exact lipid composition sequence")

        shuffled = np.random.permutation(np.asarray(sequence, dtype=object))
        return shuffled.tolist()

    def _is_candidate_center_valid(self, candidate: np.ndarray, radius: float) -> bool:
        """
        蛋白放置时的第一层防撞。
        圆盘占位近似”代替真实形状碰撞，做蛋白中心级别的局部快速防撞。

        此处不是beads级，因为在蛋白逐个放置过程中，中心级阈值判断更轻更直接。
        给脂质挖洞用的是后面基于 bead 绝对坐标的 KD-tree。
        """
        if not self._protein_centers:
            return True

        centers = np.vstack(self._protein_centers)
        radii = np.asarray(self._protein_radii, dtype=np.float64)
        distances = np.linalg.norm(centers - candidate, axis=1)
        thresholds = self.PROTEIN_SPACING_FACTOR * (radii + radius)
        return bool(np.all(distances > thresholds))

    def place_proteins_clustered(self, cluster_assignments: List[List[Protein]]) -> None:
        """
        按岛屿显式输入放置蛋白簇集。

        `cluster_assignments` 的结构为：
        - 外层 list：岛屿列表
        - 内层 list：每个岛屿里的 Protein 模板列表

        当前策略：
        1. 先用 Fibonacci sphere 给每个岛生成一个均匀球面种子；
        2. 岛内每个蛋白围绕该种子做局部角扰动；
        3. 通过中心级阈值做局部防撞；
        4. 成功后旋转模板到球面法向并写入总账本；
        5. 最后统一构建全局 bead KD-tree。
        """
        if not cluster_assignments:
            raise ValueError("cluster_assignments must contain at least one cluster")

        seeds = generate_fibonacci_sphere(self.R_mid, len(cluster_assignments))
        for cluster_index, proteins in enumerate(cluster_assignments):
            anchor_vector = seeds[cluster_index]
            for protein in proteins:
                prepared = protein.prepared_for_placement()
                prot_radius = prepared.get_projected_radius()

                candidate_point = None
                for _ in range(self.PROTEIN_PLACEMENT_MAX_TRIES):
                    candidate = apply_local_axis_angle_perturbation(
                        anchor_vector,
                        self.PROTEIN_CLUSTER_MAX_ANGLE,
                    )
                    if self._is_candidate_center_valid(candidate, prot_radius):
                        candidate_point = candidate
                        break

                if candidate_point is None:
                    raise RuntimeError(
                        f"failed to place protein {protein.name} in cluster {cluster_index} "
                        f"after {self.PROTEIN_PLACEMENT_MAX_TRIES} attempts"
                    )

                aligned_coords = align_template_to_sphere(
                    template_coords=prepared.coords,
                    intrinsic_axis=self.PROTEIN_ALIGNMENT_AXIS,
                    target_position=candidate_point,
                    align_to_outward_normal=True,
                )

                self._add_molecule_to_ledger(prepared.name, prepared.bead_types, aligned_coords)
                self.detector.add_protein(aligned_coords, prepared.category)
                self._protein_centers.append(candidate_point)
                self._protein_radii.append(prot_radius)

        # 所有蛋白绝对坐标都入账后，构建全局 KD-tree，
        # 供后续双层脂质在铺膜阶段执行“挖洞跳过”。
        self.detector.build_trees()

    def _fill_lipid_leaflet(
        self,
        R_target: float,
        composition: Dict[str, float],
        is_inner: bool,
    ) -> None:
        """
        在给定半径的球面上铺一层脂质。
        只做“脂质-蛋白”碰撞跳过，不做“脂质-脂质”显式防撞，也不做后续局部重排。
        即默认 Fibonacci 球面点本身足够均匀，配合后续 MD 弛豫可以消化这些近似。

        逻辑顺序固定：
        1. 根据球面积 4πR² / lipid_area估算该叶总脂质数；
        2. 按配方比例构造“精确整数总数”的脂质名序列；
        3. 生成过采样候选点；
        4. 对每个点先做蛋白碰撞检查（头基点是否落进蛋白 bead 的排斥半径内）；
        5. 只有真正通过碰撞检查的点，才会消费序列里的下一个脂质名；
        6. 通过后再把脂质模板对齐并入账。

        因此，“当前位置最终放什么脂质”并不是由坐标本身直接决定，
        而是由三部分共同决定：
        - 该叶的 composition 配方
        - `_build_exact_lipid_sequence(...)` 生成的随机打乱序列
        - 当前点是否被蛋白挖洞逻辑跳过
        """
        total_count = int(round((4.0 * np.pi * (R_target**2)) / self.lipid_area))
        if total_count <= 0:
            raise ValueError("leaflet lipid count computed as zero or negative")

        lipid_sequence = self._build_exact_lipid_sequence(composition, total_count)
        num_points = int(np.ceil(total_count * self.LIPID_POINT_OVERSAMPLE))
        candidate_points = generate_fibonacci_sphere(R_target, num_points)
        # Fibonacci sphere 的返回顺序沿 z 轴近似单调，从一极扫到另一极。
        # 如果这里直接按原顺序消费，并在放满 total_count 后提前 break，
        # 就会把“过采样额外多出来的那一段”固定压到某个极区，形成假性缺口。
        # 因此必须先打乱候选点，再做蛋白挖洞与逐点放置。
        candidate_points = np.random.permutation(candidate_points)

        placed_count = 0
        for point in candidate_points:
            if placed_count >= total_count:
                break

            # 这里的碰撞查询直接面向蛋白 bead KD-tree。
            # 命中则说明这个头部点落在蛋白排斥壳内，应直接跳过。
            if self.detector.check_collision(
                point,
                category="surface_transmembrane",
                radius=self.lipid_exclusion_radius,
            ):
                continue

            # 只有保留下来的点才会消费一个脂质名；
            # 被蛋白排斥跳过的候选点不会改变最终配方总数。
            lipid_name = lipid_sequence[placed_count]
            lipid = self._get_or_build_lipid_template(lipid_name)
            aligned_coords = align_lipid_to_sphere(
                lipid_coords=lipid.coords,
                lipid_up_vector=lipid.vector,
                target_position=point,
                flip_for_inner=is_inner,
            )
            self._add_molecule_to_ledger(lipid_name, lipid.bead_names, aligned_coords)
            placed_count += 1

        if placed_count != total_count:
            raise RuntimeError(
                f"failed to place all lipids for {'inner' if is_inner else 'outer'} leaflet: "
                f"placed {placed_count} / {total_count}"
            )

    def build(self, cluster_assignments: List[List[Protein]]) -> "VesicleBuilder":
        """
        一键执行完整总装流程。

        固定顺序：
        - 放蛋白
        - 铺外叶
        - 铺内叶
        """
        self._reset_state()
        self.place_proteins_clustered(cluster_assignments)
        self._fill_lipid_leaflet(self.R_out, self.comp_out, False)
        self._fill_lipid_leaflet(self.R_in, self.comp_in, True)
        return self

    def _shift_and_box(self) -> tuple[np.ndarray, np.ndarray]:
        """
        为 `.gro` 输出准备正坐标平移量和盒子尺寸。

        `.gro` 理论上可以写负坐标，但为了调试和可视化更直观，
        这里统一把体系平移到正坐标区域，并在最外层留 5 nm padding。
        盒子尺寸按当前实际坐标包围盒算，不是假设一个固定立方盒。

        这个 box 是导出阶段的简化正交盒：
        - 让 `.gro` 当前就保持自洽并方便可视化；
        - 后续正式模拟前，完全可以再用 `gmx editconf` 覆盖成更合适的盒子。
        因此这里建议保留，而不是删除。
        """
        if not self.atoms:
            box = np.array([2.0 * (self.R_out + 5.0)] * 3, dtype=np.float64)
            shift = box / 2.0
            return shift, box

        coords = np.array([[atom.x, atom.y, atom.z] for atom in self.atoms], dtype=np.float64)
        padding = 5.0
        min_coords = np.min(coords, axis=0)
        max_coords = np.max(coords, axis=0)
        shift = -min_coords + padding
        box = (max_coords - min_coords) + 2.0 * padding
        return shift, box

    def write_outputs(
        self,
        gro_name: str | Path | None = None,
        top_name: str | Path | None = None,
    ) -> None:
        """
        把当前账本写成 `vesicle.gro` 与 `topol.top`。

        `.gro` 写法采用固定列宽；
        `.top` 则根据当前实际出现的分子自动输出 include 与 `[ molecules ]`。
        include 顺序为：
        1. `vesicle/data/forcefields/martini_v2.2.itp`
        2. 当前体系实际用到的官方脂质 `.itp`
        3. 当前体系实际用到的蛋白 `.itp`

        若未显式传入路径，则默认输出到：
        - `vesicle/outputs/basic_vesicle/vesicle.gro`
        - `vesicle/outputs/basic_vesicle/topol.top`
        """
        if gro_name is None:
            gro_path = self.DEFAULT_OUTPUT_DIR / self.DEFAULT_GRO_NAME
        else:
            gro_path = Path(gro_name)

        if top_name is None:
            top_path = self.DEFAULT_OUTPUT_DIR / self.DEFAULT_TOP_NAME
        else:
            top_path = Path(top_name)

        gro_path.parent.mkdir(parents=True, exist_ok=True)
        top_path.parent.mkdir(parents=True, exist_ok=True)

        shift, box = self._shift_and_box()

        with gro_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write("VesicleBuilder output\n")
            handle.write(f"{len(self.atoms):5d}\n")
            for atom in self.atoms:
                x, y, z = np.array([atom.x, atom.y, atom.z], dtype=np.float64) + shift
                handle.write(
                    f"{atom.res_id:5d}{atom.res_name:<5}{atom.atom_name:>5}{atom.atom_id:5d}"
                    f"{x:8.3f}{y:8.3f}{z:8.3f}\n"
                )
            handle.write(f"{box[0]:10.5f}{box[1]:10.5f}{box[2]:10.5f}\n")

        forcefield_dir = self.FORCEFIELD_DIR
        if not forcefield_dir.exists():
            raise FileNotFoundError(f"forcefield directory does not exist: {forcefield_dir}")

        def _forcefield_include_line(filename: str) -> str:
            include_path = forcefield_dir / filename
            if not include_path.exists():
                raise FileNotFoundError(f"required forcefield file does not exist: {include_path}")
            rel_path = os.path.relpath(include_path, start=top_path.parent)
            return f'#include "{rel_path.replace(os.sep, "/")}"\n'

        include_lines = [_forcefield_include_line(self.FORCEFIELD_INCLUDE)]
        for lipid_name in self.MOLECULE_WRITE_ORDER:
            if lipid_name not in self.LIPID_ITP_MAP:
                continue
            if self.molecule_counts.get(lipid_name, 0) == 0:
                continue
            include_lines.append(_forcefield_include_line(self.LIPID_ITP_MAP[lipid_name]))
        for protein_name, itp_name in self.PROTEIN_ITP_MAP.items():
            molecule_name = self.PROTEIN_MOLECULE_MAP[protein_name]
            if self.molecule_counts.get(molecule_name, 0) == 0:
                continue
            include_lines.append(_forcefield_include_line(itp_name))

        with top_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.writelines(include_lines)
            handle.write("\n[ system ]\n")
            handle.write("VesicleBuilder system\n\n")
            handle.write("[ molecules ]\n")
            for name in self.MOLECULE_WRITE_ORDER:
                count = self.molecule_counts.get(name, 0)
                if count > 0:
                    handle.write(f"{name:<10s} {count}\n")


__all__ = ["AtomRecord", "VesicleBuilder"]
