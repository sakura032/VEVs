---
name: frontend
description: 仅用于 VEVs 仓库中 `frontend` 目录及其与 `vesicle/outputs`、`frontend/public/visualization` 的可视化联动开发。处理 React/Vite/Three.js、GRO 前端可视化、静态资产同步、前端构建验证时，必须优先使用 WSL2 的交互式 shell，激活 Ubuntu 中的 `vesicle_sim` conda 环境，再检查 `node`、`npm`、`node_modules` 和 `vite`。禁止仅根据 Windows shell 或非交互式 WSL 结果判断前端环境缺失。
---

# Frontend 技能说明

## 1. 适用范围

- 本技能只用于 `VEVs/frontend` 目录相关任务。
- 也适用于 `vesicle/outputs` 产物同步到 `frontend/public/visualization` 的联动场景。

## 2. 环境原则

- 前端开发环境的真实来源是：
  - WSL2 Ubuntu
  - 交互式 shell
  - `conda activate vesicle_sim`
- 不能把以下结果当作最终结论：
  - Windows PowerShell 中 `vite` 不存在
  - 非交互式 `wsl.exe bash -lc ...` 中 `node` / `npm` 不存在
  - Windows 侧 `frontend/node_modules` 不存在

这些都只能说明“当前这个 shell 上下文不可用”，不能说明前端环境真的没配好。

## 3. 强制工作流

只要任务涉及 `frontend/` 的运行、构建、安装依赖、验证页面、three.js 可视化，必须优先按这个顺序做：

1. 使用 **WSL2 交互式 shell**，不要先用 Windows shell 结论做判断。
2. 在 WSL 中执行：
   - `source /home/sakura0329/miniconda3/etc/profile.d/conda.sh`
   - `conda activate vesicle_sim`
3. 在激活后立刻验证：
   - `python --version`
   - `node -v`
   - `npm -v`
4. 再进入项目：
   - `cd /mnt/d/scientific/casetwo/VEVs/frontend`
5. 再检查依赖：
   - `test -d node_modules && echo node_modules_exists || echo node_modules_missing`
6. 若 `node_modules` 缺失，再执行 `npm install`
7. 构建验证优先执行：
   - `npm run build`
8. 开发预览再执行：
   - `npm run dev`

推荐命令模式：

```bash
wsl.exe bash -ic "source /home/sakura0329/miniconda3/etc/profile.d/conda.sh && conda activate vesicle_sim && cd /mnt/d/scientific/casetwo/VEVs/frontend && node -v && npm -v && npm run build"
```

## 4. 失败时的判断规则

- 如果 Windows 里 `vite` 不存在：
  - 先不要下结论
  - 先去 WSL 交互式 `vesicle_sim` 里验证
- 如果非交互式 WSL 看不到 `node` / `npm`：
  - 先怀疑 shell 初始化路径差异
  - 必须改用 `bash -ic`
- 如果 Windows 里没有 `frontend/node_modules`：
  - 不代表 WSL 交互式环境不可用
  - 先在 WSL 交互式 shell 里检查项目目录
- 只有在 **WSL 交互式 + vesicle_sim 已激活** 的前提下，`node` / `npm` / `node_modules` 仍然缺失，才能判定前端环境真的没配齐

## 5. 目录与数据联动规则

处理囊泡前端可视化时，优先使用：

- 输入产物：
  - `vesicle/outputs/basic_vesicle/vesicle.gro`
  - `vesicle/outputs/basic_vesicle/topol.top`
- 前端静态可视化目录：
  - `frontend/public/visualization/vesicle/basic_vesicle/`

如果 `vesicle/outputs/basic_vesicle/` 有新产物，而前端仍在显示旧数据，必须先同步静态文件，再谈前端 bug。

## 6. VEVs 前端的当前约定

- 技术栈：
  - React
  - Vite
  - three.js
  - react-three-fiber
- 整颗囊泡可视化的默认策略：
  - 先用 `.gro` loader
  - 整体默认点云
  - 局部筛选后才切到 spheres
- 不要把整颗 `vesicle.gro` 强行塞进现有 PDB 工作流再判断性能问题
- 优先走囊泡专页，而不是直接复用 docking / PDB 主链路

## 7. 修改 frontend 代码时的最低验证

只要改动了 `frontend/` 中的代码，默认至少做：

1. `npm run build`
2. 若改了静态结构数据路径或 loader：
   - 验证目标文件确实存在于 `frontend/public/visualization/...`
3. 若改了 whole vesicle 页面：
   - 说明默认加载的 GRO 路径
   - 说明当前默认显示模式（points / spheres）

## 8. 沟通要求

- 明确告诉用户你当前是否已经：
  - 进入 WSL 交互式 shell
  - 激活 `vesicle_sim`
  - 验证 `node -v` / `npm -v`
  - 验证 `node_modules`
- 不要再用“frontend 没装依赖”这类结论性表述，除非已经完成上面的强制检查链路。
