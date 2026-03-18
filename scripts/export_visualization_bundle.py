"""
export_visualization_bundle.py

Create symlink-only visualization bundles for frontend consumption.

Storage contract:
1. Bundle root is `frontend/visualization/<run_id>/`.
2. Raw artifacts in `work/` and `outputs/` are linked, never copied.
3. `sampled_frames.json` and referenced frame PDB files are linked when present.
4. Derived lightweight metadata is generated under `derived/`.
5. `frontend/public/visualization/` is cleaned (no run data kept there).
6. `frontend/visualization/index.json` is maintained for run discovery.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VIS_ROOT = PROJECT_ROOT / "frontend" / "visualization"
PUBLIC_VIS_ROOT = PROJECT_ROOT / "frontend" / "public" / "visualization"
WATER_RESIDUES = {"HOH", "WAT", "TIP3"}
REQUIRED_BUNDLE_RELATIVE_PATHS = (
    "work/preprocessed/receptor_clean.pdb",
    "work/assembled/complex_initial.pdb",
    "outputs/docking/poses.csv",
    "outputs/metadata/run_manifest.json",
)


@dataclass(frozen=True)
class BundlePaths:
    run_id: str
    work_run_dir: Path
    outputs_run_dir: Path
    bundle_dir: Path
    work_link: Path
    outputs_link: Path
    sampled_frames_link: Path
    frame_pdb_dir: Path
    derived_dir: Path
    structure_roles_path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create symlink-only visualization bundle for one run_id."
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Run identifier under work/runs/<run_id> and outputs/runs/<run_id>.",
    )
    return parser.parse_args()


def build_paths(run_id: str) -> BundlePaths:
    run_id = run_id.strip()
    if not run_id or "/" in run_id or "\\" in run_id or ".." in run_id:
        raise ValueError(f"unsafe run_id: {run_id}")
    work_run_dir = PROJECT_ROOT / "work" / "runs" / run_id
    outputs_run_dir = PROJECT_ROOT / "outputs" / "runs" / run_id
    bundle_dir = VIS_ROOT / run_id
    return BundlePaths(
        run_id=run_id,
        work_run_dir=work_run_dir,
        outputs_run_dir=outputs_run_dir,
        bundle_dir=bundle_dir,
        work_link=bundle_dir / "work",
        outputs_link=bundle_dir / "outputs",
        sampled_frames_link=bundle_dir / "sampled_frames.json",
        frame_pdb_dir=bundle_dir / "frame_pdb",
        derived_dir=bundle_dir / "derived",
        structure_roles_path=bundle_dir / "derived" / "structure_roles.json",
    )


def ensure_run_exists(paths: BundlePaths) -> None:
    if not paths.work_run_dir.exists():
        raise FileNotFoundError(f"Run work dir not found: {paths.work_run_dir}")
    if not paths.outputs_run_dir.exists():
        raise FileNotFoundError(f"Run output dir not found: {paths.outputs_run_dir}")


def remove_path(path: Path) -> None:
    path_text = str(path)
    try:
        path_exists = os.path.lexists(path_text)
    except OSError:
        path_exists = False
    if not path_exists:
        return
    try:
        if path.is_symlink() or path.is_file():
            path.unlink()
            return
        if path.is_dir():
            shutil.rmtree(path)
            return
        path.unlink()
        return
    except OSError as exc:
        if os.name == "nt":
            # Handle broken Windows reparse points (for example stale junctions).
            rmdir_result = subprocess.run(
                ["cmd", "/c", "rmdir", "/s", "/q", path_text],
                capture_output=True,
                text=True,
                check=False,
            )
            if rmdir_result.returncode == 0:
                return
            del_result = subprocess.run(
                ["cmd", "/c", "del", "/f", "/q", path_text],
                capture_output=True,
                text=True,
                check=False,
            )
            if del_result.returncode == 0:
                return
            raise RuntimeError(
                f"Failed to remove Windows reparse path: {path_text}\n"
                f"rmdir stderr={rmdir_result.stderr}\n"
                f"del stderr={del_result.stderr}"
            ) from exc
        raise


def build_preferred_link_target(link_path: Path, target_path: Path) -> Path:
    target_abs = target_path.resolve()
    link_parent_abs = link_path.parent.resolve()
    try:
        relative = os.path.relpath(target_abs, start=link_parent_abs)
        if relative and relative != ".":
            return Path(relative)
    except ValueError:
        # Different drives on Windows may not support relative paths.
        pass
    return target_abs


def create_windows_junction(link_path: Path, target_spec: Path) -> None:
    command = f'mklink /J "{link_path}" "{target_spec}"'
    result = subprocess.run(
        ["cmd", "/c", command], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to create junction: {command}\nstdout={result.stdout}\nstderr={result.stderr}"
        )


def create_directory_link(link_path: Path, target_path: Path) -> str:
    target_abs = target_path.resolve()
    link_target = build_preferred_link_target(link_path, target_abs)
    remove_path(link_path)
    try:
        os.symlink(link_target, link_path, target_is_directory=True)
        return "symlink-relative" if not link_target.is_absolute() else "symlink-absolute"
    except OSError as exc:
        if os.name == "nt":
            create_windows_junction(link_path, link_target)
            return "junction-relative" if not link_target.is_absolute() else "junction-absolute"
        raise RuntimeError(
            f"Failed to create directory symlink {link_path} -> {link_target}"
        ) from exc


def create_file_link(link_path: Path, target_path: Path) -> str:
    target_abs = target_path.resolve()
    link_target = build_preferred_link_target(link_path, target_abs)
    remove_path(link_path)
    try:
        os.symlink(link_target, link_path)
        return "symlink-relative" if not link_target.is_absolute() else "symlink-absolute"
    except OSError as exc:
        if os.name == "nt":
            # Hardlink fallback uses absolute target and still stays platform-resolvable.
            os.link(target_abs, link_path)
            return "hardlink"
        raise RuntimeError(
            f"Failed to create file symlink {link_path} -> {link_target}"
        ) from exc


def resolve_sampled_frames_source(paths: BundlePaths) -> Path | None:
    candidates = [
        paths.work_run_dir / "md" / "sampled_frames.json",
        paths.outputs_run_dir / "analysis" / "binding" / "sampled_frames.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def parse_atom_record_key(line: str) -> tuple[str, bool] | None:
    if not (line.startswith("ATOM") or line.startswith("HETATM")):
        return None
    serial = line[6:11].strip() or "0"
    atom_name = line[12:16].strip() or "UNK"
    residue = line[17:20].strip() or "UNK"
    chain_id = line[21:22].strip() or "_"
    residue_id = line[22:26].strip() or "0"
    atom_key = f"{serial}|{chain_id}|{residue_id}|{residue}|{atom_name}"
    is_water = residue in WATER_RESIDUES
    return atom_key, is_water


def parse_pdb_atom_keys(path: Path) -> tuple[set[str], set[str]]:
    all_keys: set[str] = set()
    water_keys: set[str] = set()
    if not path.exists():
        return all_keys, water_keys
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        payload = parse_atom_record_key(line)
        if payload is None:
            continue
        atom_key, is_water = payload
        all_keys.add(atom_key)
        if is_water:
            water_keys.add(atom_key)
    return all_keys, water_keys


def resolve_structure_role_payload(paths: BundlePaths) -> dict[str, Any]:
    receptor_rel = "work/preprocessed/receptor_clean.pdb"
    ligand_rel = "work/preprocessed/ligand_prepared.pdb"
    receptor_path = paths.work_run_dir / "preprocessed" / "receptor_clean.pdb"
    ligand_path = paths.work_run_dir / "preprocessed" / "ligand_prepared.pdb"

    receptor_keys, receptor_water = parse_pdb_atom_keys(receptor_path)
    ligand_keys, ligand_water = parse_pdb_atom_keys(ligand_path)
    receptor_non_water = receptor_keys - receptor_water
    ligand_non_water = ligand_keys - ligand_water

    atom_roles: dict[str, str] = {}
    resolution_notes: list[str] = []

    for key in sorted(receptor_water | ligand_water):
        atom_roles[key] = "water"

    receptor_only = receptor_non_water - ligand_non_water
    ligand_only = ligand_non_water - receptor_non_water
    overlap = receptor_non_water & ligand_non_water

    for key in sorted(receptor_only):
        atom_roles[key] = "receptor"
    for key in sorted(ligand_only):
        atom_roles[key] = "ligand"
    for key in sorted(overlap):
        atom_roles[key] = "unresolved"

    receptor_exists = receptor_path.exists()
    ligand_exists = ligand_path.exists()
    if not receptor_exists or not ligand_exists:
        missing = []
        if not receptor_exists:
            missing.append(receptor_rel)
        if not ligand_exists:
            missing.append(ligand_rel)
        resolution_status = "missing"
        resolution_notes.append(
            "Missing input file(s): " + ", ".join(missing)
        )
    elif len(receptor_keys) == 0 and len(ligand_keys) == 0:
        resolution_status = "missing"
        resolution_notes.append("Both receptor and ligand files contain zero atom records.")
    else:
        union_size = len(receptor_non_water | ligand_non_water) or 1
        smaller_size = min(
            max(len(receptor_non_water), 1),
            max(len(ligand_non_water), 1),
        )
        overlap_ratio_union = len(overlap) / union_size
        overlap_ratio_smaller = len(overlap) / smaller_size
        if (
            len(overlap) > 0
            and (overlap_ratio_union >= 0.60 or overlap_ratio_smaller >= 0.80)
        ):
            resolution_status = "ambiguous"
            resolution_notes.append(
                "Receptor and ligand atom keys are highly overlapping; conflicted keys marked as unresolved."
            )
        else:
            resolution_status = "resolved"
            resolution_notes.append(
                "Receptor and ligand atom keys are sufficiently separable for role mapping."
            )

    resolution_notes.append(
        "counts: "
        f"receptor_keys={len(receptor_non_water)}, "
        f"ligand_keys={len(ligand_non_water)}, "
        f"overlap={len(overlap)}, "
        f"water_keys={len(receptor_water | ligand_water)}"
    )

    return {
        "run_id": paths.run_id,
        "resolution_status": resolution_status,
        "resolution_notes": resolution_notes,
        "source": {
            "receptor_file": receptor_rel,
            "ligand_file": ligand_rel,
            "method": "atom_key_overlap_from_preprocessed_structures",
        },
        "atom_roles": atom_roles,
    }


def write_structure_role_payload(paths: BundlePaths) -> dict[str, Any]:
    paths.derived_dir.mkdir(parents=True, exist_ok=True)
    payload = resolve_structure_role_payload(paths)
    paths.structure_roles_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def resolve_frame_pdb_source(sampled_source: Path, frame_obj: dict[str, Any]) -> Path | None:
    for key in ("pdb_file", "frame_pdb", "pdb_path"):
        raw_value = frame_obj.get(key)
        if not isinstance(raw_value, str) or not raw_value.strip():
            continue
        raw_path = Path(raw_value.strip())
        if raw_path.is_absolute() and raw_path.exists():
            return raw_path
        candidate_from_json = (sampled_source.parent / raw_path).resolve()
        if candidate_from_json.exists():
            return candidate_from_json
        candidate_from_project = (PROJECT_ROOT / raw_path).resolve()
        if candidate_from_project.exists():
            return candidate_from_project
    return None


def link_sampled_frames_and_frame_pdb(paths: BundlePaths) -> tuple[bool, int]:
    sampled_source = resolve_sampled_frames_source(paths)
    remove_path(paths.sampled_frames_link)
    remove_path(paths.frame_pdb_dir)
    if sampled_source is None:
        return False, 0

    create_file_link(paths.sampled_frames_link, sampled_source)

    payload = json.loads(sampled_source.read_text(encoding="utf-8"))
    frames = payload.get("frames") if isinstance(payload, dict) else None
    if not isinstance(frames, list):
        return True, 0

    paths.frame_pdb_dir.mkdir(parents=True, exist_ok=True)
    linked_count = 0
    linked_sources: set[Path] = set()
    for frame_obj in frames:
        if not isinstance(frame_obj, dict):
            continue
        source_pdb = resolve_frame_pdb_source(sampled_source, frame_obj)
        if source_pdb is None or source_pdb in linked_sources:
            continue
        linked_sources.add(source_pdb)
        frame_index = frame_obj.get("frame_index")
        if isinstance(frame_index, (int, float)):
            link_name = f"frame_{int(frame_index):04d}.pdb"
        else:
            link_name = source_pdb.name
        create_file_link(paths.frame_pdb_dir / link_name, source_pdb)
        linked_count += 1
    return True, linked_count


def read_existing_index(index_path: Path) -> dict[str, str]:
    if not index_path.exists():
        return {}
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    runs = payload.get("runs")
    if not isinstance(runs, list):
        return {}
    mapping: dict[str, str] = {}
    for entry in runs:
        if isinstance(entry, dict) and isinstance(entry.get("run_id"), str):
            mapping[entry["run_id"]] = str(entry.get("updated_at") or "")
    return mapping


def update_run_index(current_run_id: str) -> None:
    VIS_ROOT.mkdir(parents=True, exist_ok=True)
    index_path = VIS_ROOT / "index.json"
    previous_updated = read_existing_index(index_path)
    run_ids = sorted([child.name for child in VIS_ROOT.iterdir() if child.is_dir()])
    now_iso = datetime.now(timezone.utc).isoformat()
    entries: list[dict[str, str]] = []
    for run_id in run_ids:
        if run_id == current_run_id:
            updated_at = now_iso
        else:
            updated_at = previous_updated.get(run_id) or datetime.fromtimestamp(
                (VIS_ROOT / run_id).stat().st_mtime, tz=timezone.utc
            ).isoformat()
        entries.append({"run_id": run_id, "updated_at": updated_at})
    index_path.write_text(
        json.dumps({"runs": entries}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def clean_public_visualization() -> int:
    if not PUBLIC_VIS_ROOT.exists():
        PUBLIC_VIS_ROOT.mkdir(parents=True, exist_ok=True)
        return 0
    removed = 0
    for child in list(PUBLIC_VIS_ROOT.iterdir()):
        if child.name == ".gitkeep":
            continue
        remove_path(child)
        removed += 1
    return removed


def validate_bundle_access(paths: BundlePaths) -> None:
    missing: list[str] = []
    for relative_path in REQUIRED_BUNDLE_RELATIVE_PATHS:
        candidate = paths.bundle_dir / relative_path
        if not candidate.exists():
            missing.append(relative_path)

    if missing:
        details = "\n".join(f"- {item}" for item in missing)
        raise RuntimeError(
            "Bundle exported but required files are not reachable via "
            "frontend/visualization links. This usually indicates cross-platform "
            "link target mismatch.\n"
            f"run_id: {paths.run_id}\n"
            f"bundle_dir: {paths.bundle_dir}\n"
            f"missing relative paths:\n{details}"
        )


def create_bundle(paths: BundlePaths) -> None:
    ensure_run_exists(paths)
    VIS_ROOT.mkdir(parents=True, exist_ok=True)
    paths.bundle_dir.mkdir(parents=True, exist_ok=True)

    removed_public_items = clean_public_visualization()
    work_link_kind = create_directory_link(paths.work_link, paths.work_run_dir)
    outputs_link_kind = create_directory_link(paths.outputs_link, paths.outputs_run_dir)
    sampled_exists, frame_pdb_count = link_sampled_frames_and_frame_pdb(paths)
    role_payload = write_structure_role_payload(paths)
    validate_bundle_access(paths)
    update_run_index(paths.run_id)

    print("Visualization bundle exported successfully.")
    print(f"- run_id: {paths.run_id}")
    print(f"- bundle_dir: {paths.bundle_dir}")
    print(f"- work link: {paths.work_link} ({work_link_kind})")
    print(f"- outputs link: {paths.outputs_link} ({outputs_link_kind})")
    print(f"- sampled_frames link: {sampled_exists}")
    print(f"- frame_pdb links: {frame_pdb_count}")
    print(f"- structure_roles path: {paths.structure_roles_path}")
    print(f"- structure_roles status: {role_payload['resolution_status']}")
    print(f"- cleaned frontend/public/visualization items: {removed_public_items}")


def main() -> None:
    args = parse_args()
    paths = build_paths(args.run_id)
    create_bundle(paths)


if __name__ == "__main__":
    main()
