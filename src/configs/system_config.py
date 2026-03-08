from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class ProjectPaths:
    """项目路径配置（project paths）。

    作用：
    1. 统一管理原始输入、工作目录、输出目录。
    2. 避免在 workflow 或 runner 中硬编码路径。
    3. 为 route A / route B / umbrella sampling 提供一致的目录约定。
    """

    project_root: Path
    data_dir: Path
    work_dir: Path
    output_dir: Path
    log_dir: Path
    report_dir: Path

    @classmethod
    def from_root(cls, project_root: str | Path) -> "ProjectPaths":
        root = Path(project_root).resolve()
        data_dir = root / "data"
        work_dir = root / "work"
        output_dir = root / "outputs"
        log_dir = output_dir / "logs"
        report_dir = output_dir / "reports"
        return cls(
            project_root=root,
            data_dir=data_dir,
            work_dir=work_dir,
            output_dir=output_dir,
            log_dir=log_dir,
            report_dir=report_dir,
        )

    def ensure_dirs(self) -> None:
        for path in [self.data_dir, self.work_dir, self.output_dir, self.log_dir, self.report_dir]:
            path.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class SystemConfig:
    """体系配置（system-level configuration）。

    这是 route A / route B 共用的上位配置。
    它不关心具体 workflow，只定义“我们要模拟什么样的物理体系”。
    """

    receptor_path: Path
    ligand_path: Path
    forcefield_name: str = "amber14sb"
    water_model: str = "tip3p"
    temperature_kelvin: float = 300.0
    pressure_bar: float = 1.0
    ionic_strength_molar: float = 0.15
    ph: float = 7.4
    has_membrane: bool = False
    membrane_template_path: Optional[Path] = None
    metadata: dict[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.receptor_path.exists():
            raise FileNotFoundError(f"Receptor file not found: {self.receptor_path}")
        if not self.ligand_path.exists():
            raise FileNotFoundError(f"Ligand file not found: {self.ligand_path}")
        if self.has_membrane and self.membrane_template_path is not None:
            if not self.membrane_template_path.exists():
                raise FileNotFoundError(
                    f"Membrane template not found: {self.membrane_template_path}"
                )
        if self.temperature_kelvin <= 0:
            raise ValueError("temperature_kelvin must be positive")
        if self.pressure_bar <= 0:
            raise ValueError("pressure_bar must be positive")
        if self.ionic_strength_molar < 0:
            raise ValueError("ionic_strength_molar cannot be negative")
