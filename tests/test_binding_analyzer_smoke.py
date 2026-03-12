from __future__ import annotations

import json
from pathlib import Path
import shutil

import pandas as pd

from src.analysis import BindingAnalyzer
from src.configs import ProjectPaths
from src.interfaces.contracts import SimulationArtifacts


def _new_temp_root(test_name: str) -> Path:
    root = Path("work") / "pytest_temp" / test_name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_binding_analyzer_log_fallback_smoke() -> None:
    root = _new_temp_root("binding_analyzer_smoke")
    paths = ProjectPaths.from_root(root)

    md_dir = paths.work_dir / "md"
    md_dir.mkdir(parents=True, exist_ok=True)
    log_csv = md_dir / "md_log.csv"

    df = pd.DataFrame(
        {
            "step": [0, 100, 200, 300],
            "time": [0.0, 0.2, 0.4, 0.6],
            "temperature": [299.2, 300.1, 301.0, 300.4],
            "potentialEnergy": [-1234.0, -1229.0, -1231.5, -1230.2],
        }
    )
    df.to_csv(log_csv, index=False)

    analyzer = BindingAnalyzer(paths=paths)
    outputs = analyzer.analyze(SimulationArtifacts(log_csv=log_csv))

    assert "metrics_json" in outputs
    assert outputs["metrics_json"].exists()
    assert any("figure" in key for key in outputs.keys())
    for value in outputs.values():
        assert value.exists()

    payload = json.loads(outputs["metrics_json"].read_text(encoding="utf-8"))
    assert payload["analysis_mode"] == "log_fallback_missing_trajectory"
    assert payload["metrics_semantics"] == "diagnostic_not_physical"
    assert payload["diagnostic"] == "true"
