# Python 验证矩阵

## 1. 纯语法与导入层改动

推荐至少执行：

```bash
conda run -n vesicle_sim python -m compileall src scripts tests
```

## 2. `src/vesicle/` 或 `tests/vesicle/` 改动

推荐至少执行：

```bash
conda run -n vesicle_sim python -m pytest tests/vesicle
```

## 3. 入口脚本改动

推荐按情况补充：

```bash
conda run -n vesicle_sim python scripts/vesicle_build.py --help
```

```bash
conda run -n vesicle_sim python scripts/vesicle_sync_frontend.py --help
```

## 4. 数据契约改动

如果改动影响了输出路径或同步逻辑，除测试外还应说明：

- 目标输出目录是什么
- 前端同步目标是什么
- 是否需要人工核对生成结果
