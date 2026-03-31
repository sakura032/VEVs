# 文档同步检查清单

## 1. 以下变化必须同步文档

- 根目录结构变化
- 新增或删除入口脚本
- 数据目录分层变化
- 输出目录和可视化目录变化
- 前端路由变化
- 测试方式变化
- 默认运行环境变化
- `.agents` 技能体系变化

## 2. 常见同步位置

- 项目入口变化
  - 更新根 `README.md`
- 前端结构变化
  - 更新 `docs/design/frontend_architecture.md`
- 前端使用步骤变化
  - 更新 `docs/user_guide/frontend_usage.md`
- skill 体系变化
  - 更新 `docs/user_guide/` 下的技能使用教程

## 3. 文档自检

文档写完后至少检查：

1. 路径是否真实存在
2. 命令是否仍可执行
3. 描述是否夸大当前完成度
4. 是否还残留旧 binding / legacy 叙事
