# Example invocations

## Explicit invocation examples

### 1. Review a refactor
$vevs 检查我这次对 src/utils/ 和 src/models/workflows/ 的改动是否破坏了分层架构，并在必要时同步更新 README.md

### 2. Add a concrete Route A component
$vevs 基于当前仓库实现最小可运行的 StructureRepository，并补一个对应测试，保持 work/outputs 目录规则不变

### 3. Extend analysis carefully
$vevs 为 Route A 增加 BindingAnalyzer 的最小真实指标输出，不要引入伪物理结果，并更新 README 进度说明

### 4. Plan a membrane-ready change
$vevs 设计一个不会破坏 Route A 的 membrane-ready 配置扩展方案，只补必要接口和注释，不提前伪实现 Route B

## What good usage looks like
A good response under this skill should:
- identify the layer first
- respect the current repo structure
- make incremental changes
- preserve Route A stability
- avoid fake scientific claims
- update README/TREE when the phase status changes
