# Skills 使用教程

## 1. 这份文档的作用

这份文档说明当前项目 `.agents/skills/` 体系如何使用、各个 skill 分别负责什么，以及后续应该如何维护这套技能系统。

现在的设计目标不是“把所有规则塞进一个大 skill”，而是把技能拆成边界清晰、职责单一、可长期维护的几层能力。

## 2. 当前技能列表

当前项目已经整理为以下 skills：

- `governance`
  - 仓库级治理、边界判断和长期演进守门
- `vesicle_sim`
  - 默认运行环境与命令执行规范
- `main`
  - `src/vesicle/` 主干代码、数据契约和对应测试
- `frontend`
  - 前端应用架构与 vesicle 可视化
- `docs`
  - README 与 `docs/` 体系同步
- `python-validation`
  - Python 改动后的最小可信验证
- `frontend-validation`
  - 前端改动后的最小可信验证
- `structure`
  - 目录迁移、文件重命名和结构整理

## 3. 技能分层理解

可以把这套 skills 理解成四层：

- 治理层
  - `governance`
- 环境层
  - `vesicle_sim`
- 业务层
  - `main`
  - `frontend`
  - `docs`
- 质量与重构层
  - `python-validation`
  - `frontend-validation`
  - `structure`

这样拆分的好处是：一个 skill 只解决一种问题，后续更新时不会互相污染。

## 4. 每个 skill 适合什么时候用

### `governance`

在这些场景下优先用：

- 你不确定某个功能该放在哪一层
- 你要做跨目录重构
- 你要调整项目长期结构
- 你要修改 `.agents` 本身

典型表达方式：

```text
$governance 检查这次目录迁移是否符合当前仓库的结构边界
```

### `vesicle_sim`

这个环境和路径是为fty的电脑量身定制的，远程连接wsl使用conda环境，其他两人无法直接使用，可仿照定制个人专属环境的skills。在这些场景下优先用：

- 你要运行 Python 脚本
- 你要跑 `pytest`
- 你要跑前端 lint 或 build
- 你要确认依赖是否在默认环境里

典型表达方式：

```text
$vesicle_sim 在默认环境里执行这次 Python 和前端验证
```

### `main`

在这些场景下优先用：

- 你要改 `src/vesicle/`
- 你要改 `tests/vesicle/`
- 你要改 vesicle 主入口脚本
- 你要调整主干数据契约

典型表达方式：

```text
$main 修改 vesicle builder，并同步更新对应测试
```

### `frontend`

在这些场景下优先用：

- 你要改前端页面或 feature
- 你要改 loader
- 你要改前端可视化数据读取路径
- 你要整理前端架构边界

典型表达方式：

```text
$frontend 整理 Whole Vesicle Explorer 的数据加载和页面结构
```

### `docs`

在这些场景下优先用：

- 你要更新根 README
- 你要同步 `docs/`
- 你要写技能教程或使用说明
- 目录、命令、契约已经变化，需要同步文档

典型表达方式：

```text
$docs 根据最新的项目结构重写 README 和用户指南
```

### `python-validation`

在这些场景下优先用：

- 你改了 Python 代码后需要验证
- 你改了脚本入口后需要补 CLI 检查
- 你改了数据契约后要补 Python 侧核验

典型表达方式：

```text
$python-validation 为这次 Python 改动执行最小验证集合
```

### `frontend-validation`

在这些场景下优先用：

- 你改了前端源码
- 你改了前端数据路径
- 你改了页面装配或路由

典型表达方式：

```text
$frontend-validation 为这次前端改动执行 lint、build 和数据路径检查
```

### `structure`

在这些场景下优先用：

- 你要搬文件
- 你要重命名模块
- 你要拆分或合并文件
- 你要清理旧目录

典型表达方式：

```text
$structure 把这个模块迁移到新目录，并同步更新 import、测试和文档
```

## 5. 推荐使用顺序

复杂任务时，不要只靠一个 skill 硬撑到底。推荐按任务链路组合使用：

1. 先用 `governance` 判断边界
2. 涉及命令执行时用 `vesicle_sim`
3. 改 Python 主干时用 `main`
4. 改前端时用 `frontend`
5. 改完后用 `python-validation` 或 `frontend-validation`
6. 如果发生目录迁移，再加 `structure`
7. 如果 README / docs 落后了，再加 `docs`

## 6. references 怎么看

每个 skill 目录下都带有 `references/`。这些文件不是额外装饰，而是细节规则的承载位置。

设计原则是：

- `SKILL.md` 放工作流程和守门规则
- `references/` 放详细路径、检查清单和补充说明

这样可以保证：

- skill 主体足够短
- 触发逻辑足够清晰
- 细节仍有地方可查

## 7. 后续如何维护 skills

这部分非常重要。以后 skills 不应被当成“一次性整理结果”，而应被当成项目的一部分持续维护。

建议遵循以下规则：

- 目录变化时，检查 `governance` 和 `structure`
- 默认环境变化时，检查 `vesicle_sim`
- Python 主干或数据契约变化时，检查 `main` 和 `python-validation`
- 前端架构或前端数据路径变化时，检查 `frontend` 和 `frontend-validation`
- README、docs 或使用方式变化时，检查 `docs`

每次维护 skill 时，至少检查：

1. `SKILL.md` 的适用范围是否仍然准确
2. `references/` 是否仍然和当前仓库一致
3. `agents/openai.yaml` 是否仍然和正文一致
4. 是否存在旧 skill 已经过时，应当删除而不是继续保留

## 8. 维护中的反模式

应避免以下情况：

- 一个 skill 写得过长，什么都想管
- README 和 skill 说法互相冲突
- 旧 skill 不删，导致新旧规则并存
- skill 里重复写大量项目事实，后续必须双份维护

## 9. 实际维护建议

以后最稳的方式是把 skill 更新和代码更新放在同一轮任务里完成。

例如：

- 你搬了目录
  - 同步更新 `structure`
  - 同步更新 `governance`
  - 必要时同步更新 `README.md`
- 你改了前端路径
  - 同步更新 `frontend`
  - 同步更新 `frontend-validation`
  - 必要时同步更新前端文档
- 你改了 Python 主入口
  - 同步更新 `main`
  - 同步更新 `python-validation`

这样做的结果是：技能体系会自然跟着项目演化，而不是等堆积很久以后再大修一次。
