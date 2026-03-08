from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(slots=True)
class DockingConfig:
    """对接配置（docking configuration）。

    Phase 0 不实现真实 docking backend，
    但这里先把 workflow 需要的所有控制参数固定下来。
    """

    method: Literal["rigid", "semi_flexible", "flexible"] = "rigid"
    backend: Literal["vina", "smina", "gnina", "placeholder"] = "placeholder"
    n_poses: int = 20
    exhaustiveness: int = 16
    random_seed: int = 20260308
    receptor_box_center: Optional[tuple[float, float, float]] = None
    receptor_box_size: Optional[tuple[float, float, float]] = None
    score_cutoff: Optional[float] = None

    def validate(self) -> None:
        if self.n_poses <= 0:
            raise ValueError("n_poses must be positive")
        if self.exhaustiveness <= 0:
            raise ValueError("exhaustiveness must be positive")
