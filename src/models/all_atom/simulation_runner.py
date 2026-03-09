from __future__ import annotations

from dataclasses import dataclass
import logging

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

    作用：
    1. 把 runner 运行时需要的配置打包。
    2. 避免 prepare/minimize/equilibrate/production 每一步都传散乱参数。
    """

    system_config: SystemConfig
    md_config: MDConfig
    membrane_config: MembraneConfig
    paths: ProjectPaths


class AllAtomSimulation:
    """全原子模拟执行器（AA-MD execution façade）。

    当前 Phase 1 已实现：
    - prepare_system()
    - minimize()
    - equilibrate()
    - production()

    设计边界：
    1. 当前仅支持 solution mode，不支持 membrane mode
    2. 当前假设 assembled complex 是未溶剂化的 PDB
    3. 当前假设所选 force field 能覆盖体系中的全部残基/原子类型
    """

    def __init__(self, context: SimulationContext):
        self.context = context
        self.paths = context.paths
        self.paths.ensure_dirs()

        # Runtime handles（运行时对象）
        self._topology = None
        self._positions = None
        self._system = None
        self._integrator = None
        self._simulation = None

        # Reporter state
        self._production_reporters_configured = False
    
    #1 统一定义产物路径
    def _build_artifact_paths(self) -> SimulationArtifacts:
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
    
    #2 把 forcefield_name + water_model 映射成 OpenMM XML 文件名. SystemConfig.forcefield_name 只是逻辑名，OpenMM 真正需要的是 XML 文件名
    def _resolve_forcefield_files(self) -> tuple[str, str]:
        ff_name = self.context.system_config.forcefield_name.lower()
        water_model = self.context.system_config.water_model.lower()

        if ff_name == "amber14sb":
            water_map = {
                "tip3p": "amber14/tip3p.xml",
                "tip3pfb": "amber14/tip3pfb.xml",
                "spce": "amber14/spce.xml",
                "tip4pew": "amber14/tip4pew.xml",
                "tip4pfb": "amber14/tip4pfb.xml",
                "opc": "amber14/opc.xml",
                "opc3": "amber14/opc3.xml",
            }
            if water_model not in water_map:
                raise ValueError(
                    f"Unsupported water model for amber14sb: {water_model}"
                )
            return "amber14-all.xml", water_map[water_model]

        if ff_name == "charmm36":
            water_map = {
                "tip3p": "charmm36_2024/water.xml",
                "spce": "charmm36_2024/spce.xml",
                "tip4pew": "charmm36_2024/tip4pew.xml",
                "tip5p": "charmm36_2024/tip5p.xml",
            }
            if water_model not in water_map:
                raise ValueError(
                    f"Unsupported water model for charmm36: {water_model}"
                )
            return "charmm36_2024.xml", water_map[water_model]

        raise ValueError(f"Unsupported force field name: {ff_name}")
    
    #3 构建 LangevinMiddleIntegrator 输出：OpenMM integrator 对象
    def _build_integrator(self) -> LangevinMiddleIntegrator:
        cfg = self.context.md_config
        sys_cfg = self.context.system_config
        return LangevinMiddleIntegrator(
            sys_cfg.temperature_kelvin * unit.kelvin,
            cfg.friction_per_ps / unit.picosecond,
            cfg.timestep_fs * unit.femtosecond,
        )
    
    #4 选择 CPU/CUDA/OpenCL，并设置精度属性，输出：OpenMM platform 对象 + properties dict
    def _get_platform_and_properties(self) -> tuple[Platform, dict[str, str]]:
        platform_name = self.context.md_config.platform
        precision = self.context.md_config.precision

        try:
            platform = Platform.getPlatformByName(platform_name)
        except Exception as exc:
            logger.warning(
                "Requested platform %s is unavailable, falling back to CPU. Original error: %s",
                platform_name,
                exc,
            )
            return Platform.getPlatformByName("CPU"), {}

        properties: dict[str, str] = {}
        if platform_name in {"CUDA", "OpenCL"}:
            properties["Precision"] = precision

        return platform, properties
    
    #5 把纳秒转换为积分步数，输出：整数步数
    def _steps_from_ns(self, time_ns: float) -> int:
        """把纳秒转换为积分步数（ns -> integration steps）。

        timestep_fs 以飞秒为单位，因此：
        steps = time_ns * 1e6 / timestep_fs
        """
        if time_ns < 0:
            raise ValueError("time_ns must be non-negative")
        timestep_fs = self.context.md_config.timestep_fs
        return int(round(time_ns * 1_000_000 / timestep_fs))
    
    #6 写当前帧、检查恒压器、配置 DCD/CSV/checkpoint 报告器
    #6.1 把当前 Simulation context 中的坐标写成 PDB 文件，输出：无（直接写文件）
    def _write_current_structure(self, output_path) -> None:
        """把当前 context 中的坐标写成 PDB。"""
        if self._simulation is None or self._topology is None:
            raise RuntimeError("Simulation runtime is not initialized.")

        state = self._simulation.context.getState(
            getPositions=True,
            getEnergy=True,
            enforcePeriodicBox=True,
        )
        with open(output_path, "w", encoding="utf-8") as handle:
            app.PDBFile.writeFile(
                self._topology,
                state.getPositions(),
                handle,
            )
    
    #6.2 检查当前 System 中是否已存在 MonteCarloBarostat，输出：布尔值
    def _has_barostat(self) -> bool:
        """检查当前 System 中是否已存在 MonteCarloBarostat。"""
        if self._system is None:
            return False
        for i in range(self._system.getNumForces()):
            force = self._system.getForce(i)
            if isinstance(force, MonteCarloBarostat):
                return True
        return False
    
    #6.3 配置 production 阶段 reporters：DCDReporter + StateDataReporter + CheckpointReporter。输出：无（直接修改 Simulation 对象）
    def _configure_production_reporters(
        self,
        artifacts: SimulationArtifacts,
        total_steps: int,
    ) -> None:
        """配置 production 阶段 reporters。"""
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

        # 清空旧 reporters，避免重复追加
        self._simulation.reporters.clear()

        # 1) 坐标轨迹
        self._simulation.reporters.append(
            app.DCDReporter(
                str(artifacts.trajectory),
                cfg.save_interval_steps,
                append=False,
                enforcePeriodicBox=None,
            )
        )

        # 2) 数值日志
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

        # 3) Checkpoint
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
    
    #7 构建 OpenMM 体系（PDB -> 加氢/溶剂/离子 -> System/Simulation），输出：SimulationArtifacts（包含 system.xml、initial_state.xml 等路径）
    def prepare_system(self, assembled: AssembledComplex) -> SimulationArtifacts:
        """准备 OpenMM 体系（prepare OpenMM system）。

        Phase 1 minimal runnable version:
        1. 读取未溶剂化的 complex PDB
        2. 构建 ForceField
        3. 创建 Modeller
        4. 补氢
        5. 加显式水和离子
        6. createSystem()
        7. 创建 Integrator / Simulation
        8. 写出 system.xml 与 initial_state.xml
        """
        logger.info("Preparing OpenMM system for %s", assembled.complex_structure)

        if assembled.mode != "solution":
            raise NotImplementedError(
                "Phase 1 minimal runner currently supports solution mode only, "
                "not membrane mode."
            )

        structure_path = assembled.complex_structure
        if structure_path.suffix.lower() != ".pdb":
            raise ValueError(
                "Phase 1 minimal runner currently supports only PDB input for assembled complex"
            )

        artifacts = self._build_artifact_paths()

        protein_ff_xml, water_ff_xml = self._resolve_forcefield_files()
        logger.info("Using OpenMM force field files: %s + %s", protein_ff_xml, water_ff_xml)

        pdb = app.PDBFile(str(structure_path))
        forcefield = app.ForceField(protein_ff_xml, water_ff_xml)

        modeller = app.Modeller(pdb.topology, pdb.positions)

        # 补氢
        modeller.addHydrogens(forcefield, pH=self.context.system_config.ph)

        # 加显式水和离子
        modeller.addSolvent(
            forcefield,
            model=self.context.system_config.water_model.lower(),
            padding=1.0 * unit.nanometer,
            ionicStrength=self.context.system_config.ionic_strength_molar * unit.molar,
        )

        # 创建 System
        system = forcefield.createSystem(
            modeller.topology,
            nonbondedMethod=app.PME,
            nonbondedCutoff=1.0 * unit.nanometer,
            constraints=app.HBonds,
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

        artifacts.system_xml.write_text(
            XmlSerializer.serialize(system),
            encoding="utf-8",
        )

        init_state = simulation.context.getState(
            getPositions=True,
            getEnergy=True,
            enforcePeriodicBox=True,
        )
        artifacts.initial_state_xml.write_text(
            XmlSerializer.serialize(init_state),
            encoding="utf-8",
        )

        logger.info("OpenMM system prepared successfully")
        return artifacts
    
    #8 能量最小化（minimization），输出：SimulationArtifacts（写出 minimized.pdb 更新 minimized_structure 路径）
    def minimize(self, artifacts: SimulationArtifacts) -> SimulationArtifacts:
        """能量最小化（energy minimization）。

        Phase 1:
        - 调用 OpenMM minimizeEnergy()
        - 将最小化后的结构写出为 minimized.pdb
        """
        if self._simulation is None or self._topology is None:
            raise RuntimeError(
                "Simulation runtime is not initialized. Call prepare_system() before minimize()."
            )

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
            app.PDBFile.writeFile(
                self._topology,
                minimized_state.getPositions(),
                handle,
            )

        logger.info("Minimized structure written to %s", artifacts.minimized_structure)
        return artifacts
    
    #9 平衡（equilibration），输出：SimulationArtifacts（写出 equil_nvt_last.pdb 和 equil_npt_last.pdb 更新 nvt_last_structure 和 npt_last_structure 路径）
    def equilibrate(self, artifacts: SimulationArtifacts) -> SimulationArtifacts:
        """真实实现最小 NVT/NPT 平衡（minimal NVT/NPT equilibration）。

        当前实现：
        1. NVT：按目标温度初始化速度，并积分 nvt_equilibration_ns
        2. NPT：若 use_barostat=True，则加入 MonteCarloBarostat，reinitialize 后继续积分
        3. 分别写出 equil_nvt_last.pdb 和 equil_npt_last.pdb
        """
        if self._simulation is None or self._system is None or self._topology is None:
            raise RuntimeError(
                "Simulation runtime is not initialized. Call prepare_system() before equilibrate()."
            )

        cfg = self.context.md_config
        sys_cfg = self.context.system_config

        nvt_steps = self._steps_from_ns(cfg.nvt_equilibration_ns)
        npt_steps = self._steps_from_ns(cfg.npt_equilibration_ns)

        logger.info(
            "Starting NVT equilibration: %.3f ns (%d steps)",
            cfg.nvt_equilibration_ns,
            nvt_steps,
        )

        # 给体系分配与目标温度匹配的初始速度
        self._simulation.context.setVelocitiesToTemperature(
            sys_cfg.temperature_kelvin,
            cfg.random_seed,
        )

        # NVT 积分
        if nvt_steps > 0:
            self._simulation.step(nvt_steps)

        # 写出 NVT 末态结构
        self._write_current_structure(artifacts.nvt_last_structure)
        logger.info("NVT last frame written to %s", artifacts.nvt_last_structure)

        # NPT：通过 MonteCarloBarostat 实现恒压
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
                # Context 创建后修改了 System，必须 reinitialize 才会生效
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
            # 为了保证下游 I/O 契约完整，这里把 NVT 末态再写一份到 NPT 输出路径
            self._write_current_structure(artifacts.npt_last_structure)

        return artifacts
    
    #10 生产（production），输出：SimulationArtifacts（写出 production.dcd、final_state.xml、production.chk 更新 trajectory、final_state_xml、checkpoint 路径）
    def production(self, artifacts: SimulationArtifacts) -> SimulationArtifacts:
        """真实实现 production MD。

        当前实现：
        1. 配置 DCDReporter / StateDataReporter / CheckpointReporter
        2. 按 production_ns 积分推进
        3. 显式写出 final_state.xml 和 production.chk
        """
        if self._simulation is None or self._system is None or self._topology is None:
            raise RuntimeError(
                "Simulation runtime is not initialized. Call prepare_system() before production()."
            )

        cfg = self.context.md_config
        prod_steps = self._steps_from_ns(cfg.production_ns)
        if prod_steps <= 0:
            raise ValueError(
                "production_ns must be positive to generate a production trajectory."
            )

        logger.info(
            "Starting production MD: %.3f ns (%d steps)",
            cfg.production_ns,
            prod_steps,
        )

        self._configure_production_reporters(artifacts, prod_steps)

        self._simulation.step(prod_steps)

        # 显式写出最终 state（portable XML）
        self._simulation.saveState(str(artifacts.final_state_xml))

        # 显式写出最终 checkpoint，确保最后一步状态被保存
        self._simulation.saveCheckpoint(str(artifacts.checkpoint))

        logger.info(
            "Production completed: trajectory -> %s, final state -> %s, checkpoint -> %s",
            artifacts.trajectory,
            artifacts.final_state_xml,
            artifacts.checkpoint,
        )
        return artifacts
    
    #11 串联执行 AA-MD protocol: prepare -> minimize -> equilibrate -> production，输出：SimulationArtifacts（包含 prepare/minimize/equilibration/production 产物路径）
    def run_full_protocol(
        self,
        assembled: AssembledComplex,
        run_production: bool = True,
    ) -> SimulationArtifacts:
        """执行当前已实现的 AA-MD protocol。"""
        artifacts = self.prepare_system(assembled)
        artifacts = self.minimize(artifacts)
        artifacts = self.equilibrate(artifacts)

        if run_production:
            artifacts = self.production(artifacts)

        return artifacts
