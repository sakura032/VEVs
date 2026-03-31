"""
tests.vesicle.test_placement
============================

这组测试覆盖 `src/vesicle/utils/placement.py` 里的核心空间放置原语：

- 球面候选点生成
- 脂质模板球面对齐
- 局部角扰动
- 基础碰撞检测

文件名从 `test_geometry.py` 调整为 `test_placement.py`，是为了和当前代码结构保持一致：
这里测试的不再只是几何函数，还包括了同属于放置层的空间排斥查询。
"""

from __future__ import annotations

import numpy as np
import pytest

from src.vesicle.utils.placement import (
    CollisionDetector,
    align_lipid_to_sphere,
    apply_local_axis_angle_perturbation,
    generate_fibonacci_sphere,
)


def _unit(vec: np.ndarray) -> np.ndarray:
    """测试辅助函数：把任意非零向量转成单位向量。"""
    return vec / np.linalg.norm(vec)


def test_generate_fibonacci_sphere_points_lie_on_requested_radius() -> None:
    """
    只要球面布点正确，所有点到球心的距离都应该等于请求半径。
    """
    center = np.array([1.0, -2.0, 0.5], dtype=np.float64)
    points = generate_fibonacci_sphere(radius=50.0, num_points=1000, center=center)

    radii = np.linalg.norm(points - center, axis=1)
    assert points.shape == (1000, 3)
    assert np.allclose(radii, 50.0)


@pytest.mark.parametrize(
    ("flip_for_inner", "expected_dot_sign"),
    [
        (False, 1.0),
        (True, -1.0),
    ],
)
def test_align_lipid_to_sphere_orients_leaflets_correctly(
    flip_for_inner: bool,
    expected_dot_sign: float,
) -> None:
    """
    用一个最简单的“二珠模板”验证内外叶朝向：
    - 外叶时尾部应朝球心；
    - 内叶时尾部应背离球心。
    """
    coords = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, -1.0]], dtype=np.float64)
    intrinsic_axis = np.array([0.0, 0.0, -1.0], dtype=np.float64)
    target = np.array([10.0, 0.0, 0.0], dtype=np.float64)

    aligned = align_lipid_to_sphere(
        lipid_coords=coords,
        lipid_up_vector=intrinsic_axis,
        target_position=target,
        flip_for_inner=flip_for_inner,
    )

    head = aligned[0]
    tail = aligned[1]
    tail_direction = _unit(tail - head)
    center_direction = _unit(-head)

    assert np.allclose(head, target)
    assert np.isclose(np.dot(tail_direction, center_direction), expected_dot_sign, atol=1e-6)


def test_apply_local_axis_angle_perturbation_preserves_radius_and_caps_angle() -> None:
    """
    局部扰动必须满足两个硬约束：
    - 半径不变
    - 扰动角不会超过上限
    """
    np.random.seed(7)
    anchor = np.array([0.0, 0.0, 10.0], dtype=np.float64)
    perturbed = apply_local_axis_angle_perturbation(anchor, max_angle_rad=0.26)

    assert np.isclose(np.linalg.norm(perturbed), 10.0)

    angle = np.arccos(
        np.clip(np.dot(_unit(anchor), _unit(perturbed)), -1.0, 1.0)
    )
    assert angle <= 0.26 + 1e-12


def test_apply_local_axis_angle_perturbation_rejects_negative_angle() -> None:
    """负角上限没有物理意义，应该直接拒绝。"""
    with pytest.raises(ValueError, match="max_angle_rad"):
        apply_local_axis_angle_perturbation(np.array([1.0, 0.0, 0.0]), max_angle_rad=-0.1)


def test_collision_detector_reports_hit_after_tree_build() -> None:
    """已注册并建树后的蛋白 bead 应能被最近邻查询命中。"""
    detector = CollisionDetector()
    detector.add_protein(
        np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.3]], dtype=np.float64),
        category="surface_transmembrane",
    )
    detector.build_trees()

    assert detector.check_collision(
        np.array([0.0, 0.0, 0.05], dtype=np.float64),
        category="surface_transmembrane",
        radius=0.1,
    )


def test_collision_detector_returns_false_when_tree_missing() -> None:
    """未建树或该类别没有蛋白时，查询应保守返回 False。"""
    detector = CollisionDetector()

    assert not detector.check_collision(
        np.array([1.0, 0.0, 0.0], dtype=np.float64),
        category="surface_transmembrane",
    )
