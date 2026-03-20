from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# 让测试脚本可以通过 `python vesicle/test/test_factory.py` 直接运行。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vesicle.models.lipid import LIPID_LIBRARY, build_lipid_3d


def _compute_anchor_center(lipid_3d, anchors):
    """
    计算指定锚点组在当前坐标中的几何中心。

    该函数用于验证“头部归一到原点”是否生效：
    - build_lipid_3d 会执行 coords -= head_center。
    - 因此 head_anchors 的中心应该接近 [0, 0, 0]。
    """
    anchor_indices = [lipid_3d.bead_names.index(anchor) for anchor in anchors]
    return np.mean(lipid_3d.coords[anchor_indices], axis=0)


def main() -> None:
    """
    phase1 personB 的脂质工厂烟雾测试（smoke test）。

    覆盖目标：
    - POPC: 验证 .gro 文件读取路径。
    - CHOL: 验证硬编码构象路径。
    """
    print("=== Lipid Factory Smoke Test ===")

    for lipid_name in ("POPC", "CHOL"):
        blueprint = LIPID_LIBRARY[lipid_name]
        lipid_3d = build_lipid_3d(blueprint)

        head_center = _compute_anchor_center(lipid_3d, blueprint.head_anchors)
        vector_norm = np.linalg.norm(lipid_3d.vector)

        print(f"\n[{lipid_name}]")
        print(f"coords.shape = {lipid_3d.coords.shape}")
        print(
            "vector = "
            f"[{lipid_3d.vector[0]: .4f}, {lipid_3d.vector[1]: .4f}, {lipid_3d.vector[2]: .4f}]"
        )
        print(f"|vector| = {vector_norm:.6f}")
        print(
            "head_center_after_shift = "
            f"[{head_center[0]: .6f}, {head_center[1]: .6f}, {head_center[2]: .6f}]"
        )

        if lipid_3d.vector[2] < 0:
            print("direction_check = 通过（主轴朝向负 z，符合插入膜内部直觉）")
        else:
            print("direction_check = 警告（主轴未朝负 z，请检查模板定义）")


if __name__ == "__main__":
    main()

