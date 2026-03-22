"""
geometry.py
几何工具模块 - 用于粗粒度囊泡模拟中的点云生成与分子对齐

本模块主要负责两件事：
1. 生成高均匀性的球面点云（Fibonacci 螺旋算法），作为脂质/蛋白的候选放置位置
2. 将单个或批量脂质模板对齐到球面特定点，并根据内外叶需求自动翻转方向

设计原则：
- 所有坐标统一使用 nm 单位（与 MARTINI .gro 文件一致）
- 输入校验严格（防止 NaN/Inf/形状错误传播）
- 旋转计算优先使用 scipy.spatial.transform.Rotation 的高级接口（更鲁棒）
- 浮点安全阈值（EPS）用于处理奇点和数值不稳定
- 支持单分子和批量操作（实际构建囊泡时批量性能更重要）

使用注意：
- 脂质模板假设头部珠子已在坐标原点附近（通常在 lipid.py 中完成预处理）
- 向上向量 (lipid_up_vector) 应为从头部指向尾部的单位向量（脂质的“朝向”）
- 内外叶翻转逻辑：外叶尾巴朝球心（-normal），内叶尾巴背离球心（+normal）

后续可扩展方向：
- 支持蛋白对齐（需要额外参数：跨膜区识别、旋转自由度限制）
- 加碰撞检测接口（结合 KDTree 排除重叠位置）
- 支持非均匀点云（例如偏向赤道或极区）
"""

from __future__ import annotations

import numpy as np
from scipy.spatial.transform import Rotation
from typing import Union, Tuple

# ────────────────────────────────────────────────
# 浮点安全阈值（全局常量）
# ────────────────────────────────────────────────
# EPS_NORM：向量模长阈值，小于此值视为“零向量”，用于避免除零或数值不稳定
# EPS_ANGLE：角度奇点阈值，用于判断是否接近 0° 或 180°（叉积退化情况）
EPS_NORM   = 1e-12
EPS_ANGLE  = 1e-6

def _normalize(name: str, vec: np.ndarray, eps: float = EPS_NORM) -> np.ndarray:
    """
    将向量归一化为单位向量。

    参数:
        name : 用于报错的变量名
        vec  : 输入向量 (shape=(3,))
        eps  : 最小模长阈值（防止除零）

    返回:
        归一化后的单位向量

    异常:
        ValueError: 如果向量模长过小或非有限
    """
    norm = np.linalg.norm(vec)
    if not np.isfinite(norm) or norm < eps:
        raise ValueError(f"参数 {name} 的范数过小或非法（norm={norm}），无法归一化")
    return vec / norm

def _as_vec3(name: str, v: np.ndarray) -> np.ndarray:
    """
    安全地将输入转换为 shape=(3,) 的 float64 向量。

    作用：
    1. 统一所有几何计算的输入类型，避免 list/tuple/int/float32 等混用导致广播错误或精度丢失
    2. 强制检查形状和数值有效性（非有限值会提前抛异常，防止后续计算污染 NaN/Inf）

    参数：
        name   : 用于报错时显示的变量名（调试友好）
        v      : 输入向量（支持 list/tuple/array/scalar）

    返回：
        shape=(3,) 的 float64 向量

    异常：
        ValueError: 形状不对或含有 NaN/Inf
    """
    arr = np.asarray(v, dtype=np.float64)
    if arr.shape != (3,):
        raise ValueError(f"{name} 必须是形状为 (3,) 的向量，实际得到 {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} 含有非有限值 (NaN 或 Inf): {arr}")
    return arr


def _as_coords(name: str, coords: np.ndarray) -> np.ndarray:
    """
    安全地将输入转换为 shape=(N,3) 的 float64 坐标矩阵。

    作用：
    确保所有点云输入都是正确的三维坐标矩阵，避免维度错误导致隐式广播或计算错误。

    参数：
        name   : 变量名（报错用）
        coords : 输入坐标（支持 list/array）

    返回：
        shape=(N,3) 的 float64 矩阵

    异常：
        ValueError: 维度不对或含有 NaN/Inf
    """
    arr = np.asarray(coords, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(f"{name} 必须是形状为 (N, 3) 的坐标矩阵，实际得到 {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} 含有非有限值 (NaN 或 Inf)")
    return arr


def generate_fibonacci_sphere(
    radius: float,
    num_points: int,
    center: np.ndarray = np.array([0.0, 0.0, 0.0]),
) -> np.ndarray:
    """
    生成高均匀性的 Fibonacci 螺旋球面点云。

    算法原理：
    - 使用黄金分割螺旋（Golden Spiral）在单位球面上均匀分布点
    - z 坐标采用偏移采样：z = 1 - 2*(i + 0.5)/N，避免南北极点堆积
    - 经度角使用黄金角增量：theta = π * (3 - √5) * i
    - 最后缩放到目标半径并平移到指定球心

    参数：
        radius     : 球半径（单位 nm，与 MARTINI .gro 一致）
        num_points : 生成的点数（建议 1000~50000，根据囊泡大小）
        center     : 球心坐标，shape=(3,)

    返回：
        shape=(num_points, 3) 的点云坐标数组（float64）

    注意：
        - 点数越多，均匀性越好，但计算量也越大
        - 点数太少时极区仍可能略微不均（这是 Fibonacci 算法的固有特性）
    """
    # 参数校验
    radius = float(radius)
    if radius <= 0 or not np.isfinite(radius):
        raise ValueError(f"radius 必须是正有限数，实际得到 {radius}")

    num_points = int(num_points)
    if num_points <= 0:
        raise ValueError(f"num_points 必须是正整数，实际得到 {num_points}")

    center = _as_vec3("center", center)

    # 生成索引（从 0 到 num_points-1）
    i = np.arange(num_points, dtype=np.float64)

    # z 坐标：偏移 0.5 避免极点堆积
    z = 1.0 - (2.0 * (i + 0.5)) / num_points

    # 经度角：黄金角增量（≈ 137.508°）
    theta = np.pi * (3.0 - np.sqrt(5.0)) * i

    # xy 平面半径：sqrt(1 - z²)
    r_xy = np.sqrt(np.maximum(1.0 - z * z, 0.0))  # 防止浮点误差导致负值

    # 笛卡尔坐标（单位球）
    x = r_xy * np.cos(theta)
    y = r_xy * np.sin(theta)
    z_scaled = z

    # 缩放到目标半径
    points = radius * np.column_stack((x, y, z_scaled))

    # 平移到指定球心
    return points + center


def align_lipid_to_sphere(
    lipid_coords: np.ndarray,
    lipid_up_vector: np.ndarray,
    target_position: np.ndarray,
    sphere_center: np.ndarray = np.array([0.0, 0.0, 0.0]),
    flip_for_inner: bool = False,
) -> np.ndarray:
    """
    将单个脂质模板对齐到球面目标点，并根据内外叶需求自动翻转方向。

    核心逻辑：
    1. 计算目标点的法向量 n = normalize(target_position - sphere_center)
    2. 确定目标向上向量：
       - 外叶：尾巴朝球心 → target_up = -n
       - 内叶：尾巴背离球心 → target_up = +n
    3. 使用 Rotation.align_vectors 将脂质模板的向上向量对齐到 target_up
       （scipy 内部自动处理奇点，不需要手动分支处理 angle≈0/π）
    4. 应用旋转 + 平移到目标位置

    参数：
        lipid_coords     : 脂质模板坐标，shape=(N_lipid, 3)，头部应接近原点
        lipid_up_vector  : 脂质模板的“向上”方向（通常头→尾），shape=(3,)
        target_position  : 球面上的放置目标点，shape=(3,)
        sphere_center    : 球心位置，shape=(3,)
        flip_for_inner   : 是否为内叶（True=尾巴背离球心，False=尾巴朝球心）

    返回：
        对齐后的坐标，shape=(N_lipid, 3)

    注意：
        - 模板坐标假设头部已在原点附近（lipid.py 预处理完成）
        - 如果模板原点不在头部，需先在 lipid.py 中平移
    """
    coords = _as_coords("lipid_coords", lipid_coords)
    up_vec = _normalize("lipid_up_vector", _as_vec3("lipid_up_vector", lipid_up_vector))
    target = _as_vec3("target_position", target_position)
    center = _as_vec3("sphere_center", sphere_center)

    # 计算径向向量和单位法向量
    radial = target - center
    normal = _normalize("radial vector", radial)

    # 确定目标向上方向
    target_up = -normal if not flip_for_inner else normal

    # 使用 scipy 的高级接口对齐两个向量（自动处理奇点）
    # align_vectors 返回 (rotation, rmsd)，我们只取 rotation
    rotation, _ = Rotation.align_vectors(
        a=target_up.reshape(1, -1),   # 目标方向 (1,3)
        b=up_vec.reshape(1, -1)       # 模板方向 (1,3)
    )

    # 应用旋转 + 平移到目标点
    rotated = rotation.apply(coords)
    aligned = rotated + target

    return aligned


def align_lipids_batch(
    lipid_coords: np.ndarray,
    lipid_up_vector: np.ndarray,
    target_positions: np.ndarray,
    sphere_center: np.ndarray = np.array([0.0, 0.0, 0.0]),
    flip_for_inner: bool = False,
) -> np.ndarray:
    """
    批量将多个脂质模板对齐到多个球面位置（向量化实现，性能优化版）

    适用场景：
    - 一次性放置几千到几万个脂质分子（构建完整囊泡外/内叶）
    - 避免 for 循环调用单分子版本导致性能瓶颈

    参数：
        lipid_coords      : 单脂质模板坐标 (N_lipid, 3)
        lipid_up_vector   : 单脂质向上向量 (3,)
        target_positions  : 多个目标点 (N_points, 3)
        sphere_center     : 球心
        flip_for_inner    : 是否内叶翻转

    返回：
        所有对齐后的坐标，shape=(N_points * N_lipid, 3)

    实现细节：
    - 使用广播将单个向上向量扩展到所有目标点
    - Rotation.align_vectors 支持批量输入
    - 最终 reshape 合并所有脂质坐标
    """
    coords = _as_coords("lipid_coords", lipid_coords)
    up_vec = _normalize("lipid_up_vector", _as_vec3("lipid_up_vector", lipid_up_vector))
    targets = _as_coords("target_positions", target_positions)
    center = _as_vec3("sphere_center", sphere_center)

    # 计算所有法向量并归一化
    radials = targets - center
    normals = np.apply_along_axis(_normalize, 1, radials)

    # 目标向上向量（外叶 -normal，内叶 +normal）
    target_ups = -normals if not flip_for_inner else normals

    # 批量计算旋转（scipy 支持广播输入）
    rotations, _ = Rotation.align_vectors(
        a=target_ups,                          # (N_points, 3)
        b=up_vec[None, :].repeat(len(targets), axis=0)  # (N_points, 3)
    )

    # 应用旋转（广播到所有脂质）
    rotated = rotations.apply(
        coords[None, :, :].repeat(len(targets), axis=0)  # (N_points, N_lipid, 3)
    )

    # 平移到各自目标点
    aligned = rotated + targets[:, None, :]  # 广播到 (N_points, N_lipid, 3)

    # 展平为 (N_points * N_lipid, 3)
    return aligned.reshape(-1, 3)


__all__ = [
    "generate_fibonacci_sphere",
    "align_lipid_to_sphere",
    "align_lipids_batch",
]