# 主干数据契约参考

## 1. 输入目录

当前稳定输入位于：

- `data/vesicle/forcefields/`
- `data/vesicle/lipids/`
- `data/vesicle/proteins/`

## 2. 输出目录

当前稳定输出位于：

- `outputs/vesicle/<dataset_id>/vesicle.gro`
- `outputs/vesicle/<dataset_id>/topol.top`

## 3. 前端同步目标

同步后的前端目录位于：

- `frontend/visualization/vesicle/index.json`
- `frontend/visualization/vesicle/<dataset_id>/vesicle.gro`
- `frontend/visualization/vesicle/<dataset_id>/topol.top`
- `frontend/visualization/vesicle/<dataset_id>/meta.json`

## 4. data 根目录的分层

当前 `data/` 的根层次语义是：

- `data/raw/`
  - 原始数据
- `data/processed/`
  - 清洗或标准化后的数据
- `data/external/`
  - 外部来源数据
- `data/interim/`
  - 临时中间结果
- `data/vesicle/`
  - 当前主干模块正式使用的模板与静态输入

## 5. 使用建议

如果你改变了这些路径、文件名或元数据字段，就不再是单纯代码改动，而是契约改动；这时必须同步：

- 代码
- 测试
- README 或 docs
