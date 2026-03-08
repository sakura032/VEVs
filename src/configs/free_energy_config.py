from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(slots=True)
class EndpointFreeEnergyConfig:
    """端点自由能配置（endpoint free-energy configuration）。"""

    method: Literal["mmgbsa", "mmpbsa", "placeholder"] = "placeholder"
    frame_stride: int = 10
    start_frame: int = 0
    end_frame: Optional[int] = None
    dielectric_solute: float = 1.0
    dielectric_solvent: float = 78.5

    def validate(self) -> None:
        if self.frame_stride <= 0:
            raise ValueError("frame_stride must be positive")


@dataclass(slots=True)
class UmbrellaSamplingConfig:
    """伞形采样配置（umbrella sampling configuration）。"""

    cv_type: Literal["distance", "z_distance", "contact_number"] = "distance"
    window_centers: tuple[float, ...] = ()
    force_constant_kj_mol_nm2: float = 1000.0
    equilibration_ns_per_window: float = 0.5
    production_ns_per_window: float = 2.0
    reconstruction_method: Literal["wham", "mbar"] = "wham"

    def validate(self) -> None:
        if not self.window_centers:
            raise ValueError("window_centers cannot be empty")
        if self.force_constant_kj_mol_nm2 <= 0:
            raise ValueError("force_constant_kj_mol_nm2 must be positive")
