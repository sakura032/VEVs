# 当前仓库边界参考

## 1. 当前主干

当前仓库已经收敛到一条更清晰的主干：

- Python 代码主干在 `src/vesicle/`
- Python 测试主干在 `tests/vesicle/`
- 前端主干在 `frontend/`
- 数据模板主干在 `data/vesicle/`
- 输出主干在 `outputs/vesicle/`

## 2. 已经明确删除的旧路线

以下内容不应再被重新引入主干：

- 旧 docking / binding 主线
- `work/` 过程产物目录
- 旧 `frontend/public/visualization` 静态资源路径
- 旧 `vesicle/` 子项目式目录

## 3. 当前根目录的职责划分

- `config/`
  - 预留给集中配置文件
- `data/`
  - 放模板、原始数据、处理中数据和临时数据
- `docs/`
  - 放正式文档
- `logs/`
  - 放运行日志
- `outputs/`
  - 放生成产物
- `scripts/`
  - 放项目级脚本入口
- `src/`
  - 放核心源码
- `tests/`
  - 放测试
- `frontend/`
  - 放前端应用和可视化数据目录
- `.agents/`
  - 放技能定义

## 4. 当前文档事实来源

需要确认项目事实时，优先查看：

1. 根 `README.md`
2. `docs/design/frontend_architecture.md`
3. `docs/user_guide/frontend_usage.md`

本参考文件只负责帮助技能快速判断边界，不代替正式文档。
