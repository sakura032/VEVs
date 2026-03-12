from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
import json

from src.configs import ProjectPaths
from src.interfaces.contracts import InputManifest, StructureRepositoryProtocol


class StructureRepository(StructureRepositoryProtocol):
    """Input file validation and manifest export for Route A workflow."""

    def __init__(self, paths: ProjectPaths):
        self.paths = paths
        self.paths.ensure_dirs()

    def validate_input_files(self, manifest: InputManifest) -> None:
        self._validate_path(manifest.receptor_path, role="receptor")
        self._validate_path(manifest.ligand_path, role="ligand")
        if manifest.membrane_template_path is not None:
            self._validate_path(manifest.membrane_template_path, role="membrane_template")

    def export_manifest(self, manifest: InputManifest, output_path: Path | None = None) -> Path:
        """Write a provenance-friendly manifest JSON for reproducibility."""
        self.validate_input_files(manifest)

        out = output_path or (self.paths.output_dir / "metadata" / "input_manifest.json")
        out.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "manifest": {
                "receptor_path": str(manifest.receptor_path.resolve()),
                "ligand_path": str(manifest.ligand_path.resolve()),
                "membrane_template_path": (
                    str(manifest.membrane_template_path.resolve())
                    if manifest.membrane_template_path is not None
                    else None
                ),
                "metadata": manifest.metadata,
            },
            "files": {
                "receptor": self._file_record(manifest.receptor_path),
                "ligand": self._file_record(manifest.ligand_path),
                "membrane_template": (
                    self._file_record(manifest.membrane_template_path)
                    if manifest.membrane_template_path is not None
                    else None
                ),
            },
        }

        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return out

    def _validate_path(self, path: Path, role: str) -> None:
        if not path.exists():
            raise FileNotFoundError(f"{role} file not found: {path}")
        if not path.is_file():
            raise ValueError(f"{role} path is not a file: {path}")
        ext = path.suffix.lower()
        if role in {"receptor", "ligand"} and ext != ".pdb":
            raise ValueError(
                f"{role} currently supports only .pdb in minimum Route A, got: {path.name}"
            )
        if role == "membrane_template" and ext not in {".pdb", ".cif"}:
            raise ValueError(f"Unsupported membrane template format: {path.name}")

    def _file_record(self, path: Path) -> dict[str, str | int]:
        digest = sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        stat = path.stat()
        return {
            "path": str(path.resolve()),
            "size_bytes": stat.st_size,
            "sha256": digest.hexdigest(),
            "mtime_epoch": int(stat.st_mtime),
        }

