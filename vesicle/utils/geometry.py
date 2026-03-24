"""
vesicle.utils.geometry
======================

这个文件负责 `vesicle/` 里最核心的几何原语，目标非常单纯：

1. 在球面上生成尽量均匀的候选点。
2. 把一个“已经在局部坐标系下整理好”的模板刚体旋转到球面目标位置。
3. 对球面锚点做局部角扰动，用来模拟 TEM 岛屿内部的聚簇。

这里故意不掺杂任何“生物学分配策略”或“碰撞树管理”。
那些都交给更上层的 builder 与 collision 模块处理。
"""

from __future__ import annotations

import numpy as np
from scipy.spatial.transform import Rotation

# 所有向量归一化前都要经过这个阈值检查。
# 只要模长小于它，就认为这个向量在数值上已经不稳定，不适合继续做方向计算。
EPS_NORM = 1e-12


def _as_vec3(name: str, value: np.ndarray) -> np.ndarray:
    """
    把输入强制转换成 shape=(3,) 的三维向量。

    这样做的目的不是“形式主义”，而是为了尽早拦截以下问题：
    - 用户误传了标量、二维向量或 (N,3) 坐标矩阵；
    - 输入里混入了 NaN / Inf，导致后面旋转计算直接污染整条坐标链。
    """
    arr = np.asarray(value, dtype=np.float64)
    if arr.shape != (3,):
        raise ValueError(f"{name} must have shape (3,), got {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains NaN or Inf: {arr}")
    return arr


def _as_coords(name: str, coords: np.ndarray) -> np.ndarray:
    """
    把输入强制转换成 shape=(N,3) 的坐标矩阵。

    这个函数是所有“刚体模板”入口的统一守门员。
    只要模板坐标不合法，后续任何旋转、平移都没有意义。
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

    这里统一用一个函数而不是每个地方自己写 `vec / norm`，
    是为了把“零向量/退化向量”的错误分支集中管理，避免后面出现隐蔽的除零。
    """
    norm = np.linalg.norm(vec)
    if not np.isfinite(norm) or norm < eps:
        raise ValueError(f"{name} is too small or invalid for normalization (norm={norm})")
    return vec / norm


def generate_fibonacci_sphere(
    radius: float,
    num_points: int,
    center: np.ndarray = np.array([0.0, 0.0, 0.0]),
) -> np.ndarray:
    """
    用 Fibonacci sphere 算法在球面上生成近似均匀分布的点。

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

    说明
    ----
    这里使用黄金角推进 + 偏移采样的 z 坐标：
    - `z = 1 - 2 * (i + 0.5) / N`
    这样可以避免点恰好堆到南北极，整体更适合后续做蛋白种子或脂质候选点。
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
    把任意“局部模板”刚体旋转并平移到球面目标点。

    这个函数是几何层真正的通用核心。
    它不关心输入模板是脂质还是蛋白，只要求两件事：
    1. `template_coords` 已经在局部坐标系中整理好；
       也就是模板的“放置原点”已经位于局部原点附近。
    2. `intrinsic_axis` 能代表模板在局部坐标系下的本征朝向。

    `align_to_outward_normal` 的含义：
    - True  : 本征轴对齐到球面外法向。
    - False : 本征轴对齐到球面内法向（即朝球心）。
    """
    coords = _as_coords("template_coords", template_coords)
    axis = _normalize("intrinsic_axis", _as_vec3("intrinsic_axis", intrinsic_axis))
    target = _as_vec3("target_position", target_position)
    center = _as_vec3("sphere_center", sphere_center)

    # 球面目标点的径向方向就是局部法向。
    # 这一步是整个球面对齐问题的几何核心。
    radial = target - center
    normal = _normalize("radial_vector", radial)
    target_axis = normal if align_to_outward_normal else -normal

    # Rotation.align_vectors 会自动给出一个最小旋转，
    # 用它比自己手写轴角分支更稳，也更不容易在近平行/近反平行情形下出错。
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

    之所以保留它，是因为脂质的“内叶/外叶”语义比“朝外法向/朝内法向”更直观：
    - 外叶：尾部朝球心
    - 内叶：尾部背离球心

    其中 `lipid_up_vector` 约定为“头部 -> 尾部”的方向。
    因此：
    - 外叶时，本征轴应对齐到“朝球心”的方向；
    - 内叶时，本征轴应对齐到“背离球心”的方向。
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

    这个函数现在是 TEM 岛屿内部聚簇的专用数学算子。
    它做的事情很简单：
    1. 保持原始半径不变；
    2. 找一个与当前锚点方向正交的随机旋转轴；
    3. 在 `[0, max_angle_rad]` 内均匀取一个角度；
    4. 把锚点沿这个局部角度扇区旋转出去。

    为什么不做球冠面积均匀采样？
    因为这里不是为了“均匀撒点”，而是为了故意保留中心更密、边缘更稀的聚簇形态，
    这更接近 TEM 核心高密、边界渐疏的建模目的。
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

    # 先用随机向量叉乘来构造一个切向旋转轴。
    # 只要随机向量不与 v_norm 平行，这个轴就自然位于局部切平面中。
    random_vec = np.random.randn(3)
    axis = np.cross(v_norm, random_vec)

    # 极小概率下，random_vec 会与 v_norm 几乎平行，导致叉积接近零。
    # 这里用一个后备基向量显式兜底，避免死锁。
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


__all__ = [
    "EPS_NORM",
    "generate_fibonacci_sphere",
    "align_template_to_sphere",
    "align_lipid_to_sphere",
    "apply_local_axis_angle_perturbation",
]
