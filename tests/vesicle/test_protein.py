"""
tests.vesicle.test_protein
==========================

这组测试保证蛋白模板的两个关键能力可用：
- `.gro` 读取与几何缓存计算；
- 放置前局部坐标系整理。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from src.vesicle.models.protein import Protein

PROTEIN_DIR = Path("data/vesicle/proteins")


def test_protein_from_gro_loads_coords_and_geometry_descriptors() -> None:
    """
    最基本的模板加载能力：
    - bead 坐标数量正确；
    - bead 名与坐标一一对应；
    - 几何缓存不为空。
    """
    protein = Protein.from_gro("CD9", PROTEIN_DIR / "cg_CD9_clean.gro")

    assert protein.coords.shape == (533, 3)
    assert len(protein.bead_types) == protein.coords.shape[0]
    assert protein.get_projected_radius() > 0.0
    assert protein.bounding_box is not None
    assert protein.bounding_box[0].shape == (3,)
    assert protein.bounding_box[1].shape == (3,)


def test_prepared_for_placement_centers_tm_and_xy_without_changing_radius() -> None:
    """
    `prepared_for_placement()` 不应改变模板本身的尺度，
    只应改变它在局部坐标系中的平移偏置。
    """
    protein = Protein.from_gro("CD81", PROTEIN_DIR / "cg_CD81_clean.gro")
    prepared = protein.prepared_for_placement()

    assert np.isclose(prepared.get_tm_center(), 0.0)
    assert np.allclose(np.mean(prepared.coords[:, :2], axis=0), np.zeros(2), atol=1e-8)
    assert np.isclose(prepared.get_projected_radius(), protein.get_projected_radius())


def test_copy_template_duplicates_loaded_template_without_reparsing() -> None:
    """
    复制模板应该保留几何与 bead 信息，但返回独立对象。
    """
    protein = Protein.from_gro("CD63", PROTEIN_DIR / "cg_CD63_clean.gro")
    copied = protein.copy_template()

    assert copied is not protein
    assert copied.name == protein.name
    assert copied.bead_types == protein.bead_types
    assert np.allclose(copied.coords, protein.coords)
