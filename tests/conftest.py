"""
tests.conftest
==============

统一管理测试期间产生的临时目录。

当前约定：

1. 所有需要落地文件的测试，只能把临时产物写到 `tests/.tmp/` 下；
2. 每个测试函数拥有自己独立的临时根目录；
3. 测试成功后自动删除该目录，避免在仓库里残留临时文件；
4. 测试失败时保留目录，便于排查问题。
"""

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path

import pytest

TESTS_TMP_ROOT = Path(__file__).resolve().parent / ".tmp"


def _slugify_test_name(node_name: str) -> str:
    """
    把 pytest 节点名转成适合作为目录名前缀的稳定字符串。

    这里不追求可逆，只追求：
    - 人类可读；
    - 文件系统安全；
    - 同一测试在同一轮运行中的目录名前缀稳定。
    """
    slug = re.sub(r"[^0-9A-Za-z_.-]+", "_", node_name).strip("._-")
    return slug or "pytest_case"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[object]):
    """
    把每个阶段的执行结果挂到 `item` 上，供 fixture 在 teardown 阶段判断。
    """
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest.fixture
def managed_tmp_root(request: pytest.FixtureRequest) -> Path:
    """
    为单个测试函数创建受管临时目录。

    目录位置固定在 `tests/.tmp/` 下，避免再把测试输出写回 `work/` 或其他项目主目录。

    清理策略：
    - 测试通过：自动删除；
    - 测试失败：保留目录，方便检查失败现场。
    """
    TESTS_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    prefix = f"{_slugify_test_name(request.node.name)}-"
    temp_dir = Path(tempfile.mkdtemp(prefix=prefix, dir=TESTS_TMP_ROOT))

    yield temp_dir

    rep_call = getattr(request.node, "rep_call", None)
    if rep_call is not None and rep_call.passed:
        shutil.rmtree(temp_dir, ignore_errors=True)
        try:
            next(TESTS_TMP_ROOT.iterdir())
        except StopIteration:
            TESTS_TMP_ROOT.rmdir()
