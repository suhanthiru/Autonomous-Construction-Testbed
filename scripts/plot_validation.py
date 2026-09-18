"""Render fixed-scale scientific comparisons from saved records."""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from excavation_sim.datasets import rheometer_volume_fraction


def terrain(run: Path, data: Path, output: Path):
    import json

    report = json.loads((run / "report.json").read_text())
    trial = report["trial"]
    target = np.load(
        data
        / "data/system-identification-targets/sand"
        / f"pcd_{trial}_cropped_norm_z_aligned_height_map-res40.npy",
        allow_pickle=False,
    )
    predicted = np.load(run / "height.npy", allow_pickle=False)
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), layout="constrained")
    extent = (0.08, 0.32, 0.08, 0.32)
    for ax, values, title in zip(
        axes[:2],
        [target, predicted],
        ["Measured final surface", "Simulated final surface"],
        strict=True,
    ):
        im = ax.imshow(values.T * 1000, origin="lower", extent=extent, vmin=15, vmax=120)
        ax.set_title(title)
    fig.colorbar(im, ax=axes[:2], label="Height (mm)", shrink=0.8)
    error = (predicted - target) * 1000
    im = axes[2].imshow(error.T, origin="lower", extent=extent, cmap="RdBu_r", vmin=-30, vmax=30)
    axes[2].set_title("Simulated minus measured")
    fig.colorbar(im, ax=axes[2], label="Height error (mm)", shrink=0.8)
    for ax in axes:
        ax.set(xlabel="x (m)", ylabel="y (m)")
    fig.suptitle(
        f"DDBot trial {trial}: exploratory replay, not physically validated\n"
        f"MAE {report['mae_m'] * 1000:.2f} mm; "
        f"unoccupied simulated cells {report['empty_surface_cells']}"
    )
    fig.savefig(output, dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--rheometer", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.rheometer:
        data = rheometer_volume_fraction(args.rheometer)
        fig, ax = plt.subplots(figsize=(6, 4), layout="constrained")
        for condition in data["conditions"]:
            ax.plot(
                condition["dimensionless_depth"],
                condition["dimensionless_pressure"],
                label=f"Packing fraction {condition['packing_fraction']}",
            )
        ax.set(
            xlim=(0, 11),
            ylim=(0, 700),
            xlabel="Depth / intruder radius",
            ylabel="Dimensionless pressure",
            title="Rheometer data transformation\nPublished normalization; no simulation fit",
        )
        ax.legend()
        fig.savefig(args.output, dpi=180)
        plt.close(fig)
    else:
        if not args.run or not args.data:
            parser.error("provide --run and --data, or --rheometer")
        terrain(args.run, args.data, args.output)
