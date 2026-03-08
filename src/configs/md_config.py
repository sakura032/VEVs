from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True)
class MDConfig:
    """动力学协议配置（molecular dynamics protocol configuration）。

    作用：
    1. 定义最小化、平衡、生产模拟的时间与积分参数。
    2. 将“物理协议（protocol）”从 workflow 中剥离。
    3. 为后续 solution / membrane 双协议预留扩展位点。
    """

    platform: Literal["CPU", "CUDA", "OpenCL"] = "CUDA"
    precision: Literal["single", "mixed", "double"] = "mixed"
    timestep_fs: float = 2.0
    friction_per_ps: float = 1.0
    minimize_max_iterations: int = 5000
    minimize_tolerance_kj_mol_nm: float = 10.0
    nvt_equilibration_ns: float = 0.2
    npt_equilibration_ns: float = 0.8
    production_ns: float = 20.0
    save_interval_steps: int = 5000
    state_interval_steps: int = 5000
    checkpoint_interval_steps: int = 25000
    random_seed: int = 20260308
    use_barostat: bool = True
    use_semiisotropic_barostat: bool = False

    def validate(self) -> None:
        if self.timestep_fs <= 0:
            raise ValueError("timestep_fs must be positive")
        if self.production_ns <= 0:
            raise ValueError("production_ns must be positive")
        if self.save_interval_steps <= 0:
            raise ValueError("save_interval_steps must be positive")
