---
name: governance
description: 用于 VEVs 仓库内任何涉及目录边界、模块职责、跨目录重构、长期演进方向或主干规则判断的任务。凡是改动会影响 `src/`、`frontend/`、`data/`、`outputs/`、`docs/`、`scripts/` 或 `.agents/` 的职责分层时触发。
---

# governance 技能说明

## 1. 核心定位

这个技能负责仓库级治理，不直接替代具体实现技能，而是确保改动不会破坏当前项目已经稳定下来的主干结构。

当前默认主干是：

- `src/vesicle/` 负责核心 Python 领域代码
- `frontend/` 负责当前前端可视化框架
- `data/`、`outputs/`、`docs/`、`logs/`、`config/` 负责项目级组织结构

## 2. 什么时候使用

出现以下任一情况时，应优先使用本技能：

- 调整目录结构
- 移动或重命名跨目录文件
- 设计新模块放在哪一层
- 判断某个功能应属于 `src/`、`scripts/`、`frontend/` 还是 `docs/`
- 审查改动是否重新引入旧的 legacy binding 叙事
- 更新 `.agents` 本身

## 3. 不负责什么

以下任务不应主要依赖本技能：

- 单个算法函数的局部实现
- 单个前端组件的局部样式微调
- 纯测试命令执行
- 单纯的 README 文案润色

这些任务应分别交给 `main`、`frontend`、`python-validation`、`frontend-validation` 或 `docs`。

## 4. 当前治理原则

- 不重新引入已经移除的旧 docking / binding / `work/` 主线
- 任何结构变化都要同步更新对应文档
- 技能维护本身是正常开发的一部分，不是额外补丁
- 技能只写工作方式与守门规则，不重复堆砌项目事实
- 项目事实优先以根 `README.md` 和 `docs/` 为准

## 5. 工作流程

处理仓库级任务时，按这个顺序推进：

1. 先读根 `README.md`
2. 如果涉及前端边界，再读 `docs/design/frontend_architecture.md`
3. 判断问题属于哪一层：领域代码、前端、文档、验证、结构迁移
4. 只改本层应该改的内容，不把多层逻辑混在一个文件里
5. 若改动了路径、命令、契约或职责边界，同步更新 docs 和相关 skills

## 6. references 使用规则

需要确认仓库当前边界时，读取：

- `references/repo-boundaries.md`

需要更新或审查 `.agents` 时，读取：

- `references/skills-maintenance.md`

## 7. 最低交付要求

- 结构调整必须说明为什么这样分层
- 路径变化必须同步 README 或 docs
- `.agents` 变更必须同步 `agents/openai.yaml`
