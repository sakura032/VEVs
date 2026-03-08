from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(slots=True)
class MembraneConfig:
    """膜环境配置（membrane configuration）。

    注意：
    这个配置即使在 route A 暂时不用，也必须先定义。
    这样 route A 才是 membrane-ready architecture，而不是 solution-only hack。
    """

    enabled: bool = False
    lipid_composition: dict[str, float] = field(default_factory=lambda: {"POPC": 1.0})
    bilayer_size_nm: tuple[float, float] = (10.0, 10.0)
    protein_orientation: Literal["auto", "manual"] = "auto"
    leaflet_asymmetry: bool = False
    water_padding_nm: float = 1.5
    ion_concentration_molar: float = 0.15

    def validate(self) -> None:
        if self.enabled and not self.lipid_composition:
            raise ValueError("lipid_composition cannot be empty when membrane is enabled")
        total = sum(self.lipid_composition.values())
        if self.enabled and total <= 0:
            raise ValueError("sum of lipid_composition must be positive")
        if self.water_padding_nm <= 0:
            raise ValueError("water_padding_nm must be positive")
