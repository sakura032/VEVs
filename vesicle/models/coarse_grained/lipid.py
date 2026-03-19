from dataclasses import dataclass
from typing import Dict, List

import numpy as np


@dataclass(frozen=True)
class LipidBlueprint:
    """
    脂质“蓝图”对象（Blueprint）。

    设计意图：
    1. 这个类只保存“静态定义信息”，不保存任何 3D 实例状态。
    2. 与旧版单一 Lipid 类相比，蓝图与实体彻底分离，避免字段职责混杂。
    3. 所有字段都使用显式输入，不依赖隐式默认值顺序，从根源上规避 dataclass
       的“默认字段在前、非默认字段在后”的实例化错误。

    字段说明：
    - name: 脂质短名，例如 POPC / CHOL。
    - head_group: 头基类别，供上层统计、分组和后续策略路由使用。
    - tail_type: 尾部化学类型描述，保留给上层分析或文档输出。
    - charge: 分子净电荷（Martini CG 层面的近似值）。
    - area_per_lipid: 单分子占据面积（nm^2），用于囊泡几何估算。
    - preferred_leaflet: 该脂质的偏好膜叶（outer / inner / both）。
    - head_anchors: “头部锚点”珠子名列表，用于定义头部中心。
    - tail_anchors: “尾部锚点”珠子名列表，用于定义尾部中心。
    """

    name: str
    head_group: str
    tail_type: str
    charge: float
    area_per_lipid: float
    preferred_leaflet: str
    head_anchors: List[str]
    tail_anchors: List[str]


@dataclass
class Lipid3D:
    """
    脂质“3D 实体”对象（Runtime 3D Instance）。

    设计意图：
    1. 这个类只承载可参与几何运算的实例数据。
    2. blueprint 保存“它是什么脂质”，coords/vector 保存“它在 3D 中是什么形态”。
    3. 通过分层建模，后续在组装阶段既可以复用蓝图元数据，也能直接消费几何数据。

    约定：
    - coords 坐标，形状为 (N, 3)，且已经被平移到“头部中心在原点”。
    - vector 向量，形状为 (3,)，是“头部中心 -> 尾部中心”的单位向量。
    """

    blueprint: LipidBlueprint
    bead_names: List[str]
    coords: np.ndarray
    vector: np.ndarray

    @property
    def name(self) -> str:
        """便捷访问脂质名称，避免上层频繁写 `lipid3d.blueprint.name`。"""
        return self.blueprint.name

    def __repr__(self) -> str:
        """调试输出：展示脂质名、珠子数和方向向量。"""
        return (
            f"<Lipid3D name={self.name} beads={len(self.bead_names)} "
            f"vector=({self.vector[0]:.3f}, {self.vector[1]:.3f}, {self.vector[2]:.3f})>"
        )


# 统一脂质蓝图库。
# 这里显式写出“头锚点/尾锚点”，不再依赖“去掉头部后对剩余珠子求均值”的旧策略。
LIPID_LIBRARY: Dict[str, LipidBlueprint] = {
    "POPC": LipidBlueprint(
        name="POPC",
        head_group="PC",
        tail_type="palmitoyl-oleoyl",
        charge=0.0,
        area_per_lipid=0.64,
        preferred_leaflet="both",
        head_anchors=["NC3", "PO4"],
        tail_anchors=["C4A", "C4B"],
    ),
    "POPE": LipidBlueprint(
        name="POPE",
        head_group="PE",
        tail_type="palmitoyl-oleoyl",
        charge=0.0,
        area_per_lipid=0.65,
        preferred_leaflet="both",
        head_anchors=["NH3", "PO4"],
        tail_anchors=["C4A", "C4B"],
    ),
    "POPS": LipidBlueprint(
        name="POPS",
        head_group="PS",
        tail_type="palmitoyl-oleoyl",
        charge=-1.0,
        area_per_lipid=0.66,
        preferred_leaflet="inner",
        head_anchors=["CNO", "PO4"],
        tail_anchors=["C4A", "C4B"],
    ),
    "DPSM": LipidBlueprint(
        name="DPSM",
        head_group="SM",
        tail_type="sphingomyelin",
        charge=0.0,
        area_per_lipid=0.55,
        preferred_leaflet="outer",
        head_anchors=["NC3", "PO4"],
        # 对应官方 DPSM-em.gro：A 链末端为 C3A（而非 C4A），B 链末端为 C4B。
        tail_anchors=["C3A", "C4B"],
    ),
    "POP2": LipidBlueprint(
        name="POP2",
        head_group="PIP2",
        tail_type="phosphoinositide",
        charge=-4.0,
        area_per_lipid=0.70,
        preferred_leaflet="inner",
        head_anchors=["P1", "P2", "PO4"],
        tail_anchors=["C4A", "C4B"],
    ),
    "CHOL": LipidBlueprint(
        name="CHOL",
        head_group="sterol",
        tail_type="cholesterol",
        charge=0.0,
        area_per_lipid=0.40,
        preferred_leaflet="both",
        head_anchors=["ROH"],
        tail_anchors=["C2"],
    ),
}


__all__ = ["LipidBlueprint", "Lipid3D", "LIPID_LIBRARY"]
