from __future__ import annotations

from pathlib import Path
import json

from src.configs import ProjectPaths
from src.interfaces.contracts import InputManifest, PreparedStructures, StructurePreprocessorProtocol


class StructurePreprocessor(StructurePreprocessorProtocol):
    """Minimum Route A preprocessor based on PDBFixer + OpenMM PDB writer."""

    def __init__(self, paths: ProjectPaths, keep_water: bool = False):
        self.paths = paths
        self.keep_water = keep_water
        self.paths.ensure_dirs()

    def preprocess(self, manifest: InputManifest) -> PreparedStructures:
        prep_dir = self.paths.work_dir / "preprocessed"
        prep_dir.mkdir(parents=True, exist_ok=True)

        receptor_clean = prep_dir / "receptor_clean.pdb"
        ligand_prepared = prep_dir / "ligand_prepared.pdb"

        receptor_report = self._clean_pdb(
            input_path=manifest.receptor_path,
            output_path=receptor_clean,
        )
        ligand_report = self._clean_pdb(
            input_path=manifest.ligand_path,
            output_path=ligand_prepared,
        )

        report = {
            "receptor": receptor_report,
            "ligand": ligand_report,
            "keep_water": self.keep_water,
        }
        report_path = self.paths.output_dir / "metadata" / "preprocess_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        return PreparedStructures(
            receptor_clean=receptor_clean,
            ligand_prepared=ligand_prepared,
            preprocess_report=report_path,
        )

    def _clean_pdb(self, input_path: Path, output_path: Path) -> dict[str, str | int]:
        if input_path.suffix.lower() != ".pdb":
            raise ValueError(
                f"Minimum Route A preprocessor currently supports .pdb only: {input_path}"
            )
        if not input_path.exists():
            raise FileNotFoundError(f"Input PDB not found: {input_path}")

        try:
            from pdbfixer import PDBFixer
            from openmm import app
        except ImportError as exc:
            raise ImportError(
                "StructurePreprocessor requires pdbfixer and openmm in the execution environment."
            ) from exc

        fixer = PDBFixer(filename=str(input_path))
        fixer.removeHeterogens(keepWater=self.keep_water)
        fixer.findMissingResidues()
        fixer.findMissingAtoms()
        fixer.addMissingAtoms()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as handle:
            app.PDBFile.writeFile(fixer.topology, fixer.positions, handle)

        return {
            "input": str(input_path.resolve()),
            "output": str(output_path.resolve()),
            "num_missing_residues_groups": len(fixer.missingResidues),
            "num_missing_atoms_residues": len(fixer.missingAtoms),
            "num_missing_terminals_residues": len(fixer.missingTerminals),
        }

