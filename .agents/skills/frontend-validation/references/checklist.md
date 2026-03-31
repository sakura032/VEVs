# 前端验证矩阵

## 1. 前端源码改动

推荐至少执行：

```bash
source /home/sakura0329/miniconda3/etc/profile.d/conda.sh && conda activate vesicle_sim && cd /home/sakura0329/projects/VEVs/frontend && npm run lint
```

```bash
source /home/sakura0329/miniconda3/etc/profile.d/conda.sh && conda activate vesicle_sim && cd /home/sakura0329/projects/VEVs/frontend && npm run build
```

## 2. loader 或数据路径改动

除构建外，还应检查：

- `frontend/visualization/vesicle/index.json` 是否存在
- 目标数据集目录是否存在
- `meta.json`、`vesicle.gro`、`topol.top` 是否齐全

## 3. 路由或页面结构改动

应补充说明：

- 当前真实业务页仍是什么
- 占位页是否仍然只承担未来模块入口
- 文档是否需要同步更新
