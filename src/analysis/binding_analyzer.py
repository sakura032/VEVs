from __future__ import annotations

from pathlib import Path
import json

from src.configs import ProjectPaths
from src.interfaces.contracts import BindingAnalyzerProtocol, SimulationArtifacts


class BindingAnalyzer(BindingAnalyzerProtocol):
    """Minimum Route A analyzer with trajectory-first and log fallback modes."""

    def __init__(self, paths: ProjectPaths):
        self.paths = paths
        self.paths.ensure_dirs()

    def analyze(self, simulation: SimulationArtifacts) -> dict[str, Path]:
        out_dir = self.paths.output_dir / "analysis" / "binding"
        fig_dir = out_dir / "figures"
        out_dir.mkdir(parents=True, exist_ok=True)
        fig_dir.mkdir(parents=True, exist_ok=True)

        metrics: dict[str, float | int | str] = {}
        outputs: dict[str, Path] = {}

        used_trajectory = (
            simulation.npt_last_structure is not None
            and simulation.trajectory is not None
            and simulation.npt_last_structure.exists()
            and simulation.trajectory.exists()
        )

        if used_trajectory:
            try:
                traj_outputs, traj_metrics = self._analyze_from_trajectory(simulation, out_dir, fig_dir)
                outputs.update(traj_outputs)
                metrics.update(traj_metrics)
                metrics["analysis_mode"] = "trajectory"
                metrics["metrics_semantics"] = "physical_trajectory_derived"
            except Exception:
                # Keep Route A runnable when trajectory-analysis deps are missing.
                log_outputs, log_metrics = self._analyze_from_log(simulation, out_dir, fig_dir)
                outputs.update(log_outputs)
                metrics.update(log_metrics)
                metrics["analysis_mode"] = "log_fallback_after_trajectory_error"
                metrics["metrics_semantics"] = "diagnostic_not_physical"
                metrics["diagnostic"] = "true"
        else:
            log_outputs, log_metrics = self._analyze_from_log(simulation, out_dir, fig_dir)
            outputs.update(log_outputs)
            metrics.update(log_metrics)
            metrics["analysis_mode"] = "log_fallback_missing_trajectory"
            metrics["metrics_semantics"] = "diagnostic_not_physical"
            metrics["diagnostic"] = "true"

        metrics_path = out_dir / "metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
        outputs["metrics_json"] = metrics_path
        return outputs

    def _analyze_from_trajectory(
        self,
        simulation: SimulationArtifacts,
        out_dir: Path,
        fig_dir: Path,
    ) -> tuple[dict[str, Path], dict[str, float | int]]:
        try:
            import MDAnalysis as mda
            from MDAnalysis.analysis.rms import RMSD
            import pandas as pd
            import matplotlib.pyplot as plt
        except ImportError as exc:
            raise ImportError(
                "Trajectory analysis requires MDAnalysis, pandas and matplotlib."
            ) from exc

        assert simulation.npt_last_structure is not None
        assert simulation.trajectory is not None

        universe = mda.Universe(str(simulation.npt_last_structure), str(simulation.trajectory))
        rmsd_runner = RMSD(
            universe,
            universe,
            select="backbone",
            ref_frame=0,
        ).run()

        # columns: frame, time(ps), rmsd(backbone)
        arr = rmsd_runner.results.rmsd
        df = pd.DataFrame(arr, columns=["frame", "time_ps", "rmsd_angstrom"])

        rmsd_csv = out_dir / "rmsd.csv"
        df.to_csv(rmsd_csv, index=False)

        rmsd_png = fig_dir / "rmsd.png"
        plt.figure(figsize=(6, 4))
        plt.plot(df["time_ps"] / 1000.0, df["rmsd_angstrom"], linewidth=1.0)
        plt.xlabel("Time (ns)")
        plt.ylabel("Backbone RMSD (Angstrom)")
        plt.title("Route A RMSD")
        plt.tight_layout()
        plt.savefig(rmsd_png, dpi=200)
        plt.close()

        outputs = {
            "rmsd_csv": rmsd_csv,
            "rmsd_figure": rmsd_png,
        }
        metrics = {
            "n_frames": int(len(df)),
            "rmsd_mean_angstrom": float(df["rmsd_angstrom"].mean()),
            "rmsd_max_angstrom": float(df["rmsd_angstrom"].max()),
            "rmsd_min_angstrom": float(df["rmsd_angstrom"].min()),
        }
        return outputs, metrics

    def _analyze_from_log(
        self,
        simulation: SimulationArtifacts,
        out_dir: Path,
        fig_dir: Path,
    ) -> tuple[dict[str, Path], dict[str, float | int]]:
        if simulation.log_csv is None or not simulation.log_csv.exists():
            raise FileNotFoundError("Simulation log_csv is missing; cannot run fallback analysis")

        try:
            import pandas as pd
            import matplotlib.pyplot as plt
        except ImportError as exc:
            raise ImportError(
                "Fallback analysis requires pandas and matplotlib."
            ) from exc

        log_df = pd.read_csv(simulation.log_csv)
        if log_df.empty:
            raise ValueError("Simulation log CSV is empty")

        # Pick available x/y columns conservatively.
        x_col = "time" if "time" in log_df.columns else ("step" if "step" in log_df.columns else None)
        y_col = (
            "temperature"
            if "temperature" in log_df.columns
            else ("potentialEnergy" if "potentialEnergy" in log_df.columns else None)
        )
        if x_col is None or y_col is None:
            raise ValueError("log_csv does not contain required columns for fallback plotting")

        profile_png = fig_dir / "log_profile.png"
        plt.figure(figsize=(6, 4))
        plt.plot(log_df[x_col], log_df[y_col], linewidth=1.0)
        plt.xlabel(x_col)
        plt.ylabel(y_col)
        plt.title("Route A Log Profile")
        plt.tight_layout()
        plt.savefig(profile_png, dpi=200)
        plt.close()

        outputs = {"log_profile_figure": profile_png}
        metrics = {
            "n_log_rows": int(len(log_df)),
            "profile_mean": float(log_df[y_col].mean()),
            "profile_max": float(log_df[y_col].max()),
            "profile_min": float(log_df[y_col].min()),
        }
        return outputs, metrics
