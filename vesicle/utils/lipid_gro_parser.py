"""
兼容层：历史模块 `lipid_gro_parser.py`。

说明：
- 新实现已经迁移到 `vesicle.utils.lipid_factory`。
- 这里保留最小转发能力，避免旧导入路径立刻报错。
- 新代码请直接使用 `build_lipid_3d`。
"""

from pathlib import Path
from typing import Dict
import warnings

from vesicle.models.coarse_grained.lipid import LIPID_LIBRARY, Lipid3D, LipidBlueprint
from vesicle.utils.lipid_factory import build_lipid_3d


def parse_lipid_template(filepath: str, metadata: Dict) -> Lipid3D:
    """
    向后兼容旧接口。

    参数语义（兼容旧签名）：
    - filepath: 旧版传入的模板路径。新实现会取其父目录作为 `gro_dir`。
    - metadata: 至少应包含 `name`；其余字段优先从 `LIPID_LIBRARY` 读取。

    返回：
    - 新版 `Lipid3D` 实体。
    """
    warnings.warn(
        "`parse_lipid_template` 已弃用，请改用 `build_lipid_3d`。",
        DeprecationWarning,
        stacklevel=2,
    )

    name = metadata.get("name")
    if not name:
        raise ValueError("metadata 必须包含 `name` 字段。")

    if name in LIPID_LIBRARY:
        blueprint = LIPID_LIBRARY[name]
    else:
        raise ValueError(
            f"未知脂质 {name}。请在 LIPID_LIBRARY 中注册后再调用。"
        )

    gro_dir = str(Path(filepath).parent)
    return build_lipid_3d(blueprint=blueprint, gro_dir=gro_dir)


__all__ = ["parse_lipid_template", "build_lipid_3d", "LipidBlueprint", "Lipid3D"]
