"""Draw the paper's sorting figure (workload_value.pdf) from profiles_combined_{0..4}.csv.

The CSVs are written by analyze_sweep.py in the format of clustering/src/analyze.py, and the
plot below is that script's: same utility, colours, labels and size. Writes
workload_value.pdf (task_bytes_read, as in the paper) and workload_value_rows.pdf
(task_records_read) into --dir, and prints the utilities.

  utility(strategy) = sum over queries of value(q) * plain(q) / strategy(q)
  No Sort           = sum of value(q)

If the CSVs carry an `executions` column (Redbench IMDb, written by analyze_sweep.py
--weighting executions), each query is weighted by its trace executions (net utility), as in
analyze_sweep.py; TPC-DS CSVs have no such column and count every query once.
"""
from argparse import ArgumentParser
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter, NullFormatter  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

VALUE_ITERS = [0, 1, 2, 3, 4]
X_LABELS = ["Constant", "Value 50", "Value 100", "Value 500", "Value 1000"]
TICK_LABELS = ["Const", "50", "100", "500", "1000"]  # short enough not to collide at font 22
GROUP_LABELS = ["VOD", "Frequent", "Random", "No Sort"]
COLORS = ["#E4B935", "#E65742", "#1F63A9", "#ADDC5A"]


def utilities(d, prefix):
    out = []
    for i in VALUE_ITERS:
        df = pd.read_csv(d / f"profiles_combined_{i}.csv")
        plain = df[f"{prefix}_plain"]
        value = df["value"] * df["executions"] if "executions" in df else df["value"]
        u = [(value * plain / df[f"{prefix}_{s}"]).sum() for s in ("vod", "freq", "random")]
        u.append(value.sum())
        out.append(u)
        print(f"  {prefix:5s} {X_LABELS[i]:10s} VOD {u[0]:10.3f}  Frequent {u[1]:10.3f}  "
              f"Random {u[2]:10.3f}  No Sort {u[3]:10.3f}  "
              f"VOD vs Freq {100 * (u[0] - u[1]) / u[1]:+.2f}%  "
              f"VOD vs Random {100 * (u[0] - u[2]) / u[2]:+.2f}%")
    return np.array(out)


def fmt_tick(v, _):
    """Absolute utility without matplotlib's 1e6 offset: 500 / 2K / 1.5M."""
    for scale, suffix in ((1e6, "M"), (1e3, "K")):
        if abs(v) >= scale:
            return f"{v / scale:g}{suffix}"
    return f"{v:g}"


def plot(values, path, log=False, legend=False):
    # Size and font match the placement subfigures (Figs 8/10), set at the same printed width.
    plt.rc("font", size=22)
    fig, ax = plt.subplots(figsize=(8, 5.25))
    x, width = np.arange(len(VALUE_ITERS)), 0.2
    for i in range(values.shape[1]):
        ax.bar(x + i * width, values[:, i], width, label=GROUP_LABELS[i], color=COLORS[i])
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.set_xticks(x + width * (values.shape[1] - 1) / 2)
    ax.set_xlim(-width / 2 - 0.15, x[-1] + width * (values.shape[1] - 0.5) + 0.15)
    ax.set_xticklabels(TICK_LABELS)
    ax.set_xlabel("Maximum Query Value")
    ax.set_ylabel("Workload Utility")
    if log:
        ax.set_yscale("log")
        ax.set_ylim(bottom=10 ** np.floor(np.log10(values.min())))
        ax.yaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_major_formatter(FuncFormatter(fmt_tick))
    if legend:  # one legend per figure, on its last subfigure, as in Figs 8/10
        ax.legend(ncol=2, loc="upper left", handlelength=1, handletextpad=0.4,
                  columnspacing=0.8, borderaxespad=0.3)
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {path}")


def main():
    ap = ArgumentParser()
    ap.add_argument("--dir", required=True, help="directory holding profiles_combined_*.csv")
    ap.add_argument("--legend", action="store_true", help="draw the legend (paper: IMDb only)")
    ap.add_argument("--log", action="store_true",
                    help="log y-axis; writes workload_value_log.pdf / workload_value_rows_log.pdf")
    args = ap.parse_args()
    d, sfx = Path(args.dir), "_log" if args.log else ""
    plot(utilities(d, "bytes"), d / f"workload_value{sfx}.pdf", args.log, args.legend)
    plot(utilities(d, "rows"), d / f"workload_value_rows{sfx}.pdf", args.log, args.legend)


if __name__ == "__main__":
    main()
