"""
vesicle.models.protein
======================

这个文件定义囊泡建模阶段使用的蛋白模板对象 `Protein`。

这里的 Protein 不是“生物信息学意义上的全功能蛋白类”，
而是一个专门服务于 coarse-grained 囊泡拼装的几何模板：

- 负责从单分子 CG `.gro` 文件读取 bead 坐标；
- 负责缓存放置时最常用的几何属性；
- 负责把模板整理到适合球面放置的局部坐标系。

上层 builder 只关心“蛋白已经准备好，可以被放到某个球面点上”。
因此这里尽量把模板预处理封装干净。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Union

import numpy as np

# 这里保留多个类别，是为了让后续模型有扩展余地。
# 当前外泌体主链路实际只会稳定使用 `surface_transmembrane`。
PROTEIN_CATEGORIES = {
    "surface_transmembrane",
    "inner_associated",
    "luminal_soluble",
}


@dataclass
class Protein:
    """
    单个蛋白模板对象。

    核心字段
    --------
    name
        蛋白名，例如 `CD9`、`CD63`、`CD81`。
    coords
        shape=(N,3) 的 bead 坐标，单位为 nm。
    radius
        该蛋白在膜平面上的投影占位半径，用于局部防撞。
    tm_center
        近似跨膜中心的 z 坐标，用于把模板平到膜中面。

    设计原则
    --------
    这里不做复杂的蛋白拓扑推断，不尝试自动识别胞内外结构域。
    当前只做“对 builder 真正有用”的几何预处理。
    """

    name: str  # 蛋白名称，最基本的身份标识
    coords: np.ndarray = field(default_factory=lambda: np.zeros((0, 3), dtype=np.float64))  # bead 级局部坐标
    radius: Optional[float] = None  # 膜平面投影占位半径，用于防撞
    tm_center: Optional[float] = None  # 跨膜中心的近似 z 坐标

    category: str = "surface_transmembrane"  # 蛋白类别，如表面跨膜蛋白
    pdb_file: Optional[Path] = None  # 原始或参考 PDB 路径
    description: Optional[str] = None  # 文字说明，不参与几何计算
    net_charge: float = 0.0  # 近似净电荷
    is_glycosylated: bool = False  # 是否糖基化
    tm_helices: int = 0  # 跨膜螺旋数量

    cg_gro_file: Optional[Path] = None  # 粗粒化 .gro 模板路径
    cg_top_file: Optional[Path] = None  # 粗粒化 topology 路径
    bead_types: List[str] = field(default_factory=list)  # bead 名称/类型列表
    bounding_box: Optional[Tuple[np.ndarray, np.ndarray]] = None  # 局部包围盒

    def __post_init__(self) -> None:
        """统一做输入合法性检查，并在需要时自动加载 `.gro`。"""
        if self.category not in PROTEIN_CATEGORIES:
            raise ValueError(
                f"Invalid protein category: {self.category}. Valid: {PROTEIN_CATEGORIES}"
            )

        coords = np.asarray(self.coords, dtype=np.float64)
        if coords.ndim != 2 or coords.shape[1] != 3:
            raise ValueError(f"coords must have shape (N, 3), got {coords.shape}")
        if not np.all(np.isfinite(coords)):
            raise ValueError("coords contains NaN or Inf")
        self.coords = coords

        # 如果用户只给了 `.gro` 路径，没有直接给 bead 坐标，
        # 就在对象构造时自动把模板坐标载入进来。
        if self.cg_gro_file is not None and (
            self.coords.size == 0 or len(self.bead_types) == 0
        ):
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
        从单分子 CG `.gro` 创建模板对象。

        这里不立刻要求用户手动传 bead 坐标，
        而是把 `.gro` 路径放进 `cg_gro_file`，由 `__post_init__()` 自动完成载入。
        """
        return cls(
            name=name,
            coords=np.zeros((0, 3), dtype=np.float64),
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
        """
        用固定列宽解析 CG `.gro` 文件。

        `.gro` 不是按空格分隔的自由文本格式，
        所以这里必须按列切片，而不能偷懒直接 `split()`。
        """
        if self.cg_gro_file is None:
            raise ValueError("cg_gro_file is None")

        gro_path = Path(self.cg_gro_file)
        if not gro_path.exists():
            raise FileNotFoundError(f"Coarse-grained file does not exist: {gro_path}")

        lines = gro_path.read_text(encoding="utf-8").splitlines()
        if len(lines) < 3:
            raise ValueError(f"Invalid .gro file: {gro_path}")

        try:
            natoms = int(lines[1].strip())
        except ValueError as exc:
            raise ValueError(f"Invalid atom count in .gro file: {gro_path}") from exc

        atom_lines = lines[2 : 2 + natoms]
        if len(atom_lines) != natoms:
            raise ValueError(
                f"Invalid atom count in .gro: expected {natoms}, got {len(atom_lines)}"
            )

        coords: List[List[float]] = []
        bead_types: List[str] = []
        for line_index, line in enumerate(atom_lines, start=1):
            if len(line) < 44:
                raise ValueError(
                    f"Atom line {line_index} is too short for fixed-width parsing: {gro_path}"
                )
            bead_types.append(line[10:15].strip())
            coords.append(
                [
                    float(line[20:28].strip()),
                    float(line[28:36].strip()),
                    float(line[36:44].strip()),
                ]
            )

        self.coords = np.asarray(coords, dtype=np.float64)
        self.bead_types = bead_types

    def _compute_physical_properties(self) -> None:
        """
        计算 builder 最依赖的三个几何缓存：
        - `bounding_box`
        - `radius`
        - `tm_center`

        这里的 `radius` 不是范德华半径，而是“膜平面占位半径”。
        """
        if self.coords.size == 0:
            self.radius = 0.0 if self.radius is None else float(self.radius)
            self.tm_center = 0.0 if self.tm_center is None else float(self.tm_center)
            self.bounding_box = (np.zeros(3), np.zeros(3))
            return

        min_coords = np.min(self.coords, axis=0)
        max_coords = np.max(self.coords, axis=0)
        self.bounding_box = (min_coords, max_coords)

        # 这里先取 xy 平面的几何中心，再看最远 bead 到该中心的距离，
        # 最后乘一个 1.2 的安全系数，作为局部防撞用的占位半径。
        if self.radius is None:
            xy = self.coords[:, :2]
            center_xy = np.mean(xy, axis=0)
            distances = np.linalg.norm(xy - center_xy, axis=1)
            self.radius = float(np.max(distances) * 1.2)

        # 当前把跨膜中心简化成 z 坐标均值。
        # 对这批四跨膜蛋白来说，这个近似足够支撑囊泡模板放置。
        if self.tm_center is None:
            self.tm_center = float(np.mean(self.coords[:, 2]))

    def _clone_with_coords(self, coords: np.ndarray, *, tm_center: Optional[float]) -> "Protein":
        """
        生成一个保留元数据的新模板副本。

        这样所有“平移后得到的新模板”都走同一条复制路径，
        避免在多个函数里重复组装 `Protein(...)`。
        """
        return Protein(
            name=self.name,
            coords=np.asarray(coords, dtype=np.float64),
            radius=self.radius,
            tm_center=self.tm_center if tm_center is None else float(tm_center),
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

    def copy_template(self) -> "Protein":
        """
        复制当前模板。

        这个方法主要给上层 builder 用：
        当一个体系里需要很多个相同蛋白时，没有必要重复从磁盘读取同一份 `.gro`。
        直接复制已经解析好的模板更快，也更干净。
        """
        return self._clone_with_coords(self.coords.copy(), tm_center=self.tm_center)

    def get_projected_radius(self) -> float:
        """返回蛋白在膜平面上的占位半径。"""
        return float(self.radius if self.radius is not None else 0.0)

    def get_tm_center(self) -> float:
        """返回当前模板的跨膜中心 z 坐标。"""
        return float(self.tm_center if self.tm_center is not None else 0.0)

    def shifted_to_tm_center(self, target_z: float = 0.0) -> "Protein":
        """
        只沿 z 方向平移模板，使跨膜中心对齐到 `target_z`。

        这个函数故意不做旋转，也不碰 xy，
        因为它的职责只是“把模板平到膜中面”。
        """
        shifted_coords = self.coords.copy()
        if shifted_coords.size:
            shifted_coords[:, 2] += float(target_z) - self.get_tm_center()
        return self._clone_with_coords(shifted_coords, tm_center=target_z)

    def prepared_for_placement(self) -> "Protein":
        """
        把蛋白模板整理到 builder 最喜欢的局部坐标系。

        处理步骤：
        1. 先把跨膜中心平到 `z = 0`；
        2. 再把 xy 平面几何中心移到 `(0, 0)`。

        这样整理后的模板就可以被几何模块当成“局部刚体”，
        直接旋转到球面目标点，而不会额外携带旧模板的平移偏置。
        """
        centered = self.shifted_to_tm_center(0.0)
        if centered.coords.size == 0:
            return centered

        coords = centered.coords.copy()
        center_xy = np.mean(coords[:, :2], axis=0)
        coords[:, 0] -= center_xy[0]
        coords[:, 1] -= center_xy[1]
        return centered._clone_with_coords(coords, tm_center=0.0)


__all__ = ["PROTEIN_CATEGORIES", "Protein"]
