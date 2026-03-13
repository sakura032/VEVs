from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import Any

from src.configs import MDConfig, MembraneConfig, ProjectPaths, SystemConfig
from src.interfaces.contracts import AssembledComplex, SimulationArtifacts

try:
    from openmm import (
        LangevinMiddleIntegrator,
        MonteCarloBarostat,
        Platform,
        XmlSerializer,
        unit,
    )
    from openmm import app
except ImportError as exc:
    raise ImportError(
        "OpenMM is not installed. Install it in your simulation environment before using "
        "AllAtomSimulation."
    ) from exc

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SimulationContext:
    """AA-MD 运行上下文（simulation context）。

    输入:
    - `SystemConfig`
    - `MDConfig`
    - `MembraneConfig`
    - `ProjectPaths`

    输出:
    - 该类本身不产生产物，作为 `AllAtomSimulation` 的运行参数容器。

    失败方式:
    - dataclass 本身不抛业务异常，异常在各执行步骤内抛出。

    架构边界:
    - 该对象属于 MD Execution 层（execution layer），用于把配置一次性注入执行器，
      避免 workflow 层传递散乱参数。
    """

    system_config: SystemConfig
    md_config: MDConfig
    membrane_config: MembraneConfig
    paths: ProjectPaths


class AllAtomSimulation:
    """全原子模拟执行器（AA-MD execution facade）。

    设计目标:
    - 保持与 workflow 的分层解耦：workflow 只编排，execution 负责 OpenMM 细节。
    - 提供稳定主链：prepare -> minimize -> equilibrate -> production。
    - 维持 run_id 目录规范下的可追踪产物输出。
    """

    def __init__(self, context: SimulationContext):
        self.context = context
        self.paths = context.paths
        self.paths.ensure_dirs()

        # 运行时句柄（runtime handles）
        self._topology = None
        self._positions = None
        self._system = None
        self._integrator = None
        self._simulation = None
        self._production_reporters_configured = False

    def _build_artifact_paths(self) -> SimulationArtifacts:
        """构建标准 MD 产物路径（artifact paths）."""
        md_dir = self.paths.work_dir / "md"
        md_dir.mkdir(parents=True, exist_ok=True)
        return SimulationArtifacts(
            system_xml=md_dir / "system.xml",
            initial_state_xml=md_dir / "state_init.xml",
            minimized_structure=md_dir / "minimized.pdb",
            nvt_last_structure=md_dir / "equil_nvt_last.pdb",
            npt_last_structure=md_dir / "equil_npt_last.pdb",
            trajectory=md_dir / "production.dcd",
            final_state_xml=md_dir / "final_state.xml",
            log_csv=md_dir / "md_log.csv",
            checkpoint=md_dir / "production.chk",
        )

    def _resolve_forcefield_files(self) -> tuple[str, str]:
        """解析 OpenMM 力场文件映射（force-field XML mapping）。

        输入:
        - `SystemConfig.forcefield_name`
        - `SystemConfig.water_model`

        输出:
        - `(protein_ff_xml, water_ff_xml)`

        失败方式:
        - `ValueError`: 力场名/水模型不支持时抛出，并列出支持项。

        架构边界:
        - 该函数只做“配置到 OpenMM XML”的翻译，不包含 workflow 决策。
        """
        ff_name = self.context.system_config.forcefield_name.strip().lower()
        water_model = self.context.system_config.water_model.strip().lower()

        ff_to_water_map: dict[str, dict[str, str]] = {
            "amber14sb": {
                "tip3p": "amber14/tip3p.xml",
                "spce": "amber14/spce.xml",
                "tip4pew": "amber14/tip4pew.xml",
                "tip3pfb": "amber14/tip3pfb.xml",
                "tip4pfb": "amber14/tip4pfb.xml",
                "opc": "amber14/opc.xml",
                "opc3": "amber14/opc3.xml",
            },
            # 使用 OpenMM 文档中的标准 CHARMM36 文件名。
            "charmm36": {
                "tip3p": "charmm36/water.xml",
                "spce": "charmm36/spce.xml",
                "tip4pew": "charmm36/tip4pew.xml",
                "tip5p": "charmm36/tip5p.xml",
            },
        }
        ff_main_map = {
            "amber14sb": "amber14-all.xml",
            "charmm36": "charmm36.xml",
        }

        if ff_name not in ff_to_water_map:
            supported_ff = ", ".join(sorted(ff_to_water_map.keys()))
            raise ValueError(
                f"Unsupported force field name: {ff_name}. Supported force fields: {supported_ff}"
            )

        water_map = ff_to_water_map[ff_name]
        if water_model not in water_map:
            supported_water = ", ".join(sorted(water_map.keys()))
            raise ValueError(
                f"Unsupported water model '{water_model}' for force field '{ff_name}'. "
                f"Supported water models: {supported_water}"
            )

        return ff_main_map[ff_name], water_map[water_model]

    def _build_integrator(self) -> LangevinMiddleIntegrator:
        """构建积分器（LangevinMiddleIntegrator）。"""
        cfg = self.context.md_config
        sys_cfg = self.context.system_config
        return LangevinMiddleIntegrator(
            sys_cfg.temperature_kelvin * unit.kelvin,
            cfg.friction_per_ps / unit.picosecond,
            cfg.timestep_fs * unit.femtosecond,
        )

    def _get_platform_and_properties(self) -> tuple[Platform, dict[str, str]]:
        """获取平台与属性（platform-specific properties）。

        输入:
        - `MDConfig.platform`, `MDConfig.precision`
        - 可选 `MDConfig.device_index`, `MDConfig.cpu_threads`

        输出:
        - `(Platform, properties)`

        失败方式:
        - 请求平台不可用时自动回退 CPU，不中断流程。
        - 属性名不支持时不会抛错，按“可用即设，不可用即忽略”处理。

        架构边界:
        - 该函数属于 execution 层兼容逻辑，不改 workflow 默认行为。
        """
        cfg = self.context.md_config
        requested_platform_name = cfg.platform

        try:
            platform = Platform.getPlatformByName(requested_platform_name)
        except Exception as exc:
            logger.warning(
                "Requested platform %s is unavailable, falling back to CPU. Original error: %s",
                requested_platform_name,
                exc,
            )
            platform = Platform.getPlatformByName("CPU")

        platform_name = platform.getName()
        property_names = set(platform.getPropertyNames())
        properties: dict[str, str] = {}

        # 精度属性兼容（Precision / CudaPrecision / OpenCLPrecision）。
        if "Precision" in property_names:
            properties["Precision"] = cfg.precision
        elif platform_name.upper() == "CUDA" and "CudaPrecision" in property_names:
            properties["CudaPrecision"] = cfg.precision
        elif platform_name.upper() == "OPENCL" and "OpenCLPrecision" in property_names:
            properties["OpenCLPrecision"] = cfg.precision

        # 设备索引（DeviceIndex family）。
        if cfg.device_index:
            if "DeviceIndex" in property_names:
                properties["DeviceIndex"] = str(cfg.device_index)
            elif platform_name.upper() == "CUDA" and "CudaDeviceIndex" in property_names:
                properties["CudaDeviceIndex"] = str(cfg.device_index)
            elif platform_name.upper() == "OPENCL" and "OpenCLDeviceIndex" in property_names:
                properties["OpenCLDeviceIndex"] = str(cfg.device_index)

        # CPU 线程（Threads / CpuThreads）。
        if cfg.cpu_threads is not None:
            if "Threads" in property_names:
                properties["Threads"] = str(cfg.cpu_threads)
            elif "CpuThreads" in property_names:
                properties["CpuThreads"] = str(cfg.cpu_threads)

        return platform, properties

    def _steps_from_ns(self, time_ns: float) -> int:
        """把纳秒转成积分步数（ns -> integration steps）。"""
        if time_ns < 0:
            raise ValueError("time_ns must be non-negative")
        timestep_fs = self.context.md_config.timestep_fs
        return int(round(time_ns * 1_000_000 / timestep_fs))

    def _write_current_structure(self, output_path: Path) -> None:
        """将当前 context 坐标写出为 PDB。"""
        if self._simulation is None or self._topology is None:
            raise RuntimeError("Simulation runtime is not initialized.")

        state = self._simulation.context.getState(
            getPositions=True,
            getEnergy=True,
            enforcePeriodicBox=True,
        )
        with open(output_path, "w", encoding="utf-8") as handle:
            app.PDBFile.writeFile(self._topology, state.getPositions(), handle)

    def _has_barostat(self) -> bool:
        """检查系统中是否已有 barostat。"""
        if self._system is None:
            return False
        for i in range(self._system.getNumForces()):
            force = self._system.getForce(i)
            if isinstance(force, MonteCarloBarostat):
                return True
        return False

    def _configure_production_reporters(
        self,
        artifacts: SimulationArtifacts,
        total_steps: int,
    ) -> None:
        """配置 production reporters（DCD/CSV/checkpoint）。"""
        if self._simulation is None:
            raise RuntimeError("Simulation runtime is not initialized.")
        if total_steps <= 0:
            raise ValueError("Production total_steps must be positive.")

        cfg = self.context.md_config
        if cfg.save_interval_steps <= 0:
            raise ValueError("save_interval_steps must be positive.")
        if cfg.state_interval_steps <= 0:
            raise ValueError("state_interval_steps must be positive.")
        if cfg.checkpoint_interval_steps <= 0:
            raise ValueError("checkpoint_interval_steps must be positive.")

        self._simulation.reporters.clear()
        self._simulation.reporters.append(
            app.DCDReporter(
                str(artifacts.trajectory),
                cfg.save_interval_steps,
                append=False,
                enforcePeriodicBox=None,
            )
        )
        self._simulation.reporters.append(
            app.StateDataReporter(
                str(artifacts.log_csv),
                cfg.state_interval_steps,
                step=True,
                time=True,
                potentialEnergy=True,
                kineticEnergy=True,
                totalEnergy=True,
                temperature=True,
                volume=True,
                density=True,
                speed=True,
                elapsedTime=True,
                separator=",",
                append=False,
            )
        )
        self._simulation.reporters.append(
            app.CheckpointReporter(
                str(artifacts.checkpoint),
                cfg.checkpoint_interval_steps,
                writeState=False,
            )
        )

        self._production_reporters_configured = True
        logger.info(
            "Production reporters configured: DCD -> %s, log -> %s, checkpoint -> %s",
            artifacts.trajectory,
            artifacts.log_csv,
            artifacts.checkpoint,
        )

    def _write_json(self, output_path: Path, payload: dict[str, Any]) -> None:
        """写 JSON 工具函数（JSON writer helper）。"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _pdbfixer_fix_pdb(self, input_pdb: Path, output_pdb: Path) -> dict[str, Any]:
        """用 PDBFixer 对 assembled complex 做执行层修复（execution-side fix）。

        输入:
        - `input_pdb`: workflow 组装得到的 complex PDB
        - `output_pdb`: 修复后输出路径（通常为 `work/.../md/complex_fixed.pdb`）

        输出:
        - 修复报告 `dict`，包含 missing residues/atoms、nonstandard residues 列表、
          是否启用替换（replace_nonstandard_residues）

        失败方式:
        - `FileNotFoundError`: 输入文件缺失
        - `ValueError`: 文件后缀非法（非 `.pdb`）
        - `ImportError`: 缺少 `pdbfixer` 或 `openmm`

        架构边界:
        - 该函数属于 MD Execution 层的鲁棒性增强（robustness enhancement），
          不替代 Structure Preparation 层。
        """
        if not input_pdb.exists():
            raise FileNotFoundError(f"Input PDB not found for execution fix: {input_pdb}")
        if input_pdb.suffix.lower() != ".pdb":
            raise ValueError(f"Execution fix currently supports only .pdb, got: {input_pdb}")

        try:
            from pdbfixer import PDBFixer
            from openmm import app as openmm_app
        except ImportError as exc:
            raise ImportError(
                "Execution-layer PDBFixer step requires pdbfixer and openmm."
            ) from exc

        fixer = PDBFixer(filename=str(input_pdb))
        fixer.findMissingResidues()
        fixer.findNonstandardResidues()
        fixer.findMissingAtoms()

        nonstandard_rows: list[dict[str, str]] = []
        for item in fixer.nonstandardResidues:
            residue = item[0]
            replacement = item[1] if len(item) > 1 else "UNKNOWN"
            nonstandard_rows.append(
                {
                    "residue_name": str(getattr(residue, "name", "UNK")),
                    "chain_id": str(getattr(getattr(residue, "chain", None), "id", "")),
                    "residue_id": str(getattr(residue, "id", "")),
                    "replacement": str(replacement),
                }
            )

        # 默认不替换 nonstandard residues，避免 silent mutation（静默突变）。
        replace_nonstandard = self.context.system_config.replace_nonstandard_residues
        if replace_nonstandard and fixer.nonstandardResidues:
            fixer.replaceNonstandardResidues()

        # 默认不在这里 addMissingHydrogens，避免与 modeller.addHydrogens 重复。
        fixer.addMissingAtoms()

        output_pdb.parent.mkdir(parents=True, exist_ok=True)
        with open(output_pdb, "w", encoding="utf-8") as handle:
            openmm_app.PDBFile.writeFile(fixer.topology, fixer.positions, handle)

        return {
            "input_pdb": str(input_pdb.resolve()),
            "output_pdb": str(output_pdb.resolve()),
            "replace_nonstandard_residues": replace_nonstandard,
            "missing_residues_groups": len(fixer.missingResidues),
            "missing_atoms_residues": len(fixer.missingAtoms),
            "missing_terminals_residues": len(fixer.missingTerminals),
            "nonstandard_residue_count": len(nonstandard_rows),
            "nonstandard_residues": nonstandard_rows,
        }

    def _pdbfixer_fix_complex_if_enabled(
        self,
        structure_path: Path,
        md_dir: Path,
        metadata_dir: Path,
    ) -> Path:
        """按开关执行 complex 后处理（post-fix）并写报告。

        输入:
        - `structure_path`: 原始 assembled complex
        - `md_dir`: run 对应 `work/.../md` 目录
        - `metadata_dir`: run 对应 `outputs/.../metadata` 目录

        输出:
        - 后续 OpenMM 将读取的结构路径（原始或修复后）

        失败方式:
        - 开关开启时，依赖缺失/输入非法会抛出 `ImportError`/`ValueError`/`FileNotFoundError`

        架构边界:
        - 属于 execution 层，目的是提升“可执行稳定性（execution robustness）”。
        """
        if not self.context.md_config.enable_pdbfixer_fix:
            logger.info("Execution-layer PDBFixer post-fix is disabled by config.")
            return structure_path

        fixed_path = md_dir / "complex_fixed.pdb"
        report = self._pdbfixer_fix_pdb(structure_path, fixed_path)
        report_path = metadata_dir / "md_pdbfixer_report.json"
        self._write_json(report_path, report)
        logger.info("Execution-layer PDBFixer report written to %s", report_path)
        return fixed_path

    def prepare_system(self, assembled: AssembledComplex) -> SimulationArtifacts:
        """准备 OpenMM 系统（prepare OpenMM system）。

        输入:
        - `AssembledComplex`（当前要求 mode=solution，且结构为 `.pdb`）

        输出:
        - `SimulationArtifacts`（路径集合），并初始化 runtime handles。

        失败方式:
        - `NotImplementedError`: mode 不是 `solution`
        - `ValueError`: 输入格式非法/力场映射失败
        - `ImportError`: 若启用 execution-layer PDBFixer 且依赖缺失

        架构边界:
        - 属于 MD Execution 层，不负责 docking/workflow 决策。
        """
        logger.info("Preparing OpenMM system for %s", assembled.complex_structure)

        if assembled.mode != "solution":
            raise NotImplementedError(
                "Phase 1 minimal runner currently supports solution mode only, not membrane mode."
            )

        structure_path = assembled.complex_structure
        if structure_path.suffix.lower() != ".pdb":
            raise ValueError(
                "Phase 1 minimal runner currently supports only PDB input for assembled complex."
            )

        artifacts = self._build_artifact_paths()
        md_dir = artifacts.system_xml.parent if artifacts.system_xml is not None else (self.paths.work_dir / "md")
        metadata_dir = self.paths.output_dir / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)

        # 在 execution 层做可控后处理（post-fix），增强跨输入鲁棒性。
        structure_path = self._pdbfixer_fix_complex_if_enabled(
            structure_path=structure_path,
            md_dir=md_dir,
            metadata_dir=metadata_dir,
        )

        protein_ff_xml, water_ff_xml = self._resolve_forcefield_files()
        logger.info("Using OpenMM force field files: %s + %s", protein_ff_xml, water_ff_xml)

        pdb = app.PDBFile(str(structure_path))
        forcefield = app.ForceField(protein_ff_xml, water_ff_xml)
        modeller = app.Modeller(pdb.topology, pdb.positions)

        modeller.addHydrogens(forcefield, pH=self.context.system_config.ph)
        modeller.addSolvent(
            forcefield,
            model=self.context.system_config.water_model.lower(),
            padding=1.0 * unit.nanometer,
            ionicStrength=self.context.system_config.ionic_strength_molar * unit.molar,
        )

        # 固定输出 solvated 初态结构，便于可视化与 debug。
        solvated_pdb_path = md_dir / "solvated.pdb"
        with open(solvated_pdb_path, "w", encoding="utf-8") as handle:
            app.PDBFile.writeFile(modeller.topology, modeller.positions, handle)

        system = forcefield.createSystem(
            modeller.topology,
            nonbondedMethod=app.PME,
            nonbondedCutoff=1.0 * unit.nanometer,
            constraints=app.HBonds,
            rigidWater=True,
            ewaldErrorTolerance=0.0005,
        )

        integrator = self._build_integrator()
        platform, properties = self._get_platform_and_properties()
        if properties:
            simulation = app.Simulation(
                modeller.topology,
                system,
                integrator,
                platform,
                properties,
            )
        else:
            simulation = app.Simulation(
                modeller.topology,
                system,
                integrator,
                platform,
            )
        simulation.context.setPositions(modeller.positions)

        self._topology = modeller.topology
        self._positions = modeller.positions
        self._system = system
        self._integrator = integrator
        self._simulation = simulation
        self._production_reporters_configured = False

        artifacts.system_xml.write_text(XmlSerializer.serialize(system), encoding="utf-8")
        init_state = simulation.context.getState(
            getPositions=True,
            getEnergy=True,
            enforcePeriodicBox=True,
        )
        artifacts.initial_state_xml.write_text(
            XmlSerializer.serialize(init_state),
            encoding="utf-8",
        )

        logger.info("OpenMM system prepared successfully; solvated structure -> %s", solvated_pdb_path)
        return artifacts

    def minimize(self, artifacts: SimulationArtifacts) -> SimulationArtifacts:
        """能量最小化（energy minimization）。"""
        if self._simulation is None or self._topology is None:
            raise RuntimeError("Simulation runtime is not initialized. Call prepare_system() before minimize().")

        logger.info("Starting energy minimization")
        self._simulation.minimizeEnergy(
            tolerance=(
                self.context.md_config.minimize_tolerance_kj_mol_nm
                * unit.kilojoule_per_mole
                / unit.nanometer
            ),
            maxIterations=self.context.md_config.minimize_max_iterations,
        )

        minimized_state = self._simulation.context.getState(
            getPositions=True,
            getEnergy=True,
            enforcePeriodicBox=True,
        )
        with open(artifacts.minimized_structure, "w", encoding="utf-8") as handle:
            app.PDBFile.writeFile(self._topology, minimized_state.getPositions(), handle)

        logger.info("Minimized structure written to %s", artifacts.minimized_structure)
        return artifacts

    def equilibrate(self, artifacts: SimulationArtifacts) -> SimulationArtifacts:
        """执行最小 NVT/NPT 平衡（minimal equilibration）。"""
        if self._simulation is None or self._system is None or self._topology is None:
            raise RuntimeError("Simulation runtime is not initialized. Call prepare_system() before equilibrate().")

        cfg = self.context.md_config
        sys_cfg = self.context.system_config
        nvt_steps = self._steps_from_ns(cfg.nvt_equilibration_ns)
        npt_steps = self._steps_from_ns(cfg.npt_equilibration_ns)

        logger.info(
            "Starting NVT equilibration: %.3f ns (%d steps)",
            cfg.nvt_equilibration_ns,
            nvt_steps,
        )
        self._simulation.context.setVelocitiesToTemperature(
            sys_cfg.temperature_kelvin,
            cfg.random_seed,
        )
        if nvt_steps > 0:
            self._simulation.step(nvt_steps)
        self._write_current_structure(artifacts.nvt_last_structure)
        logger.info("NVT last frame written to %s", artifacts.nvt_last_structure)

        if cfg.use_barostat and npt_steps > 0:
            logger.info(
                "Starting NPT equilibration: %.3f ns (%d steps)",
                cfg.npt_equilibration_ns,
                npt_steps,
            )
            if not self._has_barostat():
                self._system.addForce(
                    MonteCarloBarostat(
                        sys_cfg.pressure_bar * unit.bar,
                        sys_cfg.temperature_kelvin * unit.kelvin,
                    )
                )
                self._simulation.context.reinitialize(preserveState=True)
            self._simulation.step(npt_steps)
            self._write_current_structure(artifacts.npt_last_structure)
            logger.info("NPT last frame written to %s", artifacts.npt_last_structure)
        else:
            logger.info(
                "Skipping NPT equilibration because use_barostat=%s or npt_steps=%d",
                cfg.use_barostat,
                npt_steps,
            )
            self._write_current_structure(artifacts.npt_last_structure)

        return artifacts

    def production(self, artifacts: SimulationArtifacts) -> SimulationArtifacts:
        """执行生产模拟（production MD）。"""
        if self._simulation is None or self._system is None or self._topology is None:
            raise RuntimeError("Simulation runtime is not initialized. Call prepare_system() before production().")

        cfg = self.context.md_config
        prod_steps = self._steps_from_ns(cfg.production_ns)
        if prod_steps <= 0:
            raise ValueError("production_ns must be positive to generate a production trajectory.")

        logger.info("Starting production MD: %.3f ns (%d steps)", cfg.production_ns, prod_steps)
        self._configure_production_reporters(artifacts, prod_steps)
        self._simulation.step(prod_steps)

        self._simulation.saveState(str(artifacts.final_state_xml))
        self._simulation.saveCheckpoint(str(artifacts.checkpoint))
        logger.info(
            "Production completed: trajectory -> %s, final state -> %s, checkpoint -> %s",
            artifacts.trajectory,
            artifacts.final_state_xml,
            artifacts.checkpoint,
        )
        return artifacts

    def run_full_protocol(
        self,
        assembled: AssembledComplex,
        run_production: bool = True,
    ) -> SimulationArtifacts:
        """串联执行完整协议（prepare -> minimize -> equilibrate -> production）。"""
        artifacts = self.prepare_system(assembled)
        artifacts = self.minimize(artifacts)
        artifacts = self.equilibrate(artifacts)
        if run_production:
            artifacts = self.production(artifacts)
        return artifacts

