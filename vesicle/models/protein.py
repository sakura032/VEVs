"""
Protein Utilities
蛋白质工具模块 - 用于粗粒度囊泡模拟中的单分子模板处理

本文件主要提供：
- `PROTEIN_CATEGORIES`：蛋白类别约束
- `Protein`：单分子粗粒度蛋白模板数据类
  - 支持从 MARTINI 粗粒度 `.gro` 加载坐标
  - 自动计算几何属性：`radius`（挖洞半径）、`tm_center`（跨膜中心 Z）
  - 提供 `shifted_to_tm_center()` 做 Z 对齐（只做平移）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Union

import numpy as np

PROTEIN_CATEGORIES = {
    "surface_transmembrane",  # 外表面跨膜蛋白（CD9, CD63, integrin 等）
    "inner_associated",  # 内叶/腔内关联蛋白（ALIX, TSG101, Syntenin 等）
    "luminal_soluble",  # 腔内可溶性货物（HSP70, GAPDH 等）
}


@dataclass
class Protein:
    """
    单分子粗粒度蛋白模板（坐标与几何特征）

    Person A 核心字段（必须有）：
    - `name`
    - `coords`: (N, 3) 粗粒度珠子坐标（nm）
    - `radius`: 膜平面投影半径（挖洞用）
    - `tm_center`: 跨膜区中心 Z 坐标（对齐用）

    扩展字段用于工程化加载/记录（当前模拟逻辑不强依赖这些字段）。
    """

    name: str
    coords: np.ndarray = field(
        default_factory=lambda: np.zeros((0, 3), dtype=float)
    )  # (N, 3)
    radius: Optional[float] = None
    tm_center: Optional[float] = None

    # 更完整的元信息（可选）
    category: str = "surface_transmembrane"
    pdb_file: Optional[Path] = None
    description: Optional[str] = None
    net_charge: float = 0.0
    is_glycosylated: bool = False
    tm_helices: int = 0

    # 可选：直接从 cg gro 加载模板
    cg_gro_file: Optional[Path] = None
    cg_top_file: Optional[Path] = None
    bead_types: List[str] = field(default_factory=list)

    # 包围盒（用于碰撞检测/空间查询）
    bounding_box: Optional[Tuple[np.ndarray, np.ndarray]] = None  # (min, max)

    def __post_init__(self) -> None:
        if self.category not in PROTEIN_CATEGORIES:
            raise ValueError(
                f"Invalid protein category: {self.category}. "
                f"Valid: {PROTEIN_CATEGORIES}"
            )

        coords = np.asarray(self.coords, dtype=float)
        if coords.ndim != 2 or coords.shape[1] != 3:
            raise ValueError(f"coords must be shape (N, 3), got {coords.shape}")
        self.coords = coords

        # 若提供 cg_gro_file 且 coords/bead_types 为空，则自动加载
        if self.cg_gro_file is not None and (self.coords.size == 0 or len(self.bead_types) == 0):
            self.load_cg_coords()

        self._compute_physical_properties()

    @classmethod
    def from_gro(
        cls,
        name: str,
        gro_path: Union[str, Path],
        *,
        category: str = "surface_transmembrane",
        radius: Optional[float] = None,
        tm_center: Optional[float] = None,
        pdb_file: Optional[Path] = None,
        description: Optional[str] = None,
        net_charge: float = 0.0,
        is_glycosylated: bool = False,
        tm_helices: int = 0,
    ) -> "Protein":
        """
        从 MARTINI 粗粒度 .gro 构建模板。

        注意：GROMACS `.gro` 的坐标单位是 nm，此实现不做 nm->Å 换算。
        """
        return cls(
            name=name,
            coords=np.zeros((0, 3), dtype=float),  # 由 load_cg_coords() 填充
            radius=radius,
            tm_center=tm_center,
            category=category,
            pdb_file=pdb_file,
            description=description,
            net_charge=net_charge,
            is_glycosylated=is_glycosylated,
            tm_helices=tm_helices,
            cg_gro_file=Path(gro_path),
        )

    def load_cg_coords(self) -> None:
        """从 cg .gro 文件加载粗粒度珠子坐标与 bead_types（从 atomName 读取）。"""
        if self.cg_gro_file is None:
            raise ValueError("cg_gro_file is None")

        gro_path = Path(self.cg_gro_file)
        if not gro_path.exists():
            raise FileNotFoundError(f"粗粒度文件不存在: {gro_path}")

        lines = gro_path.read_text(encoding="utf-8").splitlines()
        if len(lines) < 3:
            raise ValueError(f"Invalid .gro file: {gro_path}")

        natoms = int(lines[1].strip())
        atom_lines = lines[2 : 2 + natoms]
        if len(atom_lines) != natoms:
            raise ValueError(
                f"Invalid atom count in .gro: expected {natoms}, got {len(atom_lines)}"
            )

        coords: List[List[float]] = []
        bead_types: List[str] = []

        for line in atom_lines:
            # .gro 常见列：
            # resSeq(1-5) resName(6-10) atomName(11-15) atomNum(16-20) x(21-28) y(29-36) z(37-44)
            atom_name = line[10:15].strip()
            x = float(line[20:28])
            y = float(line[28:36])
            z = float(line[36:44])
            coords.append([x, y, z])
            bead_types.append(atom_name)

        self.coords = np.asarray(coords, dtype=float)
        self.bead_types = bead_types

    def _compute_physical_properties(self) -> None:
        """计算排斥半径（挖洞）、跨膜中心 Z、以及包围盒。"""
        if self.coords.size == 0:
            if self.radius is None:
                self.radius = 0.0
            if self.tm_center is None:
                self.tm_center = 0.0
            if self.bounding_box is None:
                self.bounding_box = (np.zeros(3), np.zeros(3))
            return

        # 包围盒（min/max）
        min_coords = np.min(self.coords, axis=0)
        max_coords = np.max(self.coords, axis=0)
        self.bounding_box = (min_coords, max_coords)

        # radius：以 XY 几何中心为参考的最大投影距离，再乘 1.2 安全裕度
        if self.radius is None:
            xy = self.coords[:, :2]  # (N, 2)
            center_xy = np.mean(xy, axis=0)  # (2,)
            distances = np.linalg.norm(xy - center_xy, axis=1)  # (N,)
            self.radius = float(np.max(distances) * 1.2)

        # tm_center：Z 坐标几何平均（近似）
        if self.tm_center is None:
            self.tm_center = float(np.mean(self.coords[:, 2]))

    def get_projected_radius(self) -> float:
        """获取膜平面投影半径（挖洞用）。"""
        return float(self.radius if self.radius is not None else 0.0)

    def get_tm_center(self) -> float:
        """获取跨膜区中心 Z 坐标。"""
        return float(self.tm_center if self.tm_center is not None else 0.0)

    def shifted_to_tm_center(self, target_z: float = 0.0) -> "Protein":
        """
        返回一个新 Protein，使模板跨膜中心对齐到 `target_z`。

        仅做 Z 平移（NumPy 广播 + 向量化），不旋转、不变形。
        """
        current_center = self.get_tm_center()
        dz = float(target_z) - current_center

        shifted_coords = self.coords.copy()
        if shifted_coords.size:
            shifted_coords[:, 2] += dz

        # 让新对象重新计算 bounding_box / radius / tm_center（由 __post_init__ 完成）
        return Protein(
            name=self.name,
            coords=shifted_coords,
            radius=self.radius,
            tm_center=float(target_z),
            category=self.category,
            pdb_file=self.pdb_file,
            description=self.description,
            net_charge=self.net_charge,
            is_glycosylated=self.is_glycosylated,
            tm_helices=self.tm_helices,
            cg_gro_file=None,
            cg_top_file=self.cg_top_file,
            bead_types=list(self.bead_types),
            bounding_box=None,
        )
