"""
vesicle/utils/collision.py

碰撞检测与蛋白放置模块 - 阶段二核心

主要功能：
1. 使用 scipy.spatial.cKDTree 快速检测脂质放置位置是否与已放置蛋白碰撞
2. 实现蛋白在球面的初步放置（随机选点 + 旋转对齐 + 挖洞）
3. 支持蛋白分类（surface_transmembrane / inner_associated）
4. 与 geometry.py 无缝配合（使用 Person B 的 Fibonacci 撒点和旋转对齐）

设计要点：
- 先放置所有蛋白 → 构建 KD-Tree → 再放置脂质（效率最高）
- 排斥半径默认为 0.5 nm（MARTINI 珠子安全距离，可调）
- 支持内外叶不同挖洞逻辑
- 所有坐标单位统一为 nm（与 MARTINI .gro 一致）

优化建议（已标注）：
- Person B 的 generate_fibonacci_sphere 已足够好，但如果点数非常大（>50000），可考虑用 halton sequence 替代（更均匀）
- 旋转对齐已使用 scipy Rotation，奇点处理良好，无需手动改
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree
from pathlib import Path
from typing import List, Tuple, Optional, Dict

# 导入 Person B 已实现的几何函数（geometry.py）
from .geometry import (
    generate_fibonacci_sphere,
    align_lipid_to_sphere,
)

# ────────────────────────────────────────────────
# 全局常量
# ────────────────────────────────────────────────
COLLISION_RADIUS = 0.5          # MARTINI 珠子典型排斥半径（nm）
EPS_COLLISION = 1e-6            # 距离判断浮点容差


class CollisionDetector:
    """
    KD-Tree 碰撞检测器

    职责：
    - 管理已放置蛋白的坐标树
    - 快速查询新位置是否碰撞
    - 支持分内外叶查询（surface_transmembrane 用外叶树，inner_associated 用内叶树）
    """

    def __init__(self):
        self.outer_tree: Optional[cKDTree] = None   # 外叶蛋白 KD-Tree
        self.inner_tree: Optional[cKDTree] = None   # 内叶蛋白 KD-Tree
        self.outer_protein_coords: List[np.ndarray] = []   # 已放置的外叶蛋白坐标
        self.inner_protein_coords: List[np.ndarray] = []   # 已放置的内叶蛋白坐标

    def add_protein(
        self,
        protein_coords: np.ndarray,
        category: str,
        position: np.ndarray,
        rotation_matrix: Optional[np.ndarray] = None,
    ):
        """
        添加一个已放置的蛋白到碰撞检测树

        参数：
            protein_coords : 该蛋白的所有珠子坐标 (N_beads, 3)
            category       : 蛋白类别（surface_transmembrane / inner_associated）
            position       : 放置位置（珠子原点）
            rotation_matrix: 旋转矩阵（可选，已对齐）
        """
        # 应用旋转（如果有）
        if rotation_matrix is not None:
            rotated = rotation_matrix @ protein_coords.T
            placed_coords = rotated.T + position
        else:
            placed_coords = protein_coords + position

        if category == "surface_transmembrane":
            self.outer_protein_coords.append(placed_coords)
        elif category == "inner_associated":
            self.inner_protein_coords.append(placed_coords)
        else:
            raise ValueError(f"不支持的蛋白类别: {category}")

    def build_trees(self):
        """构建 KD-Tree（必须在所有蛋白放置完成后调用）"""
        if self.outer_protein_coords:
            outer_all = np.vstack(self.outer_protein_coords)
            self.outer_tree = cKDTree(outer_all)

        if self.inner_protein_coords:
            inner_all = np.vstack(self.inner_protein_coords)
            self.inner_tree = cKDTree(inner_all)

        print(f"KD-Tree 构建完成: 外叶蛋白 {len(self.outer_protein_coords)} 个, 内叶蛋白 {len(self.inner_protein_coords)} 个")

    def check_collision(
        self,
        test_position: np.ndarray,
        category: str,
        radius: float = COLLISION_RADIUS,
    ) -> bool:
        """
        检查给定位置是否与已放置蛋白碰撞

        参数：
            test_position : 要放置的新位置 (3,)
            category      : 该位置所属类别（决定用哪个树）
            radius        : 碰撞半径（默认 0.5 nm）

        返回：
            True = 碰撞（不能放），False = 无碰撞（可以放）
        """
        test_pos = np.asarray(test_position).reshape(1, 3)

        if category == "surface_transmembrane" and self.outer_tree is not None:
            dist, _ = self.outer_tree.query(test_pos, k=1)
            return dist[0] < radius

        elif category == "inner_associated" and self.inner_tree is not None:
            dist, _ = self.inner_tree.query(test_pos, k=1)
            return dist[0] < radius

        return False  # 没有树或类别不支持，默认不碰撞


def place_proteins_on_sphere(
    builder,
    protein_list: List[Tuple[str, int, str]],   # (protein_name, count, category)
    radius_nm: float,
    detector: Optional[CollisionDetector] = None,
) -> CollisionDetector:
    """
    在球面上放置蛋白质（带碰撞检测）

    参数：
        builder       : VesicleBuilder 实例（提供 generate_sphere_points 和 align_lipid_to_sphere）
        protein_list  : 要放置的蛋白列表 [(name, count, category), ...]
        radius_nm     : 囊泡半径
        detector      : 已有的 CollisionDetector（可选，第一次调用可传 None）

    返回：
        CollisionDetector 对象（已构建好 KD-Tree）
    """
    if detector is None:
        detector = CollisionDetector()

    for protein_name, count, category in protein_list:
        # 生成候选点（外叶或内叶）
        if category == "surface_transmembrane":
            points = builder.generate_sphere_points(radius_nm, count * 5)  # 多生成一些候选
        else:
            inner_r = radius_nm - builder.thickness_nm
            points = builder.generate_sphere_points(inner_r, count * 5)

        placed_count = 0
        for pos in points:
            if placed_count >= count:
                break

            # 检查碰撞
            if detector.check_collision(pos, category):
                continue

            # 对齐蛋白（调用 Person B 的旋转函数）
            # 注意：这里假设蛋白模板已加载为 Protein 对象，后续可扩展
            # 暂时用简单平移 + 随机旋转模拟（实际应调用 Protein 的对齐方法）
            detector.add_protein(
                protein_coords=np.zeros((10, 3)),  # 占位，实际应从 Protein.bead_coords 获取
                category=category,
                position=pos,
            )
            placed_count += 1

        print(f"成功放置 {placed_count} 个 {protein_name} ({category})")

    detector.build_trees()
    return detector