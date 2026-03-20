from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np


@dataclass(frozen=True)
class LipidBlueprint:
    """
    脂质“蓝图对象”，只保存静态元数据，不保存任何运行时坐标状态。

    字段说明：
    - name: 脂质名称（例如 POPC / CHOL）。
    - head_group: 头基类别（PC/PE/PS/SM/PIP2/sterol 等）。
    - tail_type: 尾部化学类型描述，用于文档和统计。
    - charge: MARTINI 粗粒度层面的近似净电荷。
    - area_per_lipid: 单分子占据面积（nm^2），用于后续估算装配数量。
    - preferred_leaflet: 偏好膜叶（outer/inner/both）。
    - head_anchors: 头部锚点珠子名列表，用于定义“头部中心”。
    - tail_anchors: 尾部锚点珠子名列表，用于定义“尾部中心”。
    """

    name: str
    head_group: str
    tail_type: str
    charge: float
    area_per_lipid: float
    preferred_leaflet: str
    head_anchors: List[str]
    tail_anchors: List[str]


@dataclass
class Lipid3D:
    """
    脂质“运行时 3D 实体对象”。

    约定：
    - coords: 形状为 (N, 3) 的坐标矩阵，且已经平移到“头部中心在原点”。
    - vector: 形状为 (3,) 的单位向量，方向为“头部中心 -> 尾部中心”。
    """

    blueprint: LipidBlueprint
    bead_names: List[str]
    coords: np.ndarray
    vector: np.ndarray

    @property
    def name(self) -> str:
        """便捷访问脂质名称，等价于 self.blueprint.name。"""
        return self.blueprint.name

    def __repr__(self) -> str:
        """调试打印：显示脂质名、珠子数量与方向向量。"""
        return (
            f"<Lipid3D name={self.name} beads={len(self.bead_names)} "
            f"vector=({self.vector[0]:.3f}, {self.vector[1]:.3f}, {self.vector[2]:.3f})>"
        )


# 统一脂质蓝图库（Blueprint Library）
# 说明：
# 1. 方向定义全部使用“锚点法”，不再使用“去头部后剩余珠子均值”旧策略。
# 2. DPSM 这里按你当前的官方文件 DPSM-em.gro 适配为 C3A/C4B。
LIPID_LIBRARY: Dict[str, LipidBlueprint] = {
    "POPC": LipidBlueprint(
        name="POPC",
        head_group="PC",
        tail_type="palmitoyl-oleoyl",
        charge=0.0,
        area_per_lipid=0.64,
        preferred_leaflet="both",
        head_anchors=["NC3", "PO4"],
        tail_anchors=["C4A", "C4B"],
    ),
    "POPE": LipidBlueprint(
        name="POPE",
        head_group="PE",
        tail_type="palmitoyl-oleoyl",
        charge=0.0,
        area_per_lipid=0.65,
        preferred_leaflet="both",
        head_anchors=["NH3", "PO4"],
        tail_anchors=["C4A", "C4B"],
    ),
    "POPS": LipidBlueprint(
        name="POPS",
        head_group="PS",
        tail_type="palmitoyl-oleoyl",
        charge=-1.0,
        area_per_lipid=0.66,
        preferred_leaflet="inner",
        head_anchors=["CNO", "PO4"],
        tail_anchors=["C4A", "C4B"],
    ),
    "DPSM": LipidBlueprint(
        name="DPSM",
        head_group="SM",
        tail_type="sphingomyelin",
        charge=0.0,
        area_per_lipid=0.55,
        preferred_leaflet="outer",
        head_anchors=["NC3", "PO4"],
        tail_anchors=["C3A", "C4B"],
    ),
    "POP2": LipidBlueprint(
        name="POP2",
        head_group="PIP2",
        tail_type="phosphoinositide",
        charge=-4.0,
        area_per_lipid=0.70,
        preferred_leaflet="inner",
        head_anchors=["P1", "P2", "PO4"],
        tail_anchors=["C4A", "C4B"],
    ),
    "CHOL": LipidBlueprint(
        name="CHOL",
        head_group="sterol",
        tail_type="cholesterol",
        charge=0.0,
        area_per_lipid=0.40,
        preferred_leaflet="both",
        head_anchors=["ROH"],
        tail_anchors=["C2"],
    ),
}


# 硬编码构象库（目前仅 CHOL）。
# 坐标来源按你提供的 insane.py 权威坐标：ROH 在原点，C2 在 z=-1.300 nm。
HARDCODED_CONFORMERS: Dict[str, Dict[str, object]] = {
    "CHOL": {
        "bead_names": ["ROH", "R1", "R2", "R3", "R4", "R5", "C1", "C2"],
        "coords": np.array(
            [
                [0.000, 0.000, 0.000],
                [-0.150, 0.100, -0.250],
                [0.150, -0.100, -0.300],
                [-0.150, 0.100, -0.550],
                [0.150, -0.100, -0.600],
                [0.000, 0.000, -0.800],
                [-0.100, 0.100, -1.050],
                [0.000, 0.000, -1.300],
            ],
            dtype=np.float64,
        ),
    }
}


def _resolve_gro_path(lipid_name: str, gro_dir: str) -> Path:
    """
    在给定目录中解析脂质模板 .gro 文件路径。

    查找顺序：
    1. <name>-em.gro
    2. <name>.gro
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
    使用固定列宽解析 .gro 中的珠子名和坐标。

    注意：必须使用切片，不使用 split()，避免对齐变化引起歧义。
    - atom name: line[10:15]
    - x:         line[20:28]
    - y:         line[28:36]
    - z:         line[36:44]
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
                f"第 {line_idx} 条原子记录坐标解析失败（固定列宽模式）: {gro_path}"
            ) from exc

        bead_names.append(bead_name)
        coords_list.append([x, y, z])

    return bead_names, np.asarray(coords_list, dtype=np.float64)


def _find_anchor_indices(
    bead_names: List[str],
    anchors: List[str],
    lipid_name: str,
    anchor_group_name: str,
) -> List[int]:
    """
    在珠子名列表中查找锚点索引；缺失锚点时立即抛错（fail fast）。
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
    根据 LipidBlueprint 构建标准化的 Lipid3D。

    核心步骤：
    1. 读取原始构象（CHOL 用硬编码，其余用 .gro）。
    2. 根据锚点求 head_center 与 tail_center。
    3. 全体坐标平移：coords -= head_center（头部中心归一到原点）。
    4. 方向向量归一化：vector = (tail_center - head_center) / ||...||。
    """
    if blueprint.name in HARDCODED_CONFORMERS:
        conformer = HARDCODED_CONFORMERS[blueprint.name]
        bead_names = list(conformer["bead_names"])
        # 复制一份，避免后续平移污染全局硬编码常量。
        coords = np.array(conformer["coords"], dtype=np.float64, copy=True)
    else:
        gro_path = _resolve_gro_path(blueprint.name, gro_dir)
        bead_names, coords = _parse_gro_coordinates(gro_path)

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

    head_center = np.mean(coords[head_indices], axis=0)
    tail_center = np.mean(coords[tail_indices], axis=0)

    shifted_coords = coords - head_center

    direction = tail_center - head_center
    norm = np.linalg.norm(direction)
    if norm < 1e-12:
        raise ValueError(
            f"脂质 {blueprint.name} 的头尾中心几乎重合，无法定义稳定方向向量。"
        )

    vector = direction / norm

    return Lipid3D(
        blueprint=blueprint,
        bead_names=bead_names,
        coords=shifted_coords,
        vector=vector,
    )


__all__ = [
    "LipidBlueprint",
    "Lipid3D",
    "LIPID_LIBRARY",
    "HARDCODED_CONFORMERS",
    "build_lipid_3d",
]
