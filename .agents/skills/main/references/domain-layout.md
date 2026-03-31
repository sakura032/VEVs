# 当前主干布局参考

## 1. Python 主代码

当前核心代码位于：

- `src/vesicle/models/lipid.py`
- `src/vesicle/models/protein.py`
- `src/vesicle/models/vesicle_builder.py`
- `src/vesicle/utils/placement.py`

## 2. 当前职责理解

- `lipid.py`
  - 脂质蓝图与模板标准化
- `protein.py`
  - 蛋白模板读取与几何缓存
- `vesicle_builder.py`
  - 囊泡总装主流程
- `placement.py`
  - 球面布点、对齐、扰动、碰撞检测等空间放置原语

## 3. 脚本入口

当前稳定脚本入口：

- `scripts/vesicle_build.py`
- `scripts/vesicle_sync_frontend.py`

## 4. 测试入口

当前测试主干：

- `tests/vesicle/test_builder.py`
- `tests/vesicle/test_factory.py`
- `tests/vesicle/test_placement.py`
- `tests/vesicle/test_protein.py`

## 5. 使用建议

当任务会跨越多个文件时，先判断它属于：

- 领域模型
- 空间工具
- 脚本入口
- 数据契约
- 测试

不要直接把这些层次揉成一个改动理由。
