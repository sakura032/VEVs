from __future__ import annotations

import numpy as np
from scipy.spatial.transform import Rotation


# 浮点安全阈值：
# - EPS_VECTOR 用于判断向量范数是否接近 0，避免除以 0。
# - EPS_ANGLE 用于判断旋转角是否接近 0 或接近 π，处理旋转奇点。
EPS_VECTOR = 1e-12
EPS_ANGLE = 1e-6


def _as_vec3(name: str, value: np.ndarray) -> np.ndarray:
    """
    将输入安全转换为 shape=(3,) 的 float64 向量。

    设计目的：
    1. 统一所有几何计算输入类型，避免 list/tuple/float32 混用导致隐式精度问题。
    2. 先做形状与有限性检查，确保后续线性代数过程不会出现 NaN/Inf 污染。
    """
    vec = np.asarray(value, dtype=np.float64)
    if vec.shape != (3,):
        raise ValueError(f"参数 {name} 必须是形状为 (3,) 的向量，当前为 {vec.shape}")
    if not np.all(np.isfinite(vec)):
        raise ValueError(f"参数 {name} 含有非有限值（NaN 或 Inf）")
    return vec


def _as_coords(name: str, coords: np.ndarray) -> np.ndarray:
    """
    将输入安全转换为 shape=(N,3) 的 float64 坐标矩阵。

    设计目的：
    - 明确几何变换函数只接受三维点云，避免一维数组或错误列数导致的隐式广播错误。
    """
    arr = np.asarray(coords, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(f"参数 {name} 必须是形状为 (N, 3) 的矩阵，当前为 {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"参数 {name} 含有非有限值（NaN 或 Inf）")
    return arr


def _normalize(name: str, vec: np.ndarray, eps: float = EPS_VECTOR) -> np.ndarray:
    """
    将向量归一化为单位向量。

    数学意义：
    - 将方向信息与长度信息分离，后续旋转算法（点乘、叉乘、夹角）都依赖单位向量。

    数值安全：
    - 当范数过小（接近 0）时，归一化会出现除 0 风险，因此直接抛出异常。
    """
    norm = np.linalg.norm(vec)
    if not np.isfinite(norm) or norm < eps:
        raise ValueError(f"参数 {name} 的范数过小或非法（norm={norm}），无法归一化")
    return vec / norm


def generate_fibonacci_sphere(
    radius: float,
    num_points: int,
    center: np.ndarray = np.array([0.0, 0.0, 0.0]),
) -> np.ndarray:
    """
    生成高均匀性的 Fibonacci 球面点云。

    参数：
    - radius: 球半径（单位由调用方决定，例如 nm）。
    - num_points: 点数 N。
    - center: 球心坐标，shape=(3,)。

    返回：
    - shape=(N,3) 的点云数组。

    底层算法说明：
    1. 使用黄金分割螺旋（Golden Spiral）在单位球面上撒点。
    2. 使用 z 的 0.5 偏移补偿：
       z = 1 - 2*(i+0.5)/N
       这一步可以显著减少南北极区域过密的离散误差。
    3. 极角使用黄金角增量：
       theta = pi*(3-sqrt(5))*i
    4. 将单位球点缩放到目标半径，并平移到 center。
    """
    if not isinstance(num_points, (int, np.integer)) or num_points <= 0:
        raise ValueError(f"num_points 必须是正整数，当前为 {num_points}")

    radius_f = float(radius)
    if not np.isfinite(radius_f) or radius_f < 0.0:
        raise ValueError(f"radius 必须是有限且非负的实数，当前为 {radius}")

    center_vec = _as_vec3("center", center)

    i = np.arange(num_points, dtype=np.float64)

    # 面积补偿 z 采样：避免点在极区堆积。
    z = 1.0 - (2.0 * (i + 0.5)) / float(num_points)

    # 黄金角：相邻样本在经度方向的理想错位。
    theta = np.pi * (3.0 - np.sqrt(5.0)) * i

    # 在单位球上，横截面半径满足 r_xy = sqrt(1-z^2)。
    # clip 是浮点护甲：防止 1-z^2 因舍入误差变成极小负数。
    r_xy = np.sqrt(np.clip(1.0 - z * z, 0.0, 1.0))

    x = radius_f * r_xy * np.cos(theta)
    y = radius_f * r_xy * np.sin(theta)
    z_scaled = radius_f * z

    points = np.column_stack((x, y, z_scaled))

    # 最后平移到目标球心。
    return points + center_vec


def align_lipid_to_sphere(
    coords: np.ndarray,
    v_intrinsic: np.ndarray,
    target_point: np.ndarray,
    center: np.ndarray = np.array([0.0, 0.0, 0.0]),
    is_inner_leaflet: bool = False,
) -> np.ndarray:
    """
    将脂质模板坐标旋转并平移到球面目标点，且自动处理旋转奇点。

    参数：
    - coords: 脂质模板坐标，shape=(N,3)。通常头部已在原点。
    - v_intrinsic: 脂质模板固有方向（头->尾单位向量）。
    - target_point: 目标放置点（球面上一点）。
    - center: 球心。
    - is_inner_leaflet:
      - False: 外叶，要求尾巴指向球心。
      - True: 内叶，要求尾巴背离球心。

    返回：
    - 旋转+平移后的新坐标，shape=(N,3)。

    数学流程：
    1. 算球面法线 n = (target_point-center)/||...||。
    2. 根据膜叶确定目标尾向量 v_target：
       外叶 -> -n，内叶 -> n。
    3. 算夹角 angle = arccos(clip(dot(v_intrinsic, v_target), -1, 1))。
    4. 处理奇点：
       - angle≈0：无需旋转，直接平移。
       - angle≈π：构造动态正交轴，避免叉积退化。
    5. 常规情况使用 axis=cross(v_intrinsic, v_target) 归一化。
    6. 用 Rotation.from_rotvec(axis*angle) 做旋转，再加 target_point 平移。
    """
    coords_arr = _as_coords("coords", coords)
    v_in = _normalize("v_intrinsic", _as_vec3("v_intrinsic", v_intrinsic))
    target = _as_vec3("target_point", target_point)
    center_vec = _as_vec3("center", center)

    radial_vec = target - center_vec
    n = _normalize("target_point-center", radial_vec)

    # 外叶：尾巴朝球心；内叶：尾巴背离球心。
    v_target = n if is_inner_leaflet else -n

    # 浮点护甲：clip 防止点乘略超 [-1,1] 导致 arccos 域错误。
    dot_prod = float(np.dot(v_in, v_target))
    dot_prod = float(np.clip(dot_prod, -1.0, 1.0))
    angle = float(np.arccos(dot_prod))

    # 奇点 1：几乎无需旋转，直接平移。
    if angle < EPS_ANGLE:
        return coords_arr + target

    # 奇点 2：接近 180° 反平行，cross(v_in, v_target) 近似 0，需构造正交轴。
    if angle > np.pi - EPS_ANGLE:
        helper = np.array([0.0, 1.0, 0.0], dtype=np.float64) if abs(v_in[0]) > 0.9 else np.array([1.0, 0.0, 0.0], dtype=np.float64)
        axis = np.cross(v_in, helper)
    else:
        axis = np.cross(v_in, v_target)

    axis_norm = np.linalg.norm(axis)

    # 兜底保护：理论上奇点分支已避免退化，但仍加一层防护处理数值极端情况。
    if axis_norm < EPS_VECTOR:
        fallback_helper = np.array([0.0, 0.0, 1.0], dtype=np.float64)
        axis = np.cross(v_in, fallback_helper)
        axis_norm = np.linalg.norm(axis)
        if axis_norm < EPS_VECTOR:
            raise ValueError("旋转轴退化：无法构造稳定的旋转轴")

    axis = axis / axis_norm

    rotation = Rotation.from_rotvec(axis * angle)
    rotated = rotation.apply(coords_arr)

    # 输入模板默认头部在原点，因此加 target_point 后头部落在目标点。
    return rotated + target


__all__ = ["generate_fibonacci_sphere", "align_lipid_to_sphere"]
