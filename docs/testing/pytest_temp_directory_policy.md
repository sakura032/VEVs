# pytest 临时目录治理说明

## 1. 这份文档记录什么

这份文档记录了本项目在测试层面对“临时目录应该写到哪里、什么时候自动清理、失败时如何保留现场”的统一约定。

这次改动的目标很明确：

- 不再把 pytest 运行时产生的临时产物写到项目主目录里的 `work/`
- 所有测试临时文件统一收敛到 `tests/` 体系下
- 测试成功后自动清理，尽量不在仓库中留下临时垃圾
- 测试失败时保留现场，方便定位问题

## 2. 改动背景

在这次整理之前，`tests/vesicle/test_builder.py` 中的部分测试会把临时输出写到：

```text
work/pytest_temp/
```

这会带来几个问题：

1. `work/` 已经不再是当前项目结构的一部分，但测试还在重新生成它
2. 测试临时产物和正式产物目录容易混淆
3. 每次运行 pytest 后，仓库根目录都会被额外污染
4. 对“项目当前只保留 `outputs/vesicle/` 作为正式输出”这一原则形成反向干扰

因此，这次把测试层的临时目录管理单独规范化。

## 3. 当前统一约定

现在的约定如下：

1. 所有需要在测试期间落地文件的测试，只能把临时产物写到 `tests/.tmp/` 下
2. 每个测试函数拥有自己独立的临时根目录
3. 测试通过后自动删除对应临时目录
4. 测试失败时保留对应临时目录，用于排查失败现场
5. `tests/.tmp/` 属于测试运行时目录，不属于正式代码、数据或输出资产

## 4. 关键实现

### 4.1 `tests/conftest.py`

这次新增了统一的测试基础设施：

- [conftest.py](/home/sakura0329/projects/VEVs/tests/conftest.py)

它主要提供两部分能力：

#### `managed_tmp_root` fixture

这个 fixture 会为单个测试函数创建一个受管临时目录，位置固定在：

```text
tests/.tmp/<pytest-node-name>-<random-suffix>/
```

它的职责是：

- 保证测试临时文件全部收敛到 `tests/.tmp/`
- 保证不同测试之间互不干扰
- 让测试代码不需要自己决定临时目录应该放到哪里

#### `pytest_runtest_makereport` hook

这个 hook 用来拿到测试执行结果，并把结果挂到当前测试对象上。这样 `managed_tmp_root` 在 teardown 阶段就能区分：

- 测试通过
- 测试失败

从而决定是否删除临时目录。

### 4.2 `tests/vesicle/test_builder.py`

这次主要改造了：

- [test_builder.py](/home/sakura0329/projects/VEVs/tests/vesicle/test_builder.py)

核心变化包括：

- 原来的 `_workspace_tmp(test_name)` 不再直接写 `work/pytest_temp/`
- 现在改成 `_workspace_tmp(root, name)`，由测试传入自己的 `managed_tmp_root`
- `_patched_outputs_root(...)` 也改成基于受管临时目录工作
- 所有需要写文件的测试都改为接收 `managed_tmp_root`

这样做之后：

- builder 输出测试
- frontend 同步测试
- “输出目录不在 `outputs/vesicle/` 下”的异常测试

都只会把临时数据写到 `tests/.tmp/` 体系下。

## 5. 清理策略

### 成功时自动清理

如果测试执行成功，对应测试的临时目录会在 fixture teardown 阶段被删除。

如果整个 `tests/.tmp/` 目录在删除后变为空目录，也会顺带删除根目录本身。

这样做的结果是：

- 测试跑完后，仓库通常不会留下 `tests/.tmp/`
- 项目根目录保持整洁

### 失败时保留现场

如果测试失败，则不会自动删除对应临时目录。

这样做是为了保留失败现场，方便检查：

- 实际写出的 `vesicle.gro`
- 实际生成的 `topol.top`
- 实际同步出来的 `index.json` 或 `meta.json`

## 6. 配套改动

### `.gitignore`

这次同步更新了：

- [.gitignore](/home/sakura0329/projects/VEVs/.gitignore)

新增忽略项：

```text
tests/.tmp/
```

这样即使失败用例保留了临时目录，也不会被误加入版本控制。

### 清理脚本

这次也同步更新了：

- [cleanup_pytest_temp.sh](/home/sakura0329/projects/VEVs/scripts/cleanup_pytest_temp.sh)

它现在会清理：

- `tests/.tmp`
- 以及其他 pytest 缓存目录

不再引用已经移除的：

- `work/pytest_temp`
- `work/pytest_local_tmp*`

## 7. 后续新增测试时应该怎么写

以后只要测试需要落地文件，推荐按下面的方式写：

1. 在测试函数参数里接收 `managed_tmp_root`
2. 在该根目录下创建当前测试自己的子目录
3. 所有临时输出都写到这个子目录里
4. 不要再手动把临时文件写到 `work/`、项目根目录或正式 `outputs/` 中

示意模式：

```python
def test_something(managed_tmp_root: Path) -> None:
    out_dir = managed_tmp_root / "case_a"
    out_dir.mkdir(parents=True, exist_ok=True)
    ...
```

如果测试需要模拟 `outputs/vesicle/<dataset_id>/` 这种结构，也应该先在 `managed_tmp_root` 下构造，再通过 monkeypatch 或显式参数把目标路径指过去。

## 8. 设计取舍说明

这里没有直接使用 pytest 内置的 `tmp_path` fixture，而是额外做了一层统一管理，主要是为了满足项目自己的约束：

- 临时目录位置要显式落在 `tests/` 下，便于项目内统一观察
- 清理策略要按“成功删除、失败保留”工作，而不是完全交给默认实现
- 未来如果还要补充更多测试层规则，可以继续集中放在 `tests/conftest.py`

这意味着：

- `managed_tmp_root` 是当前仓库级的推荐做法
- 后续若无特殊需要，新增测试优先复用它

## 9. 当前验证结果

这次改动完成后，已经验证：

- `conda run -n vesicle_sim python -m pytest tests/vesicle -q`

结果为：

- `20 passed`

并且测试结束后确认：

- `tests/.tmp/` 没有残留
- 仓库根目录不会再因为成功测试而重新出现 `work/`
