# 前端源码结构参考

## 1. 当前结构

`frontend/src/` 当前按 feature-first 组织：

- `app/`
  - 应用壳、路由、全局装配
- `pages/`
  - 路由级页面装配
- `features/`
  - 业务模块主体
- `shared/`
  - 通用样式和共享组件
- `lib/`
  - loader 和底层工具

## 2. 当前业务模块

- `features/vesicle-explorer/`
  - 当前唯一真实业务模块
- `features/workspace/`
  - 未来模块占位

## 3. 关键边界

- 页面负责装配，不负责底层解析
- feature 负责业务闭合
- shared 不应携带业务专属语义
- lib 不应携带页面命名

## 4. 变更提醒

当你改变了：

- 页面路由
- feature 边界
- 共享组件职责
- loader 位置

就需要同步检查 README 和前端文档。
