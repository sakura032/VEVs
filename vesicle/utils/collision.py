"""
vesicle.utils.collision
=======================

这个模块现在刻意保持“纯工具层”定位：

- 不决定蛋白该放哪里；
- 不生成候选点；
- 不处理岛屿分配；
- 只负责把已经落位的蛋白 bead 坐标组织成 KD-tree，
  然后回答“这个点是否离蛋白太近”。

这样 builder 可以专注于组装策略，而 collision 只专注于几何排斥查询。
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np
from scipy.spatial import cKDTree

# 这是 bead 级别的默认蛋白排斥查询半径。
# builder 可以根据具体阶段覆盖这个值，例如脂质挖洞时会使用更大的排斥半径。
COLLISION_RADIUS = 0.22


def _as_coords(name: str, coords: np.ndarray) -> np.ndarray:
    """把输入强制检查为 shape=(N,3) 的有限坐标矩阵。"""
    arr = np.asarray(coords, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(f"{name} must have shape (N, 3), got {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains NaN or Inf")
    return arr


def _as_vec3(name: str, value: np.ndarray) -> np.ndarray:
    """把输入强制检查为 shape=(3,) 的有限向量。"""
    arr = np.asarray(value, dtype=np.float64)
    if arr.shape != (3,):
        raise ValueError(f"{name} must have shape (3,), got {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains NaN or Inf")
    return arr


class CollisionDetector:
    """
    蛋白 bead 碰撞检测器。

    当前只区分两棵树：
    - outer_tree：表面/跨膜蛋白，主要用于囊泡膜面挖洞；
    - inner_tree：内叶相关蛋白，为未来扩展保留。

    对于当前外泌体建模主链路，CD9 / CD81 / CD63 都会走 `surface_transmembrane`。
    """

    def __init__(self) -> None:
        self.outer_tree: Optional[cKDTree] = None
        self.inner_tree: Optional[cKDTree] = None
        self.outer_protein_coords: List[np.ndarray] = []
        self.inner_protein_coords: List[np.ndarray] = []

    def add_protein(self, protein_coords: np.ndarray, category: str) -> None:
        """
        向检测器注册一个已经放好的蛋白。

        注意这里接收的是“绝对坐标”而不是模板局部坐标。
        也就是说，builder 在真正完成旋转和平移之后，才把结果交给 detector。
        """
        coords = _as_coords("protein_coords", protein_coords)
        if category == "surface_transmembrane":
            self.outer_protein_coords.append(coords)
        elif category == "inner_associated":
            self.inner_protein_coords.append(coords)
        else:
            raise ValueError(f"Unsupported protein category: {category}")

    def build_trees(self) -> None:
        """
        在全部蛋白放置完成后构建 KD-tree。

        之所以不在 `add_protein()` 时每次都重建，是因为那样复杂度会被放大很多，
        而 builder 的正确调用顺序本来就是“先放完蛋白，再建树，再铺脂质”。
        """
        self.outer_tree = (
            cKDTree(np.vstack(self.outer_protein_coords))
            if self.outer_protein_coords
            else None
        )
        self.inner_tree = (
            cKDTree(np.vstack(self.inner_protein_coords))
            if self.inner_protein_coords
            else None
        )

    def check_collision(
        self,
        test_position: np.ndarray,
        category: str,
        radius: float = COLLISION_RADIUS,
    ) -> bool:
        """
        查询某个点是否落入指定类别蛋白的排斥半径内。

        参数
        ----
        test_position
            要检测的候选点，通常是脂质头部目标点。
        category
            选择查询哪一棵 KD-tree。
        radius
            查询半径。默认值适合 bead 级别碰撞；
            builder 在脂质挖洞阶段通常会传更大的 `lipid_exclusion_radius`。
        """
        point = _as_vec3("test_position", test_position).reshape(1, 3)
        radius = float(radius)
        if not np.isfinite(radius) or radius < 0.0:
            raise ValueError(f"radius must be finite and non-negative, got {radius}")

        if category == "surface_transmembrane":
            tree = self.outer_tree
        elif category == "inner_associated":
            tree = self.inner_tree
        else:
            raise ValueError(f"Unsupported protein category: {category}")

        if tree is None:
            # 还没建树，或者这类蛋白根本不存在。
            return False

        distance, _ = tree.query(point, k=1)
        return bool(distance[0] < radius)


__all__ = ["COLLISION_RADIUS", "CollisionDetector"]
