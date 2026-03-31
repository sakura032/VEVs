"""
tests.vesicle.test_builder
==========================

这组测试覆盖 `VesicleBuilder` 与高层脚本入口的关键闭环：

1. 默认 45 蛋白三岛构造器是否按预期生成；
2. builder 是否能完成蛋白簇集放置与精确脂质配比；
3. `.gro/.top` 是否能稳定写出；
4. 多数据集输出与前端同步索引是否按当前约定工作。
"""

from __future__ import annotations

import importlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from src.vesicle.models.protein import Protein
from src.vesicle.models.vesicle_builder import VesicleBuilder
from scripts.vesicle_build import build_default_basic_vesicle
from scripts.vesicle_sync_frontend import sync_vesicle_to_frontend

build_default_basic_vesicle_module = importlib.import_module("scripts.vesicle_build")

PROTEIN_DIR = Path("data/vesicle/proteins")


def _expected_counts(composition: dict[str, float], total_count: int) -> Counter:
    """
    复刻 builder 的“最大余数法”计数逻辑，作为测试期望值。

    这里故意不直接调用 builder 私有方法，避免测试只是重复执行同一份代码。
    """
    total = float(sum(composition.values()))
    raw = {name: (value / total) * total_count for name, value in composition.items()}
    counts = Counter({name: int(np.floor(raw[name])) for name in composition})
    remaining = total_count - sum(counts.values())

    ranked = sorted(
        composition.keys(),
        key=lambda name: (raw[name] - counts[name], composition[name], name),
        reverse=True,
    )
    for name in ranked[:remaining]:
        counts[name] += 1
    return counts


def _workspace_tmp(root: Path, name: str) -> Path:
    """
    在当前测试自己的受管临时根目录下创建子目录。

    这里所有测试产物都只允许写到 `tests/.tmp/` 对应的临时根目录中，
    避免再次污染项目主目录。
    """
    root = root / name
    root.mkdir(parents=True, exist_ok=True)
    return root


def _outputs_tmp(root: Path, dataset_name: str) -> Path:
    """
    在给定根目录下准备一个临时数据集目录。
    """
    dataset_root = root / dataset_name
    dataset_root.mkdir(parents=True, exist_ok=True)
    return dataset_root


def _patched_outputs_root(
    monkeypatch: pytest.MonkeyPatch,
    managed_tmp_root: Path,
    name: str,
) -> Path:
    """
    把高层入口里的 `OUTPUTS_ROOT` 临时改到当前测试的受管目录下，
    避免回归测试污染真实 `outputs/vesicle/`。
    """
    outputs_root = _workspace_tmp(managed_tmp_root, name) / "vesicle_outputs"
    outputs_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(build_default_basic_vesicle_module, "OUTPUTS_ROOT", outputs_root)
    return outputs_root


def _write_minimal_output_pair(output_dir: Path) -> None:
    """写一组最小可同步的 `vesicle.gro/topol.top` 假文件，用于同步脚本测试。"""
    gro_text = (
        "pytest sync fixture\n"
        "1\n"
        "    1CHOL   ROH    1   0.000   0.000   0.000\n"
        "   1.00000   1.00000   1.00000\n"
    )
    top_text = '#include "data/vesicle/forcefields/martini_v2.2.itp"\n'
    (output_dir / "vesicle.gro").write_text(gro_text, encoding="utf-8")
    (output_dir / "topol.top").write_text(top_text, encoding="utf-8")


def test_make_protein_clusters_builds_expected_three_island_layout() -> None:
    """
    验证默认三岛构造器是否真的返回：
    - 岛 0：8 CD9 + 7 CD81
    - 岛 1：7 CD9 + 8 CD81
    - 岛 2：15 CD63
    """
    cluster_assignments = VesicleBuilder.make_protein_clusters(PROTEIN_DIR)

    assert len(cluster_assignments) == 3
    assert [len(cluster) for cluster in cluster_assignments] == [15, 15, 15]

    cluster_0 = Counter(protein.name for protein in cluster_assignments[0])
    cluster_1 = Counter(protein.name for protein in cluster_assignments[1])
    cluster_2 = Counter(protein.name for protein in cluster_assignments[2])

    assert cluster_0 == Counter({"CD9": 8, "CD81": 7})
    assert cluster_1 == Counter({"CD9": 7, "CD81": 8})
    assert cluster_2 == Counter({"CD63": 15})


def test_builder_places_clustered_proteins_and_exact_leaflet_composition() -> None:
    """
    builder 的主功能回归测试。

    这里使用一个更小的三岛体系：
    - 每个岛只放 1 个蛋白；
    - 依然覆盖蛋白球面放置、局部防撞和双叶精确脂质计数。
    """
    np.random.seed(11)

    cluster_assignments = [
        [Protein.from_gro("CD9", PROTEIN_DIR / "cg_CD9_clean.gro")],
        [Protein.from_gro("CD81", PROTEIN_DIR / "cg_CD81_clean.gro")],
        [Protein.from_gro("CD63", PROTEIN_DIR / "cg_CD63_clean.gro")],
    ]

    builder = VesicleBuilder(
        radius_out=12.0,
        thickness=2.0,
        lipid_exclusion_radius=0.5,
        lipid_area=5.0,
    ).build(cluster_assignments)

    assert len(builder.protein_centers) == 3
    centers = np.vstack(builder.protein_centers)
    radii = np.asarray(builder._protein_radii, dtype=np.float64)

    assert np.allclose(np.linalg.norm(centers, axis=1), builder.R_mid)

    for i in range(len(centers)):
        for j in range(i + 1, len(centers)):
            distance = np.linalg.norm(centers[i] - centers[j])
            threshold = builder.PROTEIN_SPACING_FACTOR * (radii[i] + radii[j])
            assert distance > threshold

    assert builder.molecule_counts["CD9_0"] == 1
    assert builder.molecule_counts["CD63_0"] == 1
    assert builder.molecule_counts["CD81_0"] == 1

    total_out = int(round((4.0 * np.pi * (builder.R_out**2)) / builder.lipid_area))
    total_in = int(round((4.0 * np.pi * (builder.R_in**2)) / builder.lipid_area))

    expected_counts = _expected_counts(builder.comp_out, total_out)
    for name, count in _expected_counts(builder.comp_in, total_in).items():
        expected_counts[name] += count

    for name, count in expected_counts.items():
        assert builder.molecule_counts[name] == count


def test_builder_write_outputs_emits_gro_and_top_files(managed_tmp_root: Path) -> None:
    """
    验证输出层最基本的稳定性：
    - `.gro` 原子数正确；
    - `.top` include 与蛋白分子名正确出现。
    """
    np.random.seed(3)

    cluster_assignments = [
        [Protein.from_gro("CD9", PROTEIN_DIR / "cg_CD9_clean.gro")],
        [Protein.from_gro("CD81", PROTEIN_DIR / "cg_CD81_clean.gro")],
        [Protein.from_gro("CD63", PROTEIN_DIR / "cg_CD63_clean.gro")],
    ]

    builder = VesicleBuilder(
        radius_out=11.0,
        thickness=2.0,
        lipid_exclusion_radius=0.5,
        lipid_area=5.5,
    ).build(cluster_assignments)

    out_dir = _workspace_tmp(managed_tmp_root, "vesicle_builder")
    gro_path = out_dir / "vesicle.gro"
    top_path = out_dir / "topol.top"
    builder.write_outputs(str(gro_path), str(top_path))

    gro_lines = gro_path.read_text(encoding="utf-8").splitlines()
    top_text = top_path.read_text(encoding="utf-8")

    assert gro_lines[0] == "VesicleBuilder output"
    assert int(gro_lines[1].strip()) == len(builder.atoms)
    assert len(gro_lines) == len(builder.atoms) + 3
    assert "forcefields/martini_v2.2.itp" in top_text
    assert "forcefields/martini_v2.0_CHOL_02.itp" in top_text
    assert "forcefields/martini_v2.0_POPC_02.itp" in top_text
    assert "forcefields/martini_v2.0_DPSM_01.itp" in top_text
    assert "forcefields/martini_v2.0_POPE_02.itp" in top_text
    assert "forcefields/martini_v2.0_POPS_02.itp" in top_text
    assert "forcefields/martini_v2.0_POP2_01.itp" in top_text
    assert "CD9_0" in top_text
    assert "CD63_0" in top_text
    assert "CD81_0" in top_text


def test_fill_lipid_leaflet_shuffles_oversampled_points_before_consuming_prefix() -> None:
    """
    回归测试：过采样 Fibonacci 候选点若不先打乱再消耗，会沿 z 轴留下极区缺口。

    这里用纯 CHOL 外叶做最小诊断，因为 CHOL 的 `ROH` bead 就是球面目标点。
    """
    np.random.seed(9)

    builder = VesicleBuilder(
        radius_out=10.0,
        thickness=2.0,
        lipid_exclusion_radius=0.5,
        lipid_area=5.0,
    )
    builder._reset_state()
    builder.detector.build_trees()
    builder._fill_lipid_leaflet(builder.R_out, {"CHOL": 1.0}, False)

    roh_coords = np.array(
        [
            [atom.x, atom.y, atom.z]
            for atom in builder.atoms
            if atom.res_name == "CHOL" and atom.atom_name == "ROH"
        ],
        dtype=np.float64,
    )
    spans = np.ptp(roh_coords, axis=0)

    assert len(roh_coords) > 0
    assert spans[2] > 0.9 * spans[0]
    assert spans[2] > 0.9 * spans[1]


def test_sync_vesicle_to_frontend_updates_index_and_preserves_multiple_datasets(
    managed_tmp_root: Path,
) -> None:
    """
    直接验证通用同步器：
    - 可把两个不同输出目录同步到前端；
    - `index.json` 会同时保留两个数据集条目；
    - 最新同步的数据集排在最前面。
    """
    visualization_root = _workspace_tmp(managed_tmp_root, "vesicle_sync_root")
    source_root = _workspace_tmp(managed_tmp_root, "vesicle_sync_sources")
    dataset_a = _outputs_tmp(source_root, "pytest_sync_a")
    dataset_b = _outputs_tmp(source_root, "pytest_sync_b")
    _write_minimal_output_pair(dataset_a)
    _write_minimal_output_pair(dataset_b)

    target_a = sync_vesicle_to_frontend(dataset_a, visualization_root)
    target_b = sync_vesicle_to_frontend(dataset_b, visualization_root)

    assert (target_a / "vesicle.gro").exists()
    assert (target_b / "vesicle.gro").exists()
    assert (target_a / "meta.json").exists()
    assert (target_b / "meta.json").exists()

    index_payload = json.loads((visualization_root / "index.json").read_text(encoding="utf-8"))
    datasets = index_payload["datasets"]
    assert {entry["dataset_id"] for entry in datasets} >= {"pytest_sync_a", "pytest_sync_b"}
    assert datasets[0]["dataset_id"] == "pytest_sync_b"


def test_build_default_basic_vesicle_writes_and_syncs_named_dataset(
    monkeypatch: pytest.MonkeyPatch,
    managed_tmp_root: Path,
) -> None:
    """
    高层入口应当支持输出到 `outputs/vesicle/<dataset_name>/`，并自动同步到前端同名目录。
    """
    np.random.seed(4)

    outputs_root = _patched_outputs_root(
        monkeypatch,
        managed_tmp_root,
        "pytest_basic_outputs_root",
    )
    output_dir = _outputs_tmp(outputs_root, "pytest_basic_vesicle_entry")
    frontend_root = _workspace_tmp(managed_tmp_root, "pytest_basic_vesicle_frontend")
    builder = build_default_basic_vesicle(
        output_dir=output_dir,
        protein_dir=PROTEIN_DIR,
        frontend_visualization_root=frontend_root,
        builder_kwargs={
            "radius_out": 50.0,
            "thickness": 4.0,
            "lipid_exclusion_radius": 0.5,
            "lipid_area": 20.0,
        },
    )

    gro_path = output_dir / builder.DEFAULT_GRO_NAME
    top_path = output_dir / builder.DEFAULT_TOP_NAME
    synced_root = frontend_root / output_dir.name
    synced_gro_path = synced_root / "vesicle.gro"
    synced_top_path = synced_root / "topol.top"
    synced_meta_path = synced_root / "meta.json"
    index_path = frontend_root / "index.json"

    assert gro_path.exists()
    assert top_path.exists()
    assert synced_gro_path.exists()
    assert synced_top_path.exists()
    assert synced_meta_path.exists()
    assert index_path.exists()
    assert builder.molecule_counts["CD9_0"] == 15
    assert builder.molecule_counts["CD81_0"] == 15
    assert builder.molecule_counts["CD63_0"] == 15

    meta_payload = json.loads(synced_meta_path.read_text(encoding="utf-8"))
    assert meta_payload["dataset_id"] == output_dir.name
    assert meta_payload["structure_url"].endswith(f"/{output_dir.name}/vesicle.gro")

    index_payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert any(entry["dataset_id"] == output_dir.name for entry in index_payload["datasets"])


def test_build_default_basic_vesicle_warns_and_errors_when_sync_path_is_outside_outputs(
    managed_tmp_root: Path,
) -> None:
    """
    自动同步开启时，输出目录若不在 `outputs/vesicle/<dataset_name>/` 下，应先警告再报错。
    """
    output_dir = _workspace_tmp(managed_tmp_root, "outside_outputs_entry")
    frontend_root = _workspace_tmp(managed_tmp_root, "outside_outputs_frontend")

    with pytest.warns(UserWarning, match="自动同步只支持"):
        with pytest.raises(ValueError, match="自动同步只支持"):
            build_default_basic_vesicle(
                output_dir=output_dir,
                protein_dir=PROTEIN_DIR,
                frontend_visualization_root=frontend_root,
                builder_kwargs={
                    "radius_out": 18.0,
                    "thickness": 2.0,
                    "lipid_exclusion_radius": 0.5,
                    "lipid_area": 12.0,
                },
            )

    assert not (output_dir / "vesicle.gro").exists()
    assert not (output_dir / "topol.top").exists()
    assert not (frontend_root / output_dir.name).exists()


def test_build_default_basic_vesicle_allows_outside_outputs_when_sync_disabled(
    monkeypatch: pytest.MonkeyPatch,
    managed_tmp_root: Path,
) -> None:
    """
    关闭自动同步时，不再要求输出目录位于 `outputs/vesicle/` 下。
    """
    _patched_outputs_root(monkeypatch, managed_tmp_root, "pytest_no_sync_outputs_root")
    output_dir = _workspace_tmp(managed_tmp_root, "outside_outputs_no_sync")
    builder = build_default_basic_vesicle(
        output_dir=output_dir,
        protein_dir=PROTEIN_DIR,
        sync_frontend=False,
        builder_kwargs={
            "radius_out": 50.0,
            "thickness": 4.0,
            "lipid_exclusion_radius": 0.5,
            "lipid_area": 20.0,
        },
    )

    assert (output_dir / builder.DEFAULT_GRO_NAME).exists()
    assert (output_dir / builder.DEFAULT_TOP_NAME).exists()
