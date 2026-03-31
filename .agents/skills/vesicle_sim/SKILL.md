---
name: vesicle_sim
description: 用于 VEVs 仓库中任何需要执行 Python、pytest、npm、构建脚本或前后端验证命令的任务。默认运行环境是 WSL 内 miniconda 的 `vesicle_sim` 环境，凡是命令执行、依赖检查、测试和构建验证都应优先触发。
---

# vesicle_sim 技能说明

## 1. 核心定位

这个技能负责统一项目运行环境，避免因为 shell 上下文不同而误判依赖缺失或测试失败。

默认事实：

- 本项目长期在 WSL 中运行
- 默认 Python 环境是 miniconda 的 `vesicle_sim`
- 只要任务涉及命令执行，就优先在这个环境中完成

## 2. 什么时候使用

- 运行 `python` 脚本
- 跑 `pytest`
- 跑 `npm run lint` / `npm run build`
- 检查 `python`、`pytest`、`node`、`npm`
- 验证项目脚本是否可执行

## 3. 标准激活方式

优先使用：

```bash
source /home/sakura0329/miniconda3/etc/profile.d/conda.sh && conda activate vesicle_sim
```

如果只执行单条命令，可以优先用：

```bash
conda run -n vesicle_sim <command>
```

## 4. 工作规则

- 先进入 `vesicle_sim`，再判断依赖是否存在
- 不要基于未激活环境的结果下结论
- Python 验证和前端验证都应复用这个环境
- 如果执行失败，先区分是代码问题还是环境问题

## 5. 最低预检

按任务需要选择：

- `python --version`
- `python -m pytest --version`
- `node -v`
- `npm -v`

## 6. references 使用规则

执行具体命令前，可读取：

- `references/runtime-commands.md`

## 7. 交付要求

- 在说明中明确是否已经进入 `vesicle_sim`
- 若测试或构建失败，要说明失败来自环境还是代码
