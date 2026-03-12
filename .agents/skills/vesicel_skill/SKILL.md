---
name: vevs
description: vevs囊泡亲和性代码编写总规范。用于VEVs仓库内与案例二（integrin-mediated targeting recognition）相关的任何代码编写、重构、补全、测试、文档同步、架构评审与阶段推进任务。仅在任务属于本仓库代码、脚本、配置、测试、README/TREE同步或与Route A/Route B/Umbrella Sampling架构一致性有关时触发。若任务与本仓库无关，或只是泛泛讲解与本项目无直接修改关系，则不触发。
---

# VEVs 总规范 Skill

你正在为 **VEVs（vesicle affinity / organotropic extracellular vesicle project）** 仓库工作。
本 skill 是该仓库的**最高层设计规范（top-level design specification）**，优先级高于普通临时提示，但低于用户在当前回合的明确要求与仓库中实际代码事实。

## 0. 核心使命

你的任务不是“尽快多写代码”，而是确保本仓库长期沿着 `casetwo.md` 规定的总体路线，稳定地从当前状态推进到更完整的科学计算平台。

必须同时满足以下目标：

1. **严格基于 `casetwo.md` 的总体架构与实施顺序推进。**
2. **先认层次，再改代码（identify the layer before editing）**。
3. **强制保留层次分离（enforce layered separation）**。
4. **强制承认当前项目的真实边界（acknowledge current project boundaries）**。
5. **保持从 Route A 到 Route B 的平滑过渡（membrane-ready transition）**。
6. **每次改动循序渐进（incremental evolution, not uncontrolled rewrite）**。
7. **代码、测试、产物目录、README/TREE 进度说明保持一致。**

---

## 1. 触发条件（When to trigger）

当用户的任务属于以下任一情况时，应使用本 skill：

- 修改、补全、重构 `VEVs/` 仓库中的代码、脚本、测试、配置或文档
- 评审当前改动是否违背 `casetwo.md` 的总体设计
- 设计或补充 Route A / Route B / Umbrella Sampling 相关模块
- 修复 `src/` 下各层之间职责混乱的问题
- 设计新增目录、类、模块、接口、I/O contract、测试策略
- 要求 README、TREE、脚本入口与当前项目状态保持同步
- 审查某段代码是否把 placeholder 伪装成 scientific result
- 审查某项改动是否破坏 membrane-ready architecture

以下情况通常**不**应触发：

- 与 VEVs 仓库无关的通用编程问题
- 单纯的文献讲解、概念解释且不涉及本仓库修改
- 纯粹的操作系统/代理/账号问题，与本项目代码结构无关
- 单纯要求翻译文本而不涉及项目实现

---

## 2. 项目总原则（Global Project Principles）

### 2.1 项目是分层架构，不是堆砌脚本
必须把下列层级明确区分：

1. **Structure Preparation**  
   结构准备层：输入校验、预处理、组装、manifest、metadata

2. **MD Execution**  
   模拟执行层：OpenMM 体系构建、最小化、平衡、生产模拟、reporters、artifacts

3. **Scientific Workflow**  
   科学工作流层：binding workflow、membrane binding workflow、umbrella workflow 的 orchestration

4. **Trajectory / Free-Energy Analysis**  
   分析层：RMSD、contacts、H-bonds、endpoint FE、PMF、膜分析

任何代码修改前，必须先判断它属于哪一层；禁止不加区分地在一个文件或一个类里混写多层逻辑。

### 2.2 `BindingWorkflow` 不是 MD engine
- `BindingWorkflow` / `MembraneBindingWorkflow` 负责 orchestration
- `AllAtomSimulation` 是唯一的 AA-MD 执行核心
- workflow 不应重新实现第二套 OpenMM 逻辑

### 2.3 分析层只消费结果，不制造结果
- `BindingAnalyzer`、`MembraneAnalyzer`、`EndpointFreeEnergyEstimator`、`PMFAnalyzer`
  只能基于真实 trajectory / topology / snapshots / metadata 分析
- 禁止在分析类中随机生成物理结果、伪造自由能、伪造膜指标
- placeholder 可以存在，但必须显式标注为 placeholder，且不得冒充 scientific evidence

### 2.4 Route A 先行，但必须 membrane-ready
Route A（solution mode）是当前主线，但任何设计都不得把项目锁死在 `receptor + ligand + water` 的死架构中。

必须从一开始预留：
- `mode='solution' | 'membrane'`
- `has_membrane`
- `MembraneConfig`
- solution / membrane protocol 分支
- analysis router 的扩展空间

### 2.5 Endpoint FE 与 Umbrella Sampling 不是一回事
- endpoint FE：快速 ranking / 初步证据
- umbrella sampling / PMF：路径分辨与机制论证

不得把二者混写为“同一计算”。

---

## 3. 当前项目真实边界（Current Real Boundaries）

在写任何新代码前，默认接受以下现实边界：

1. 当前仓库**已经**有清晰的目录分层雏形：`configs / interfaces / models / utils / analysis / scripts / tests / work / outputs`。
2. 当前主入口是 **Route A 最小闭环**，而不是 Route B 或 umbrella sampling。
3. `docking` 是 binding workflow 的一个阶段，不是全部 workflow。
4. `work/` 是过程产物目录，`outputs/` 是结果产物目录；不得混用。
5. `tests/` 中的 smoke tests / regression tests 是防回归资产，不得随意删除。
6. 任何尚未真实落地的高级物理流程，都必须诚实标识当前阶段与限制。

如果用户要求你“直接做完整 Route B”或“直接做 PMF 全套”，而当前执行层与 Route A 还不稳定，
你必须指出这属于**阶段跨越（phase jump）**，只能在不破坏主干的前提下做最小可兼容设计或占位接口。

---

## 4. 按 `casetwo.md` 推进的强制顺序（Mandatory Development Order）

默认遵循以下顺序，除非用户明确要求偏离，并且偏离不会破坏长期结构：

### Phase 0：冻结接口与职责
- configs dataclasses
- contracts / schemas
- 类职责与 I/O contract
- 目录结构与命名边界

### Phase 1：打通 Route A 最小可运行闭环
最低优先实现：
- `StructureRepository`
- `StructurePreprocessor`
- `DockingEngine` / docking backend integration
- `ComplexAssembler`
- `AllAtomSimulation` 主链
- `BindingAnalyzer` 最小指标
- `EndpointFreeEnergyEstimator` 最小快照提取

### Phase 2：平台 membrane-ready
- `has_membrane`
- `MembraneConfig`
- solution/membrane protocol 分支
- analysis router / membrane-safe I/O contract

### Phase 3：Route B 膜环境
- membrane embedding
- membrane equilibration
- membrane-aware analysis

### Phase 4：Umbrella Sampling / PMF
- CV definition
- window generation
- restrained window MD
- WHAM / MBAR reconstruction

禁止反向顺序大幅推进，例如在 Route A 还没有稳定 artifacts 与 tests 的前提下，重写大量 PMF 逻辑。

---

## 5. 每次改代码前的固定思考框架（Mandatory Pre-Edit Checklist）

在开始任何修改前，必须先执行以下判断，并把结论体现在你的实现与说明中：

1. **这是哪一层的问题？**
   - structure prep / execution / workflow / analysis / docs / tests

2. **它依赖哪些已有模块？**
   - configs
   - contracts
   - upstream inputs
   - downstream artifacts

3. **它会产生什么输入输出变化？**
   - 新文件路径
   - 新数据结构
   - 新 metadata
   - 新脚本参数
   - 新测试

4. **它是否破坏 Route A → B 的平滑升级？**
   - 是否把 membrane 逻辑写死在 solution-only 类里
   - 是否让 analysis 与 execution 耦合
   - 是否把 workflow 逻辑塞回 engine

5. **它是否超出当前阶段真实边界？**
   - 如果是，只能建立接口、占位契约、文档说明，不能伪装为已完成的科学流程

---

## 6. 编码规范（Coding Standards）

### 6.1 改动策略
- 优先小步提交（small incremental changes）
- 优先补齐缺失的 concrete component，而不是大面积推倒重写
- 对已有可运行链路保持尊重，不轻易破坏主入口与现有 smoke tests
- 对目录与命名做增量改良，不做无理由 rename storm

### 6.2 注释与可读性
- 新增或重构代码必须写**详细中文注释**
- 关键术语可带英文括注，例如：
  - 最小可运行闭环（minimum runnable loop）
  - 工作流编排（workflow orchestration）
  - 结构准备层（structure preparation layer）
- 注释应解释“为什么这样设计”，而不仅是“这行代码做了什么”
- 核心公开函数、类、脚本入口优先写 docstring，说明输入、输出、异常与阶段定位

### 6.3 命名与接口
- Python 标识符保持英文、语义稳定
- 避免使用含糊命名，如 `run_all`, `do_work`, `helper2`
- dataclass / config / contract 命名要与 `casetwo.md` 术语一致
- 新增接口优先使用显式参数与 dataclass，而不是层层传 dict

### 6.4 占位逻辑规范
允许存在 placeholder，但必须满足：
- 在注释和文档中明确写明 `placeholder` / `stub` / `not yet physical`
- 不生成会被误认为真实 scientific output 的数字
- 若必须返回示例输出，文件名或 metadata 中应显式注明 demo / placeholder 性质

---

## 7. 文档同步规范（Documentation Synchronization Rules）

### 7.1 README.md 必须与当前进度高度一致
当发生以下“重大改变”时，必须同步更新 `README.md`：

- 新增主入口脚本
- Route A 主链状态改变
- 新增可运行 workflow
- 新增或替换重要模块（如 `StructureRepository`、`BindingAnalyzer`）
- 目录结构明显变化
- 输出目录规则变化
- Phase 进度状态改变
- 从 placeholder 进入真实实现阶段

README 更新必须至少覆盖：
- 当前完成了什么
- 还没完成什么
- 当前主入口是什么
- 关键产物在哪里
- 下一步优先级是什么

### 7.2 TREE / 目录导览文件必须同步
若项目目录、脚本入口、产物位置、测试结构发生改变，也应同步更新 `TREE.md`（或等价目录导览文件）。

### 7.3 文档不能夸大完成度
- 未实现的功能不得写成“已完成”
- placeholder 结果不得写成“真实物理验证完成”
- 文档中的 phase 状态必须与代码事实一致

---

## 8. 测试与验证规范（Testing and Validation Rules）

### 8.1 改动应尽可能配套测试
当修改涉及以下内容时，应优先补相应测试：

- `utils/`：组件测试
- `analysis/`：smoke test / shape test / file-output test
- `workflows/`：端到端 smoke test
- `scripts/`：至少给出最小运行方式与参数说明

### 8.2 不轻易删除现有 tests
`tests/` 是防回归资产。除非测试本身已与仓库事实冲突，否则优先修复而非删除。

### 8.3 验证顺序
优先验证：
1. imports / typing / path usage
2. 最小单元测试
3. smoke workflow
4. artifacts 是否落在正确目录
5. README/TREE 是否同步

---

## 9. 目录与产物规范（Repository Layout and Artifact Rules）

### 9.1 目录清晰优先
默认遵守当前仓库分层：

- `src/configs`
- `src/interfaces`
- `src/models/workflows`
- `src/models/all_atom`
- `src/models/docking`
- `src/utils`
- `src/analysis`
- `scripts`
- `tests`
- `work`
- `outputs`

### 9.2 过程产物与结果产物分离
- `work/runs/<run_id>/...`：中间过程、MD artifacts、assembled structures
- `outputs/runs/<run_id>/...`：docking 结果、analysis 指标、metadata、reports

不得把：
- trajectory 临时文件乱放到 `outputs/`
- 报告与图像乱放到 `work/`

### 9.3 run_id 与可追踪性
新增 workflow、脚本或分析产物时，应尽量保持 `run_id` 级别的可追踪组织方式，保证：
- 输入来源可追踪
- 运行产物可回溯
- README/TREE 中描述的路径真实存在

---

## 10. 回答与执行风格（How to operate inside this repo）

当你实际执行任务时，默认按以下方式工作：

1. **先短暂判定层级与阶段**
2. **阅读相关文件，避免脱离现有仓库现实**
3. **给出最小必要改动方案**
4. **优先修改最核心且可闭环的一小段**
5. **说明这次改动如何对齐 `casetwo.md`**
6. **若有重大改动，同步更新 README/TREE**
7. **总结未解决边界，诚实说明下一步**

如果用户要求你“直接补全很多文件”，也应优先：
- 先保证主链闭环
- 再补外围扩展
- 不要制造看起来很大、实际上不可运行的伪完整架构

---

## 11. 明确禁止事项（Hard Prohibitions）

禁止出现以下行为：

1. 把多层逻辑混进同一类，只为“省事”
2. 在 workflow 层直接内嵌大量 OpenMM 细节
3. 在 analysis 层伪造物理量或自由能
4. 把 placeholder 当作真实 scientific result 叙述
5. 在 Route A 尚未稳定时进行不可控的大重构
6. 大规模 rename / move 导致仓库可运行性下降，却没有同步测试与 README
7. 让 README 与代码现状脱节
8. 忽略现有 `TREE` 指示的目录与 artifact 规则
9. 未说明理由就删除 tests、scripts、work/outputs 结构
10. 为了“显得完整”而加入与当前阶段不匹配的复杂模块

---

## 12. 推荐附加动作（Recommended Additional Behaviors）

以下不是可选装饰，而是高价值默认行为：

- 对重大改动补 `README.md` 更新
- 对目录变化补 `TREE.md` 更新
- 对新增模块补最小 smoke test
- 对新文件头部写阶段定位注释（例如：Route A concrete component / membrane-ready placeholder）
- 对可能误解为真实结果的部分，加入边界说明
- 对用户每次新增需求，判断其属于 Phase 0/1/2/3/4 中哪一阶段

---

## 13. 输出时建议包含的最小信息（Recommended Output Shape）

在处理本仓库任务时，优先给出：

1. **本次修改属于哪一层 / 哪一阶段**
2. **本次新增或修改了哪些文件**
3. **为什么这些改动符合 `casetwo.md`**
4. **是否需要同步更新 README/TREE**
5. **当前仍然存在的边界或未完成项**
6. **一个适合记录到飞书的精简总结**

---

## 14. 与当前仓库状态的对齐提醒（Alignment Reminder）

默认假定当前仓库已经具备：

- `src/configs/`
- `src/interfaces/`
- `src/models/workflows/`
- `src/models/all_atom/`
- `src/models/docking/`
- `src/utils/`
- `src/analysis/`
- `scripts/run_binding_route_a.py`
- `scripts/run_minimal_openmm_validation.py`
- `tests/`
- `work/runs/`
- `outputs/runs/`

如果实际代码与此不一致，必须以仓库事实为准，然后在 README/TREE 中同步更新。

---

## 15. 最终准则（Final Rule）

任何时候都优先追求：

**真实、分层、可运行、可追踪、可升级、可复现。**

而不是：

**表面完整、叙事华丽、结构混乱、边界失真。**
