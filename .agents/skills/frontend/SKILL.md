---
name: frontend
description: 用于 VEVs 仓库中 `frontend/` 及其与 `frontend/visualization/vesicle/` 数据契约相关的任务。凡是修改 React 页面、feature-first 结构、loader、可视化数据读取路径或前端文档时触发。
---

# frontend 技能说明

## 1. 核心定位

这个技能只处理当前前端应用本体，以及它和 vesicle 数据集之间的连接方式。

## 2. 适用范围

- `frontend/src/`
- `frontend/visualization/vesicle/`
- `frontend/README.md`
- 与前端展示直接相关的 docs

## 3. 当前前端边界

- 当前只有一个真实业务模块：`Whole Vesicle Explorer`
- `Workspace` 是未来模块占位页
- 前端采用 feature-first 结构
- `pages/` 只做页面装配
- `features/` 承载业务逻辑
- `shared/` 只放跨模块复用内容
- `lib/` 放 loader 等底层能力

## 4. 工作流程

1. 先确认改动属于页面装配、业务 feature、共享组件还是 loader
2. 若触及数据路径，先读 `references/visualization-contract.md`
3. 若触及结构分层，先读 `references/source-layout.md`
4. 改完后交给 `frontend-validation`
5. 若路由、架构或使用方式变了，再同步 `docs`

## 5. 不应做什么

- 不把 vesicle 专属逻辑塞进 `shared/`
- 不把页面文件变成超大逻辑文件
- 不重新接回旧 binding 页面和旧 artifact 体系

## 6. 运行环境

执行前端命令时，默认复用 `vesicle_sim` 技能定义的环境规则。

## 7. references 使用规则

需要确认源码结构时，读取：

- `references/source-layout.md`

需要确认可视化数据契约时，读取：

- `references/visualization-contract.md`

## 8. 最低交付要求

- 改动必须符合 feature-first 边界
- 数据路径变化必须同步文档和验证步骤
- 前端代码改动后应调用 `frontend-validation`
