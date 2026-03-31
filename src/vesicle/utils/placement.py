"""
vesicle.utils.placement
=======================

这个模块集中承载囊泡组装阶段最核心的一组“空间放置原语”（spatial
placement primitives）。

之所以把原来的 `geometry.py` 和 `collision.py` 合并到这里，是因为这两类能力
在当前项目里并不是两条独立工作流，而是同一件事的两个侧面：

1. 先在球面上生成候选点；
2. 再把蛋白或脂质模板旋转并平移到目标位置；
3. 最后用空间排斥查询判断某个候选点是否还能继续使用。

也就是说，builder 真正依赖的不是“纯几何模块”和“纯碰撞模块”各自分离，
而是一整套围绕“如何在球面上放置分子，并判断空间冲突”的底层能力。

本模块负责：

- 球面候选点生成
- 刚体模板到球面的对齐
- 局部角扰动
- 基于 KD-tree 的碰撞检测
- 向量/坐标输入校验

本模块明确不负责：

- 生物学分配策略
- 蛋白岛屿组成决策
- 脂质配方决策
- workflow 编排
- 文件写出

边界可以概括为：
builder 决定“放什么、放多少、按什么顺序放”；
本模块只决定“如何在空间里放，以及如何判断会不会撞上”。
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

# ---------------------------------------------------------------------------
# Numerical constants
# ---------------------------------------------------------------------------

# 所有向量在归一化前都要经过这个阈值检查。
# 只要模长小于它，就认为该向量在数值上已经退化，不再适合继续做方向计算。
EPS_NORM = 1e-12

# bead 级别的默认蛋白排斥查询半径。
# builder 可以根据具体阶段覆盖这个值，例如在脂质挖洞时使用更大的排斥半径。
COLLISION_RADIUS = 0.22


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _as_vec3(name: str, value: np.ndarray) -> np.ndarray:
    """
    把输入强制检查为 shape=(3,) 的有限三维向量。

    这个函数被几何计算和碰撞查询共同依赖，原因是这两个子问题都有一个共同前提：
    输入必须真的是三维空间里的一个向量，而不是标量、二维数组或混有 NaN/Inf 的脏数据。
    一旦这里放松检查，后续的旋转、归一化、KD-tree 查询都可能产生非常隐蔽的错误。
    """
    arr = np.asarray(value, dtype=np.float64)
    if arr.shape != (3,):
        raise ValueError(f"{name} must have shape (3,), got {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains NaN or Inf: {arr}")
    return arr


def _as_coords(name: str, coords: np.ndarray) -> np.ndarray:
    """
    把输入强制检查为 shape=(N, 3) 的有限坐标矩阵。

    这既是刚体模板对齐的统一入口，也是碰撞检测器注册蛋白 bead 坐标时的统一入口。
    换句话说，只要一个对象要被当成“空间中的一批点”来处理，就先经过这里。
    """
    arr = np.asarray(coords, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(f"{name} must have shape (N, 3), got {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains NaN or Inf")
    return arr


def _normalize(name: str, vec: np.ndarray, eps: float = EPS_NORM) -> np.ndarray:
    """
    对向量做安全归一化。

    这里集中管理“零向量/近零向量”的失败分支，而不是在每个调用点散落着写
    `vec / np.linalg.norm(vec)`，这样可以让数值稳定性规则保持一致。
    """
    norm = np.linalg.norm(vec)
    if not np.isfinite(norm) or norm < eps:
        raise ValueError(f"{name} is too small or invalid for normalization (norm={norm})")
    return vec / norm


# ---------------------------------------------------------------------------
# Placement geometry
# ---------------------------------------------------------------------------

def generate_fibonacci_sphere(
    radius: float,
    num_points: int,
    center: np.ndarray = np.array([0.0, 0.0, 0.0]),
) -> np.ndarray:
    """
    用 Fibonacci sphere 算法在球面上生成近似均匀分布的候选点。

    这是蛋白岛种子和脂质铺设候选点的共同底层入口。
    它只保证“几何上的近似均匀分布”，并不试图表达任何生物学分布偏好。

    参数
    ----
    radius
        球半径，单位统一为 nm。
    num_points
        需要生成的点数。
    center
        球心坐标。

    返回
    ----
    shape=(num_points, 3) 的点云坐标。
    """
    radius = float(radius)
    if not np.isfinite(radius) or radius <= 0.0:
        raise ValueError(f"radius must be a positive finite scalar, got {radius}")

    num_points = int(num_points)
    if num_points <= 0:
        raise ValueError(f"num_points must be a positive integer, got {num_points}")

    center_vec = _as_vec3("center", center)

    indices = np.arange(num_points, dtype=np.float64)
    z = 1.0 - (2.0 * (indices + 0.5)) / num_points
    theta = np.pi * (3.0 - np.sqrt(5.0)) * indices
    r_xy = np.sqrt(np.maximum(1.0 - z * z, 0.0))

    points = radius * np.column_stack((r_xy * np.cos(theta), r_xy * np.sin(theta), z))
    return points + center_vec


def align_template_to_sphere(
    template_coords: np.ndarray,
    intrinsic_axis: np.ndarray,
    target_position: np.ndarray,
    sphere_center: np.ndarray = np.array([0.0, 0.0, 0.0]),
    *,
    align_to_outward_normal: bool,
) -> np.ndarray:
    """
    把一个局部模板刚体旋转并平移到球面目标点。

    这是放置层最通用的核心函数。它不关心输入模板是蛋白还是脂质，只关心两点：

    1. `template_coords` 是否已经在局部坐标系下整理好；
    2. `intrinsic_axis` 是否能够代表该模板的本征朝向。

    `align_to_outward_normal` 的语义：

    - True：本征轴对齐到球面外法向
    - False：本征轴对齐到球面内法向，也就是朝球心

    这里使用 `Rotation.align_vectors(...)`，而不是手写轴角分支，
    是为了尽量把近平行与近反平行情形交给成熟实现处理。
    """
    coords = _as_coords("template_coords", template_coords)
    axis = _normalize("intrinsic_axis", _as_vec3("intrinsic_axis", intrinsic_axis))
    target = _as_vec3("target_position", target_position)
    center = _as_vec3("sphere_center", sphere_center)

    radial = target - center
    normal = _normalize("radial_vector", radial)
    target_axis = normal if align_to_outward_normal else -normal

    rotation, _ = Rotation.align_vectors(
        a=target_axis.reshape(1, -1),
        b=axis.reshape(1, -1),
    )
    return rotation.apply(coords) + target


def align_lipid_to_sphere(
    lipid_coords: np.ndarray,
    lipid_up_vector: np.ndarray,
    target_position: np.ndarray,
    sphere_center: np.ndarray = np.array([0.0, 0.0, 0.0]),
    flip_for_inner: bool = False,
) -> np.ndarray:
    """
    脂质专用包装函数。

    对脂质来说，“内叶/外叶”的业务语义比“是否对齐到外法向”更直接：

    - 外叶：尾部朝球心
    - 内叶：尾部背离球心

    这里约定 `lipid_up_vector` 为“头部 -> 尾部”的方向，因此只需要把
    业务语义翻译成 `align_to_outward_normal` 的布尔值即可。
    """
    return align_template_to_sphere(
        template_coords=lipid_coords,
        intrinsic_axis=lipid_up_vector,
        target_position=target_position,
        sphere_center=sphere_center,
        align_to_outward_normal=flip_for_inner,
    )


def apply_local_axis_angle_perturbation(
    anchor_vector: np.ndarray,
    max_angle_rad: float = 0.26,
) -> np.ndarray:
    """
    对球面锚点做“随机轴 + 均匀角度”的局部角扰动。

    这是当前 TEM 岛屿内部局部聚簇的专用空间扰动算子。
    它的目标不是“球冠均匀采样”，而是故意保留中心更密、边缘更疏的局部分布感。

    该函数满足两个硬约束：

    1. 扰动前后半径保持不变；
    2. 扰动角不超过 `max_angle_rad`。
    """
    vec = _as_vec3("anchor_vector", anchor_vector)

    max_angle = float(max_angle_rad)
    if not np.isfinite(max_angle) or max_angle < 0.0:
        raise ValueError(
            f"max_angle_rad must be a finite non-negative scalar, got {max_angle_rad}"
        )

    radius = np.linalg.norm(vec)
    if radius < EPS_NORM:
        # 零向量没有可定义方向，此时直接返回自身，
        # 避免在极端退化输入下为了“强行旋转”反而制造数值垃圾。
        return vec

    v_norm = vec / radius

    # 通过与随机向量叉乘构造切向旋转轴。
    # 只要随机向量不与当前方向平行，得到的轴就自然位于局部切平面中。
    random_vec = np.random.randn(3)
    axis = np.cross(v_norm, random_vec)

    # 极小概率下 random_vec 与 v_norm 近乎平行，导致叉积接近零。
    # 这里显式兜底，避免扰动步骤在极端情形下退化。
    if np.linalg.norm(axis) < EPS_NORM:
        fallback = (
            np.array([1.0, 0.0, 0.0], dtype=np.float64)
            if abs(v_norm[0]) < 0.9
            else np.array([0.0, 1.0, 0.0], dtype=np.float64)
        )
        axis = np.cross(v_norm, fallback)

    axis = _normalize("perturbation_axis", axis)
    angle = np.random.uniform(0.0, max_angle)
    rotation = Rotation.from_rotvec(axis * angle)
    return rotation.apply(v_norm) * radius


# ---------------------------------------------------------------------------
# Collision queries
# ---------------------------------------------------------------------------

class CollisionDetector:
    """
    蛋白 bead 空间碰撞检测器。

    这个类仍然保持“纯工具层”定位：它不决定蛋白该放哪里，也不生成候选点，
    只负责把已经落位的蛋白 bead 组织成 KD-tree，然后回答某个测试点是否
    落入排斥半径内。

    当前保留两棵树：

    - `outer_tree`：表面/跨膜蛋白
    - `inner_tree`：内叶相关蛋白

    这让 builder 可以先完成蛋白放置，再统一建树，然后再在铺脂时高频做排斥查询。
    """

    def __init__(self) -> None:
        self.outer_tree: Optional[cKDTree] = None
        self.inner_tree: Optional[cKDTree] = None
        self.outer_protein_coords: List[np.ndarray] = []
        self.inner_protein_coords: List[np.ndarray] = []

    def add_protein(self, protein_coords: np.ndarray, category: str) -> None:
        """
        向检测器注册一个已经完成绝对放置的蛋白。

        注意这里接收的是“绝对坐标”，不是模板局部坐标。
        builder 必须在完成旋转和平移后再调用这里，否则 KD-tree 记录的空间位置
        就不代表最终体系中的真实位置。
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
        在全部蛋白注册完成后构建 KD-tree。

        这里故意不在 `add_protein()` 时即时重建，因为 builder 的正确使用顺序本来就是：

        1. 先把一批蛋白全部放好
        2. 再统一建树
        3. 然后进入大量重复的排斥查询

        这样可以明显减少不必要的重复建树开销。
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
        查询某个测试点是否落入指定类别蛋白的排斥半径内。

        参数
        ----
        test_position
            要检测的候选点，通常是脂质头部的目标位置。
        category
            决定查询哪一棵 KD-tree。
        radius
            查询半径。默认值适合 bead 级别的粗碰撞；
            builder 在脂质挖洞阶段通常会传入更大的排斥半径。
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
            return False

        distance, _ = tree.query(point, k=1)
        return bool(distance[0] < radius)


__all__ = [
    "COLLISION_RADIUS",
    "EPS_NORM",
    "CollisionDetector",
    "align_lipid_to_sphere",
    "align_template_to_sphere",
    "apply_local_axis_angle_perturbation",
    "generate_fibonacci_sphere",
]
