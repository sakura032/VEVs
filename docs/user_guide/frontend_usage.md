# Frontend Usage Guide

## Start Development Server

```bash
cd frontend
npm install
npm run dev
```

## Build Checks

```bash
cd frontend
npm run lint
npm run build
```

## Data Preparation

Whole Vesicle Explorer 读取的是 `frontend/visualization/vesicle/` 下的数据集。

推荐流程：

1. 先在项目根目录生成或更新一个 vesicle 数据集

```bash
python scripts/vesicle_build.py --output-dir outputs/vesicle/<dataset_id>
```

2. 再把该数据集同步到前端可视化目录

```bash
python scripts/vesicle_sync_frontend.py --source-dir outputs/vesicle/<dataset_id>
```

3. 启动前端，在 `Whole Vesicle Explorer` 中选择该数据集

## Current Routes

- `Whole Vesicle Explorer`
  - 当前真实业务页
  - 用于浏览 vesicle 数据集
- `Workspace`
  - 当前为占位页
  - 用于后续模块接入
