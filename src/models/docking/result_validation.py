from __future__ import annotations

from math import isfinite
from pathlib import Path
import json

from src.interfaces.contracts import DockingResult


#校验 pose 文件/分数合法性，输出摘要统计，并可写 JSON summary
def validate_docking_result(
    docking_result: DockingResult,
    require_pose_files: bool = True,
) -> None:
    """Validate docking result consistency and reproducibility-critical fields."""
    if not docking_result.poses:
        raise ValueError("DockingResult.poses is empty")

    seen_ids: set[int] = set()
    for pose in docking_result.poses:
        if pose.pose_id in seen_ids:
            raise ValueError(f"Duplicate pose_id detected: {pose.pose_id}")
        seen_ids.add(pose.pose_id)

        if not isfinite(pose.score):
            raise ValueError(f"Non-finite docking score for pose_id={pose.pose_id}")

        if require_pose_files:
            if pose.pose_file is None:
                raise ValueError(f"Missing pose_file for pose_id={pose.pose_id}")
            if not pose.pose_file.exists():
                raise FileNotFoundError(f"pose_file not found: {pose.pose_file}")
            if pose.pose_file.stat().st_size <= 0:
                raise ValueError(f"pose_file is empty: {pose.pose_file}")

    if docking_result.ranked_pose_table is not None:
        if not docking_result.ranked_pose_table.exists():
            raise FileNotFoundError(
                f"ranked_pose_table not found: {docking_result.ranked_pose_table}"
            )
        if docking_result.ranked_pose_table.stat().st_size <= 0:
            raise ValueError(
                f"ranked_pose_table is empty: {docking_result.ranked_pose_table}"
            )


def summarize_docking_result(docking_result: DockingResult) -> dict[str, float | int]:
    """Return compact summary statistics for downstream reports."""
    validate_docking_result(docking_result, require_pose_files=False)

    scores = [pose.score for pose in docking_result.poses]
    sorted_scores = sorted(scores)
    n = len(sorted_scores)
    median = (
        sorted_scores[n // 2]
        if n % 2 == 1
        else 0.5 * (sorted_scores[n // 2 - 1] + sorted_scores[n // 2])
    )
    return {
        "num_poses": n,
        "best_score": sorted_scores[0],
        "worst_score": sorted_scores[-1],
        "median_score": median,
    }


def write_docking_summary_json(
    docking_result: DockingResult,
    output_path: Path,
) -> Path:
    """Write machine-readable docking summary JSON for reproducibility logs."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": summarize_docking_result(docking_result),
        "selected_pose_id": docking_result.selected_pose.pose_id if docking_result.selected_pose else None,
        "ranked_pose_table": str(docking_result.ranked_pose_table) if docking_result.ranked_pose_table else None,
        "poses": [
            {
                "pose_id": pose.pose_id,
                "score": pose.score,
                "rmsd": pose.rmsd,
                "pose_file": str(pose.pose_file) if pose.pose_file else None,
                "metadata": pose.metadata,
            }
            for pose in docking_result.poses
        ],
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path
