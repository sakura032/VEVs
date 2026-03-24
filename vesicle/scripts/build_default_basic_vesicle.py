"""
vesicle.scripts.build_default_basic_vesicle
==========================================

默认基础囊泡的一键构建入口。

推荐直接运行：
    python -m vesicle.scripts.build_default_basic_vesicle

默认行为：
1. 生成默认 45 蛋白三岛输入。
2. 构建基础囊泡。
3. 写出 `vesicle/outputs/basic_vesicle/vesicle.gro` 与 `topol.top`。
4. 自动把这对产物同步到 `frontend/visualization/vesicle/basic_vesicle/`，
   并更新 `frontend/visualization/vesicle/index.json`，
   供前端 Whole Vesicle Explorer 直接读取。
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path
from typing import Dict

import numpy as np

from vesicle.models.vesicle_builder import VesicleBuilder
from vesicle.scripts.sync_vesicle_to_frontend import (
    DEFAULT_VISUALIZATION_ROOT as DEFAULT_FRONTEND_VISUALIZATION_ROOT,
)
from vesicle.scripts.sync_vesicle_to_frontend import sync_vesicle_to_frontend

DEFAULT_HELPER_CLUSTER_MAX_ANGLE = 0.60
DEFAULT_HELPER_PLACEMENT_TRIES = 200
DEFAULT_HELPER_RANDOM_SEED = 11
OUTPUTS_ROOT = Path("vesicle/outputs")


def _resolve_output_root(output_dir: str | Path | None) -> Path:
    if output_dir is None:
        return Path(VesicleBuilder.DEFAULT_OUTPUT_DIR)
    return Path(output_dir)


def _derive_dataset_name_for_sync(output_root: Path) -> str:
    outputs_root = OUTPUTS_ROOT.resolve()
    output_root_resolved = output_root.resolve()
    if output_root_resolved.parent != outputs_root:
        warning_message = (
            "自动同步只支持 `vesicle/outputs/<dataset_name>/` 这一层级的输出目录；"
            f"当前收到: {output_root.as_posix()}"
        )
        warnings.warn(warning_message, stacklevel=3)
        raise ValueError(warning_message)
    return output_root_resolved.name


def build_default_basic_vesicle(
    output_dir: str | Path | None = None,
    protein_dir: str | Path = "vesicle/data/proteins",
    builder_kwargs: Dict[str, float] | None = None,
    seed: int | None = DEFAULT_HELPER_RANDOM_SEED,
    sync_frontend: bool = True,
    frontend_visualization_root: str | Path = DEFAULT_FRONTEND_VISUALIZATION_ROOT,
) -> VesicleBuilder:
    """
    用项目约定的默认参数，直接生成一套可用的基础囊泡体系。

    这是给“先快速得到一个标准化基础囊泡”准备的高层入口。它会自动：
    1. 生成默认 45 蛋白三岛输入；
    2. 组装囊泡；
    3. 写出 `vesicle.gro` / `topol.top`；
    4. 可选地把这对输出同步到前端可视化目录。

    这里额外施加了一层高层入口专用的稳健性设置：
    - 把岛内局部扰动上限放宽到 `0.60 rad`
    - 把蛋白落位最大尝试次数提升到 `200`
    - 默认固定随机种子为 `11`

    自动同步时，输出目录必须位于 `vesicle/outputs/<dataset_name>/` 下；
    否则会先给出警告，再报错退出，避免前端数据集命名失控。
    """
    output_root = _resolve_output_root(output_dir)
    if sync_frontend:
        _derive_dataset_name_for_sync(output_root)

    if seed is not None:
        np.random.seed(int(seed))

    builder = VesicleBuilder(**(dict(builder_kwargs) if builder_kwargs is not None else {}))
    builder.PROTEIN_CLUSTER_MAX_ANGLE = DEFAULT_HELPER_CLUSTER_MAX_ANGLE
    builder.PROTEIN_PLACEMENT_MAX_TRIES = max(
        int(builder.PROTEIN_PLACEMENT_MAX_TRIES),
        DEFAULT_HELPER_PLACEMENT_TRIES,
    )
    cluster_assignments = VesicleBuilder.make_protein_clusters(protein_dir)
    builder.build(cluster_assignments)

    builder.write_outputs(
        output_root / builder.DEFAULT_GRO_NAME,
        output_root / builder.DEFAULT_TOP_NAME,
    )

    if sync_frontend:
        sync_vesicle_to_frontend(
            source_dir=output_root,
            visualization_root=frontend_visualization_root,
        )

    return builder


def _build_arg_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""
    parser = argparse.ArgumentParser(description="生成默认基础囊泡体系并写出 gro/top 文件。")
    parser.add_argument(
        "--output-dir",
        default=str(VesicleBuilder.DEFAULT_OUTPUT_DIR),
        help="输出目录，默认写到 vesicle/outputs/basic_vesicle/。",
    )
    parser.add_argument(
        "--protein-dir",
        default="vesicle/data/proteins",
        help="蛋白模板目录，默认使用 vesicle/data/proteins/。",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_HELPER_RANDOM_SEED,
        help="随机种子。默认固定为 11，保证该高层入口可复现。",
    )
    parser.add_argument("--radius-out", type=float, default=50.0, help="外叶目标半径，单位 nm。")
    parser.add_argument("--thickness", type=float, default=4.0, help="膜厚，单位 nm。")
    parser.add_argument(
        "--lipid-exclusion-radius",
        type=float,
        default=0.8,
        help="脂质头部对蛋白 bead 的排斥半径，单位 nm。",
    )
    parser.add_argument(
        "--lipid-area",
        type=float,
        default=0.65,
        help="估算脂质总数时使用的平均单分子面积，单位 nm^2。",
    )
    parser.add_argument(
        "--no-sync-frontend",
        action="store_true",
        help="只写出到 vesicle/outputs，不自动同步到 frontend/visualization/vesicle/。",
    )
    return parser


def main() -> None:
    """命令行主入口。"""
    parser = _build_arg_parser()
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    try:
        build_default_basic_vesicle(
            output_dir=output_dir,
            protein_dir=args.protein_dir,
            seed=args.seed,
            sync_frontend=not args.no_sync_frontend,
            builder_kwargs={
                "radius_out": args.radius_out,
                "thickness": args.thickness,
                "lipid_exclusion_radius": args.lipid_exclusion_radius,
                "lipid_area": args.lipid_area,
            },
        )
    except ValueError as exc:
        parser.exit(2, f"error: {exc}\n")

    print(f"已生成: {(output_dir / VesicleBuilder.DEFAULT_GRO_NAME).as_posix()}")
    print(f"已生成: {(output_dir / VesicleBuilder.DEFAULT_TOP_NAME).as_posix()}")
    if not args.no_sync_frontend:
        print(f"已同步到: {(Path(DEFAULT_FRONTEND_VISUALIZATION_ROOT) / output_dir.name).as_posix()}")


if __name__ == "__main__":
    main()
