# VEVs 项目进度说明（用于对外同步）

更新时间：2026-03-09

## 1. 项目目标（按 `casetwo.md`）
本项目围绕案例二（integrin-mediated targeting recognition）推进分层架构落地，核心目标是先打通 Route A（solution mode）的最小可运行闭环，再逐步扩展到膜环境与自由能高级流程。

当前工程已明确分层方向：
- 配置层：`src/configs/`
- 契约层：`src/interfaces/contracts.py`
- 执行层：`src/models/all_atom/simulation_runner.py`
- 工作流层：`src/models/workflows/binding_workflow.py`
- 验证入口：`scripts/run_minimal_openmm_validation.py`

## 2. 当前代码成果（已完成）
### 2.1 AA-MD 执行主链已落地
`AllAtomSimulation` 已具备真实 OpenMM 主链：
- `prepare_system()`
- `minimize()`
- `equilibrate()`
- `production()`
- `run_full_protocol()`

关键能力：
- 支持 force field 与 water model 映射
- 支持 CPU/CUDA/OpenCL 平台选择（当前验证使用 CPU）
- 支持 NVT/NPT（含 barostat）
- 产出标准 artifacts（`system.xml`、`production.dcd`、`final_state.xml` 等）

### 2.2 最小可运行验证入口已完成
新增脚本：`scripts/run_minimal_openmm_validation.py`

脚本定位：
- engine validation（引擎链路验证）
- 不经过 `BindingWorkflow`
- 直接调用 `AllAtomSimulation.run_full_protocol(...)`
- 固定为 solution mode + CPU

输入处理：
- 使用 `data/test_systems/minimal_complex/minimal_complex.pdb`
- 增加最小预清洗函数 `prepare_clean_test_input(...)`（`pdbfixer`）
- 生成 `minimal_complex_clean.pdb` 后用于装配与模拟

### 2.3 闭环产物已生成
当前 `work/md/` 目录下已有完整最小闭环输出：
- `system.xml`
- `state_init.xml`
- `minimized.pdb`
- `equil_nvt_last.pdb`
- `equil_npt_last.pdb`
- `production.dcd`
- `md_log.csv`
- `production.chk`
- `final_state.xml`

这说明 `prepare_system -> minimize -> equilibrate -> production` 链路已被实际跑通。

## 3. 对照 `casetwo.md` 的完成情况
### Phase 0（架构与契约冻结）
状态：大体完成

已完成项：
- 配置 dataclass 已建立（`SystemConfig`、`MDConfig`、`MembraneConfig` 等）
- 核心数据契约与 Protocol 已定义（`contracts.py`）
- 工作流与执行器职责已分离（`BindingWorkflow` vs `AllAtomSimulation`）

未完成项：
- 目录与模块仍是最小实现，尚未扩展为 `casetwo.md` 中完整分层文件集（如独立 builder/protocol/reporters 模块）

### Phase 1（Route A 最小可运行闭环）
状态：关键目标已完成，workflow 侧仍待补齐

已完成项：
- AA-MD 主链真实执行
- 最小输入可运行验证脚本
- artifacts 文件落地与轨迹基本 sanity check 支持

未完成项：
- `BindingWorkflow` 依赖的 concrete 组件仍缺实现（repository/preprocessor/docking/assembler/analyzer）
- 暂无 Route A 端到端“科学工作流”正式入口脚本

### Phase 2（membrane-ready 平台化）
状态：部分就绪

已完成项：
- `MembraneConfig` 已定义，接口保留扩展位

未完成项：
- `simulation_runner.py` 仍仅支持 `solution` 模式（`membrane` 路径未实现）
- 协议分支（solution/membrane）未拆分

### Phase 3（Route B 膜环境）
状态：未开始

### Phase 4（Umbrella Sampling）
状态：未开始

## 4. 现阶段结论
项目已从“纯概念骨架”进入“可运行执行核心”阶段。  
简言之：引擎主链可跑，工作流全链路尚未跑通。

## 5. 下一步规划（建议执行顺序）
1. 补齐 Route A 的最小 concrete 组件
- `StructureRepository`（输入校验）
- `StructurePreprocessor`（最小结构预处理）
- `DockingEngine`（可复现占位或接入真实 backend）
- `ComplexAssembler`（solution 模式组装）
- `BindingAnalyzer`（最小轨迹指标）

2. 打通 `BindingWorkflow.run()` 的端到端
- 从输入 manifest 到 `simulation artifacts` 再到结果汇总

3. 在 Route A 稳定后做 membrane-ready 升级
- 引入 mode 分支与 membrane protocol 接口
- 保持 `AllAtomSimulation` 为唯一 MD 执行核心

4. 最后再做 Route B 与 Umbrella Sampling
- 避免在执行层未稳定时提前引入高复杂度模块

## 6. 对外同步可直接使用的摘要
可以对外描述为：
- 架构层面已完成配置/契约/执行器/工作流骨架分离
- OpenMM 核心执行链路已真实跑通并产出轨迹
- 当前处于“Phase 1 后半段”：引擎完成，workflow concrete 实现待补齐
- 后续按 `casetwo.md` 先 Route A 完整化，再升级 membrane，再做 umbrella sampling
