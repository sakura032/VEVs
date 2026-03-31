---
name: frontend-validation
description: 用于 VEVs 仓库中前端改动后的验证任务，主要覆盖 `frontend/`、`frontend/visualization/vesicle/` 以及与前端加载路径相关的脚本联动。凡是前端源码、可视化数据路径、前端文档或页面行为修改后都应触发。
---

# frontend-validation 技能说明

## 1. 核心定位

这个技能负责前端侧的最小可信验证，确保页面改动、路径改动和构建改动不会在交付时出问题。

## 2. 默认环境

执行验证时，默认复用 `vesicle_sim` 定义的运行环境。

## 3. 最低验证原则

- 改了前端源码，至少跑 `npm run lint` 和 `npm run build`
- 改了 loader 或数据路径，要同时确认目标数据文件存在
- 改了路由或页面装配，要检查当前页面说明是否还成立

## 4. references 使用规则

具体验证矩阵见：

- `references/checklist.md`

## 5. 交付要求

- 说明运行了哪些前端检查
- 说明是否检查了可视化数据目录
- 构建失败时要区分环境问题和代码问题
