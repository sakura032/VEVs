from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# 把仓库根目录加入 sys.path，保证脚本可直接通过
# `python vesicle/test/test_factory.py` 运行。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vesicle.models.coarse_grained.lipid import LIPID_LIBRARY
from vesicle.utils.lipid_factory import build_lipid_3d


def _compute_anchor_center(lipid_3d, anchors):
    """
    计算某组锚点在当前坐标系下的几何中心。

    这个函数用于测试“平移是否正确”：
    - 理论上，build_lipid_3d 已经把头部中心平移到 (0, 0, 0)。
    - 因此这里计算 head_anchors 的中心，结果应非常接近零向量。
    """
    anchor_indices = [lipid_3d.bead_names.index(anchor) for anchor in anchors]
    return np.mean(lipid_3d.coords[anchor_indices], axis=0)


def main() -> None:
    """
    最小工厂测试（smoke test）。

    覆盖目标：
    1. POPC：验证 .gro 文件解析路径。
    2. CHOL：验证硬编码构象路径。

    输出重点：
    - 坐标矩阵 shape 是否合理。
    - 方向向量是否为单位向量。
    - 头部中心是否回到原点。
    - z 分量是否符合“头在上、尾向下（通常为负 z）”的直觉。
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
