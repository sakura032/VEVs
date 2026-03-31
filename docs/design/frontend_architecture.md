# Frontend Architecture

## Overview

当前前端已经整理成 feature-first 结构，并且只保留 vesicle 数据集链路。

前端现在保留双路由壳，但只保留一个真实业务模块：

- `Whole Vesicle Explorer`
  - 当前唯一真实业务页
  - 读取 `frontend/visualization/vesicle/index.json`
  - 加载 `.gro` / `.top` 数据集并提供筛选、裁切和显示模式切换
- `Workspace`
  - 占位页
  - 用于后续模块接入
  - 不再加载历史 run bundle

## Source Layout

```text
frontend/src/
  app/
    App.jsx
    AppShell.jsx
    providers.jsx
    routes.js
  pages/
    WholeVesicleExplorerPage.jsx
    WorkspacePage.jsx
  features/
    vesicle-explorer/
      components/
      constants/
      hooks/
      services/
      utils/
    workspace/
      components/
      constants/
  shared/
    components/
      common/
      layout/
    styles/
  lib/
    loaders/
```

## Boundary Rules

- `app/`
  - 应用壳与全局路由切换
- `pages/`
  - 路由级页面装配层
  - 只负责组合 feature，不直接承载底层业务解析
- `features/`
  - 每个业务模块自己的组件、hooks、services、constants、utils
  - 当前真实模块是 `vesicle-explorer`
  - `workspace` 作为未来模块入口占位
- `shared/`
  - 跨 feature 复用的通用 UI 与样式
  - 不应吸收 vesicle 专属逻辑
- `lib/`
  - 通用 loader 和底层读写能力
  - 不承载页面语义和业务命名

## Vesicle Data Contract

当前前端只认这一套稳定契约：

- `frontend/visualization/vesicle/index.json`
- `frontend/visualization/vesicle/<dataset_id>/vesicle.gro`
- `frontend/visualization/vesicle/<dataset_id>/topol.top`
- `frontend/visualization/vesicle/<dataset_id>/meta.json`

当前不会再读取：

- run-based artifact bundles
- pose table
- RMSD / MD log / report viewer
- legacy metrics JSON

## Extension Rule

新增模块时遵循这条规则：

1. 新建 `features/<feature-name>/`
2. 把该模块的组件、hooks、services、constants、utils 关在 feature 内
3. 在 `pages/` 增加一个薄页面做路由装配
4. 只有真正跨模块复用的能力，才提升到 `shared/` 或 `lib/`
