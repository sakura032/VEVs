"""
vesicle.scripts.sync_vesicle_to_frontend
========================================

把 `vesicle/outputs/<dataset_name>/` 下的一套囊泡产物同步到
`frontend/visualization/vesicle/<dataset_name>/`，并维护前端用的索引清单。

推荐直接运行：
    python -m vesicle.scripts.sync_vesicle_to_frontend

默认行为：
1. 从 `vesicle/outputs/basic_vesicle/` 读取 `vesicle.gro` / `topol.top`
2. 同步到 `frontend/visualization/vesicle/basic_vesicle/`
3. 更新 `frontend/visualization/vesicle/index.json`
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SOURCE_DIR = Path("vesicle/outputs/basic_vesicle")
DEFAULT_VISUALIZATION_ROOT = Path("frontend/visualization/vesicle")
DEFAULT_STRUCTURE_FILE = "vesicle.gro"
DEFAULT_TOPOLOGY_FILE = "topol.top"
DEFAULT_INDEX_FILE = "index.json"


def _read_index(index_path: Path) -> list[dict[str, Any]]:
    if not index_path.exists():
        return []
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    datasets = payload.get("datasets", [])
    if not isinstance(datasets, list):
        raise ValueError(f"invalid vesicle index payload: {index_path}")
    return [entry for entry in datasets if isinstance(entry, dict)]


def _write_index(index_path: Path, datasets: list[dict[str, Any]]) -> None:
    ordered = sorted(
        datasets,
        key=lambda entry: entry.get("updated_at", ""),
        reverse=True,
    )
    index_path.write_text(
        json.dumps({"datasets": ordered}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def sync_vesicle_to_frontend(
    source_dir: str | Path = DEFAULT_SOURCE_DIR,
    visualization_root: str | Path = DEFAULT_VISUALIZATION_ROOT,
) -> Path:
    """
    把一套囊泡输出同步到前端可视化目录。

    约定：
    - 数据集名直接取 `source_dir` 的目录名
    - 前端可视化目录固定为 `frontend/visualization/vesicle/<dataset_name>/`
    - 同步后会更新 `frontend/visualization/vesicle/index.json`
    """
    source_root = Path(source_dir)
    dataset_id = source_root.name
    if not dataset_id:
        raise ValueError(f"cannot derive dataset name from source_dir: {source_root}")

    structure_path = source_root / DEFAULT_STRUCTURE_FILE
    topology_path = source_root / DEFAULT_TOPOLOGY_FILE
    if not structure_path.exists():
        raise FileNotFoundError(f"missing source GRO: {structure_path}")
    if not topology_path.exists():
        raise FileNotFoundError(f"missing source topology: {topology_path}")

    visualization_root_path = Path(visualization_root)
    target_root = visualization_root_path / dataset_id
    target_root.mkdir(parents=True, exist_ok=True)

    shutil.copy2(structure_path, target_root / DEFAULT_STRUCTURE_FILE)
    shutil.copy2(topology_path, target_root / DEFAULT_TOPOLOGY_FILE)

    meta = {
        "dataset_id": dataset_id,
        "label": dataset_id,
        "structure_url": f"/visualization/vesicle/{dataset_id}/{DEFAULT_STRUCTURE_FILE}",
        "topology_url": f"/visualization/vesicle/{dataset_id}/{DEFAULT_TOPOLOGY_FILE}",
    }
    (target_root / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    index_path = visualization_root_path / DEFAULT_INDEX_FILE
    updated_at = datetime.now(timezone.utc).isoformat()
    datasets = [entry for entry in _read_index(index_path) if entry.get("dataset_id") != dataset_id]
    datasets.append(
        {
            **meta,
            "updated_at": updated_at,
        }
    )
    visualization_root_path.mkdir(parents=True, exist_ok=True)
    _write_index(index_path, datasets)

    return target_root


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="同步一套囊泡输出到前端可视化目录。")
    parser.add_argument(
        "--source-dir",
        default=str(DEFAULT_SOURCE_DIR),
        help="源输出目录，默认使用 vesicle/outputs/basic_vesicle/。",
    )
    parser.add_argument(
        "--visualization-root",
        default=str(DEFAULT_VISUALIZATION_ROOT),
        help="前端囊泡可视化根目录，默认使用 frontend/visualization/vesicle/。",
    )
    return parser


def main() -> None:
    """命令行入口。"""
    parser = _build_arg_parser()
    args = parser.parse_args()
    target_dir = sync_vesicle_to_frontend(
        source_dir=args.source_dir,
        visualization_root=args.visualization_root,
    )
    print(f"已同步到: {target_dir.as_posix()}")


if __name__ == "__main__":
    main()
