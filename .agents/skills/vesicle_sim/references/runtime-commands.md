# 运行环境命令参考

## 1. 默认仓库路径

当前仓库路径：

- `/home/sakura0329/projects/VEVs`

## 2. 激活命令

推荐链路：

```bash
source /home/sakura0329/miniconda3/etc/profile.d/conda.sh && conda activate vesicle_sim
```

## 3. 常用命令模板

Python 测试：

```bash
conda run -n vesicle_sim python -m pytest tests/vesicle
```

Python 语法检查：

```bash
conda run -n vesicle_sim python -m compileall src scripts tests
```

前端 lint：

```bash
source /home/sakura0329/miniconda3/etc/profile.d/conda.sh && conda activate vesicle_sim && cd /home/sakura0329/projects/VEVs/frontend && npm run lint
```

前端 build：

```bash
source /home/sakura0329/miniconda3/etc/profile.d/conda.sh && conda activate vesicle_sim && cd /home/sakura0329/projects/VEVs/frontend && npm run build
```

## 4. 判断原则

- 没有激活 `vesicle_sim` 之前，不要判断 `pytest` 缺失
- 没有进入正确前端目录之前，不要判断 `npm` 脚本缺失
- 命令失败时，先看环境，再看代码
