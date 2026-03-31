# 前端可视化数据契约参考

## 1. 当前稳定路径

前端当前只认这一套路径：

- `frontend/visualization/vesicle/index.json`
- `frontend/visualization/vesicle/<dataset_id>/vesicle.gro`
- `frontend/visualization/vesicle/<dataset_id>/topol.top`
- `frontend/visualization/vesicle/<dataset_id>/meta.json`

## 2. 当前数据发现方式

- 先读取 `index.json`
- 再按数据集读取 `meta.json`
- 再读取结构和拓扑文件

## 3. 当前不再支持的旧模式

以下模式不应重新接回：

- run-based bundle
- 旧 binding metrics
- 旧 report viewer
- `frontend/public/visualization`

## 4. 变更提醒

如果你改变了：

- `index.json` 字段
- `meta.json` 字段
- 数据集目录结构
- loader 的读取路径

就必须同步：

- 前端实现
- 脚本实现
- README 或 docs
