"""
tests.vesicle.test_factory
==========================

这组测试验证脂质模板构建是否真的完成了“标准化”：
- 头部中心是否被平移到原点；
- 方向向量是否归一化；
- CHOL 是否走了预期的硬编码模板路径。
"""

from __future__ import annotations

import numpy as np

from src.vesicle.models.lipid import HARDCODED_CONFORMERS, LIPID_LIBRARY, build_lipid_3d


def _anchor_center(lipid_3d, anchors):
    """根据锚点名重新计算当前模板坐标中的锚点几何中心。"""
    indices = [lipid_3d.bead_names.index(anchor) for anchor in anchors]
    return np.mean(lipid_3d.coords[indices], axis=0)


def test_build_lipid_3d_recenters_head_group_and_normalizes_vector() -> None:
    """
    这是 builder 使用脂质模板前最重要的两个前提：
    - 头部中心在原点；
    - `vector` 已经是单位向量。
    """
    for lipid_name in ("POPC", "CHOL"):
        blueprint = LIPID_LIBRARY[lipid_name]
        lipid_3d = build_lipid_3d(blueprint)

        assert lipid_3d.coords.shape[1] == 3
        assert np.allclose(
            _anchor_center(lipid_3d, blueprint.head_anchors),
            np.zeros(3),
            atol=1e-8,
        )
        assert np.isclose(np.linalg.norm(lipid_3d.vector), 1.0)
        assert lipid_3d.vector[2] < 0.0


def test_build_lipid_3d_uses_hardcoded_chol_conformer() -> None:
    """
    CHOL 是特殊脂质，当前显式要求走硬编码模板。
    """
    chol = build_lipid_3d(LIPID_LIBRARY["CHOL"])

    assert chol.bead_names == HARDCODED_CONFORMERS["CHOL"]["bead_names"]
    assert chol.coords.shape == HARDCODED_CONFORMERS["CHOL"]["coords"].shape
