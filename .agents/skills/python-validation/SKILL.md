---
name: python-validation
description: 用于 VEVs 仓库中 Python 侧改动后的验证任务，主要覆盖 `src/`、`scripts/`、`tests/` 和与 `data/vesicle/`、`outputs/vesicle/` 契约有关的变更。凡是 Python 代码、入口脚本或主干契约修改后都应触发。
---

# python-validation 技能说明

## 1. 核心定位

这个技能负责 Python 侧的最小可信验证，不负责实现功能，只负责确认改动后的主干还能站得住。

## 2. 默认环境

执行验证时，默认复用 `vesicle_sim` 定义的运行环境。

## 3. 最低验证原则

- 只改了文档或纯注释，不必强行跑全套测试
- 改了 Python 代码，至少做语法级检查
- 改了主干逻辑或测试文件，应跑 `pytest`
- 改了脚本入口或数据契约，应补 CLI 或链路级检查

## 4. references 使用规则

具体按什么矩阵验证，读取：

- `references/checklist.md`

## 5. 交付要求

- 清楚说明跑了哪些检查
- 如果没跑某项验证，要说明原因
- 如果失败，要说明是环境、数据还是代码问题
