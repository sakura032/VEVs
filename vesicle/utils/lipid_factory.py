from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from vesicle.models.coarse_grained.lipid import Lipid3D, LipidBlueprint


# -----------------------------------------------------------------------------
# 硬编码构象库（Hardcoded conformers）
# -----------------------------------------------------------------------------
# 说明：
# 1. 对于 Martini 体系中不易稳定获取单分子模板的脂质（例如 CHOL），
#    这里提供内置参考构象，确保组装流程在离线环境下也可复现。
# 2. 该坐标版本按你提供的 insane.py 权威参数录入：
#    - ROH 位于原点
#    - C2 位于 z=-1.300 nm
# 3. 这样定义后，使用 head_anchors=['ROH'] 与 tail_anchors=['C2']
#    可直接得到稳定、物理意义清晰的“头 -> 尾”插入方向。
HARDCODED_CONFORMERS: Dict[str, Dict[str, object]] = {
    "CHOL": {
        "bead_names": ["ROH", "R1", "R2", "R3", "R4", "R5", "C1", "C2"],
        "coords": np.array(
            [
                [0.000, 0.000, 0.000],    # ROH: 极性头部锚点（剑柄，位于原点）
                [-0.150, 0.100, -0.250],  # R1: 甾环结构
                [0.150, -0.100, -0.300],  # R2: 甾环结构
                [-0.150, 0.100, -0.550],  # R3: 甾环结构
                [0.150, -0.100, -0.600],  # R4: 甾环结构
                [0.000, 0.000, -0.800],   # R5: 甾环末端
                [-0.100, 0.100, -1.050],  # C1: 短柔性尾部起点
                [0.000, 0.000, -1.300],   # C2: 疏水尾部绝对末端（剑尖）
            ],
            dtype=np.float64,
        ),
    }
}


def _resolve_gro_path(lipid_name: str, gro_dir: str) -> Path:
    """
    根据脂质名在给定目录中寻找可用的 .gro 文件。

    策略：
    1. 仅采用标准命名：<name>-em.gro 与 <name>.gro。
    2. 不再兼容 DBSM 别名，避免上传错误文件被误读。
    3. 找不到时抛出清晰错误，帮助快速定位数据问题。
    """
    base_dir = Path(gro_dir)
    if not base_dir.exists():
        raise FileNotFoundError(f"脂质模板目录不存在: {base_dir}")

    candidates = [f"{lipid_name}-em.gro", f"{lipid_name}.gro"]

    for candidate in candidates:
        candidate_path = base_dir / candidate
        if candidate_path.exists():
            return candidate_path

    raise FileNotFoundError(
        f"未找到脂质 {lipid_name} 的 .gro 文件。"
        f"已尝试: {', '.join(candidates)}；目录: {base_dir}"
    )


def _parse_gro_coordinates(gro_path: Path) -> Tuple[List[str], np.ndarray]:
    """
    解析 .gro 文件中的珠子名称与坐标。

    关键要求：
    - 严格使用 .gro 固定列宽切片读取，不使用 split()。
    - 这样可避免字段中出现空格或对齐变化时的解析歧义。

    .gro 关键列（1-based，可对照 GROMACS 文档）：
    - 原子名: 11-15 列  -> Python 切片 [10:15]
    - x 坐标: 21-28 列   -> Python 切片 [20:28]
    - y 坐标: 29-36 列   -> Python 切片 [28:36]
    - z 坐标: 37-44 列   -> Python 切片 [36:44]
    """
    with gro_path.open("r", encoding="utf-8") as handle:
        lines = handle.readlines()

    if len(lines) < 3:
        raise ValueError(f".gro 文件过短，无法解析: {gro_path}")

    try:
        n_atoms = int(lines[1].strip())
    except ValueError as exc:
        raise ValueError(f".gro 第二行不是合法原子数: {gro_path}") from exc

    atom_lines = lines[2 : 2 + n_atoms]
    if len(atom_lines) != n_atoms:
        raise ValueError(
            f".gro 原子行数量不匹配: 声明 {n_atoms}，实际 {len(atom_lines)}，文件 {gro_path}"
        )

    bead_names: List[str] = []
    coords_list: List[List[float]] = []

    for line_idx, line in enumerate(atom_lines, start=1):
        if len(line) < 44:
            raise ValueError(
                f"第 {line_idx} 条原子记录长度不足 44 列，无法按固定列宽读取: {gro_path}"
            )

        bead_name = line[10:15].strip()
        if not bead_name:
            raise ValueError(f"第 {line_idx} 条原子记录珠子名为空: {gro_path}")

        try:
            x = float(line[20:28].strip())
            y = float(line[28:36].strip())
            z = float(line[36:44].strip())
        except ValueError as exc:
            raise ValueError(
                f"第 {line_idx} 条原子记录坐标解析失败（列宽切片模式）: {gro_path}"
            ) from exc

        bead_names.append(bead_name)
        coords_list.append([x, y, z])

    coords = np.asarray(coords_list, dtype=np.float64)
    return bead_names, coords


def _find_anchor_indices(
    bead_names: List[str],
    anchors: List[str],
    lipid_name: str,
    anchor_group_name: str,
) -> List[int]:
    """
    在珠子名称列表中查找锚点索引。

    为什么单独封装：
    - 锚点是几何定义的核心，错误必须早失败（fail fast）。
    - 错误信息会直接指出缺失锚点，避免后续出现难排查的 NaN。
    """
    indices: List[int] = []
    missing: List[str] = []

    for anchor in anchors:
        try:
            indices.append(bead_names.index(anchor))
        except ValueError:
            missing.append(anchor)

    if missing:
        raise ValueError(
            f"脂质 {lipid_name} 缺失 {anchor_group_name} 锚点: {missing}。"
            f"可用珠子: {bead_names}"
        )

    return indices


def build_lipid_3d(
    blueprint: LipidBlueprint,
    gro_dir: str = "vesicle/data/lipids",
) -> Lipid3D:
    """
    由脂质蓝图构建 3D 实体（Lipid3D）。

    流程摘要：
    1. 先确定坐标来源：硬编码（如 CHOL）或 .gro 文件。
    2. 根据蓝图锚点查找 head/tail 对应珠子索引。
    3. 分别求 head_center 与 tail_center。
    4. 将全体坐标平移到“头部中心在原点”。
    5. 计算并归一化“头 -> 尾”方向向量。
    6. 组装并返回 Lipid3D 对象。

    这样可以保证：
    - 所有脂质（含 CHOL）都遵循统一物理几何定义。
    - 后续旋转、放置、拼装阶段都可以直接消费标准化输出。
    """
    # -------------------------
    # 第 1 步：读取原始构象
    # -------------------------
    if blueprint.name in HARDCODED_CONFORMERS:
        conformer = HARDCODED_CONFORMERS[blueprint.name]
        bead_names = list(conformer["bead_names"])
        # 复制数组，避免后续平移时污染全局常量。
        coords = np.array(conformer["coords"], dtype=np.float64, copy=True)
    else:
        gro_path = _resolve_gro_path(blueprint.name, gro_dir)
        bead_names, coords = _parse_gro_coordinates(gro_path)

    # -------------------------
    # 第 2 步：定位锚点索引
    # -------------------------
    head_indices = _find_anchor_indices(
        bead_names=bead_names,
        anchors=blueprint.head_anchors,
        lipid_name=blueprint.name,
        anchor_group_name="head_anchors",
    )
    tail_indices = _find_anchor_indices(
        bead_names=bead_names,
        anchors=blueprint.tail_anchors,
        lipid_name=blueprint.name,
        anchor_group_name="tail_anchors",
    )

    # -------------------------
    # 第 3 步：求头尾中心
    # -------------------------
    head_center = np.mean(coords[head_indices], axis=0)
    tail_center = np.mean(coords[tail_indices], axis=0)

    # -------------------------
    # 第 4 步：整体平移到头部原点
    # -------------------------
    # NumPy 广播机制： (N, 3) - (3,) -> 每个珠子都减去 head_center
    shifted_coords = coords - head_center

    # -------------------------
    # 第 5 步：计算单位方向向量
    # -------------------------
    direction = tail_center - head_center
    norm = np.linalg.norm(direction)

    if norm < 1e-12:
        raise ValueError(
            f"脂质 {blueprint.name} 的头尾中心几乎重合，无法定义稳定方向向量。"
        )

    vector = direction / norm

    # -------------------------
    # 第 6 步：封装返回实体
    # -------------------------
    return Lipid3D(
        blueprint=blueprint,
        bead_names=bead_names,
        coords=shifted_coords,
        vector=vector,
    )


__all__ = ["HARDCODED_CONFORMERS", "build_lipid_3d"]
