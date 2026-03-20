from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# 让脚本可直接通过 `python vesicle/test/test_geometry.py` 运行。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vesicle.utils.geometry import align_lipid_to_sphere, generate_fibonacci_sphere


def _unit(vec: np.ndarray) -> np.ndarray:
    """将输入向量单位化（测试辅助函数）。"""
    norm = np.linalg.norm(vec)
    if norm < 1e-12:
        raise ValueError("测试中出现零向量，无法单位化")
    return vec / norm


def _report_alignment(
    aligned: np.ndarray,
    target_point: np.ndarray,
    center: np.ndarray,
    label: str,
    expect_tail_to_center: bool,
) -> None:
    """
    输出并校验放置结果。

    参数语义：
    - expect_tail_to_center=True: 期望尾部指向球心（外叶）。
    - expect_tail_to_center=False: 期望尾部背离球心（内叶）。
    """
    head = aligned[0]
    tail = aligned[1]

    tail_dir = _unit(tail - head)
    to_center = _unit(center - head)
    away_center = -to_center

    expected_dir = to_center if expect_tail_to_center else away_center
    dot_val = float(np.dot(tail_dir, expected_dir))

    print(f"\n[{label}]")
    print(f"head = {head}")
    print(f"tail = {tail}")
    print(f"tail_dir = {tail_dir}")
    print(f"expected_dir = {expected_dir}")
    print(f"dot(tail_dir, expected_dir) = {dot_val:.6f}")

    if np.allclose(head, target_point, atol=1e-8):
        print("head_check = 通过（头部已到目标点）")
    else:
        print("head_check = 失败（头部未正确到达目标点）")

    if dot_val > 0.999:
        print("tail_direction_check = 通过（尾部方向符合预期）")
    else:
        print("tail_direction_check = 失败（尾部方向异常）")


def main() -> None:
    """
    几何模块最小功能测试。

    测试 1：Fibonacci 球面点云
    - 生成半径 50 nm，1000 点。
    - 打印 shape 与半径统计，验证点都在球面附近。

    测试 2：脂质对齐与放置（外叶）
    - 模板坐标: [[0,0,0], [0,0,-1]]，固有向量 [0,0,-1]。
    - 放置在 target_point=[50,0,0]。
    - 验证头部是否到目标点、尾部是否指向球心。

    测试 3：脂质对齐与放置（内叶）
    - 同样放置在 target_point=[50,0,0]。
    - 验证头部是否到目标点、尾部是否背离球心。
    """
    print("=== Geometry Smoke Test ===")

    # ---------- 测试 1 ----------
    radius = 50.0
    num_points = 1000
    center = np.array([0.0, 0.0, 0.0], dtype=np.float64)

    points = generate_fibonacci_sphere(radius=radius, num_points=num_points, center=center)

    norms = np.linalg.norm(points - center, axis=1)
    print("\n[Fibonacci Sphere]")
    print(f"points.shape = {points.shape}")
    print(f"radius_mean = {norms.mean():.6f}")
    print(f"radius_min  = {norms.min():.6f}")
    print(f"radius_max  = {norms.max():.6f}")

    # ---------- 测试输入 ----------
    coords = np.array(
        [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, -1.0],
        ],
        dtype=np.float64,
    )
    v_intrinsic = np.array([0.0, 0.0, -1.0], dtype=np.float64)
    target_point = np.array([50.0, 0.0, 0.0], dtype=np.float64)

    # ---------- 测试 2：外叶 ----------
    aligned_outer = align_lipid_to_sphere(
        coords=coords,
        v_intrinsic=v_intrinsic,
        target_point=target_point,
        center=center,
        is_inner_leaflet=False,
    )
    _report_alignment(
        aligned=aligned_outer,
        target_point=target_point,
        center=center,
        label="Align Lipid To Sphere | Outer Leaflet",
        expect_tail_to_center=True,
    )

    # ---------- 测试 3：内叶 ----------
    aligned_inner = align_lipid_to_sphere(
        coords=coords,
        v_intrinsic=v_intrinsic,
        target_point=target_point,
        center=center,
        is_inner_leaflet=True,
    )
    _report_alignment(
        aligned=aligned_inner,
        target_point=target_point,
        center=center,
        label="Align Lipid To Sphere | Inner Leaflet",
        expect_tail_to_center=False,
    )


if __name__ == "__main__":
    main()
