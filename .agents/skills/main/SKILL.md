---
name: main
description: 用于 VEVs 仓库当前主干模块的开发任务，主要覆盖 `src/vesicle/`、`tests/vesicle/`、`data/vesicle/`、`outputs/vesicle/` 和 `scripts/vesicle_*.py`。当任务属于 vesicle 领域代码、数据契约、主入口脚本或对应测试时触发。
---

# main 技能说明

## 1. 核心定位

这个技能服务于当前项目最稳定、最核心的主干能力，也就是 vesicle 相关的 Python 代码与数据链路。

## 2. 适用范围

- `src/vesicle/`
- `tests/vesicle/`
- `data/vesicle/`
- `outputs/vesicle/`
- `scripts/vesicle_build.py`
- `scripts/vesicle_sync_frontend.py`

## 3. 当前主干规则

- 优先保持 `src/vesicle/` 的边界清晰
- `models/` 放领域对象与 builder
- `utils/` 放支撑性的通用空间计算
- 不重新引入旧 docking / binding 逻辑
- 改动核心逻辑时，优先补测试
- 新增代码注释和 docstring 使用 UTF-8 中文

## 4. 工作流程

1. 先确认改动属于领域代码、脚本还是数据契约
2. 如果触及输入输出路径，再检查 `references/data-contract.md`
3. 如果触及模块职责，再检查 `references/domain-layout.md`
4. 改完后按需交给 `python-validation`
5. 若入口、结构或契约变化明显，再同步 `docs`

## 5. 不应做什么

- 不把前端展示逻辑塞进 Python 主干
- 不把临时脚本当成长期入口
- 不把试验性数据格式直接写死成稳定契约

## 6. references 使用规则

需要确认当前主干布局时，读取：

- `references/domain-layout.md`

需要确认当前输入输出契约时，读取：

- `references/data-contract.md`

## 7. 最低交付要求

- 主干改动应有清晰职责说明
- 路径或契约变化应同步 README / docs
- 需要验证时应调用 `python-validation`
