"""R2D16: listener overhead vs. vanilla for one EC2 run, with the rep-to-rep noise band.

    python3 overhead_summary.py <run-dir> [<run-dir> ...]

<run-dir> is what 40_fetch.sh brings down: benchmarking/data/ec2/<run-id>/, holding
rep<k>/<variant>/spark_internal_listener_<variant>_results.csv
(query,dataset,runtime[ms],listener_timeout).

The metric is user-observed query latency (REVISION_SCALEUP.md §2). For each run it reports
  - per variant, per rep: the sum of the 22 per-query runtimes;
  - overhead vs. vanilla on the mean over reps, relative (%) and absolute (s per pass and
    ms per query) — REVISION_SCALEUP.md §4.3 asks for both;
  - the noise band: the rep-to-rep difference of each variant's pass sum, and the median
    per-query rep-to-rep difference. An overhead smaller than the band is "within noise".
Rows with runtime < 0 or listener_timeout=true are excluded and counted, never averaged in.
"""
import csv
import glob
import os
import statistics
import sys
from collections import defaultdict

VARIANTS = ["vanilla", "bare", "cols", "rowgroup"]


def load(run_dir):
    t = defaultdict(lambda: defaultdict(dict))      # variant -> rep -> query -> seconds
    bad = []
    for f in glob.glob(os.path.join(run_dir, "rep*", "*", "spark_internal_listener_*_results.csv")):
        rep = os.path.basename(os.path.dirname(os.path.dirname(f)))
        variant = os.path.basename(os.path.dirname(f))
        for r in csv.DictReader(open(f)):
            rt = int(r["runtime"])
            if rt < 0 or r.get("listener_timeout", "false") == "true":
                bad.append((variant, rep, r["query"]))
                continue
            t[variant][rep][r["query"]] = rt / 1000.0
    return t, bad


def summarize(run_dir):
    t, bad = load(run_dir)
    name = os.path.basename(os.path.normpath(run_dir))
    print(f"== {name}")
    if bad:
        print(f"   excluded {len(bad)} rows (failed or listener timeout): {bad[:6]}")
    reps = sorted({rep for v in t.values() for rep in v})
    # queries present in every (variant, rep): compare like with like
    common = set.intersection(*[set(t[v][rep]) for v in VARIANTS if v in t for rep in reps if rep in t[v]])
    nq = len(common)
    print(f"   reps: {reps}; queries common to every (variant, rep): {nq}")

    sums = {v: {rep: sum(t[v][rep][q] for q in common) for rep in reps if rep in t[v]} for v in VARIANTS if v in t}
    print(f"   {'variant':<9} " + " ".join(f"{rep + ' (s)':>11}" for rep in reps) +
          f" {'mean (s)':>9} {'rep Δ (s)':>9} {'rep Δ %':>8}")
    mean = {}
    for v in sums:
        vals = [sums[v][rep] for rep in reps if rep in sums[v]]
        mean[v] = statistics.mean(vals)
        d = (max(vals) - min(vals)) if len(vals) > 1 else float("nan")
        print(f"   {v:<9} " + " ".join(f"{sums[v].get(rep, float('nan')):11.1f}" for rep in reps) +
              f" {mean[v]:9.1f} {d:9.1f} {100 * d / mean[v]:8.2f}")

    if "vanilla" not in mean:
        return
    van = mean["vanilla"]
    band = max((max(sums[v].values()) - min(sums[v].values())) / statistics.mean(sums[v].values())
               for v in sums if len(sums[v]) > 1) if len(reps) > 1 else float("nan")
    print(f"   noise band (largest rep-to-rep pass difference, any variant): {100 * band:.2f}%")
    for v in [x for x in VARIANTS if x in mean and x != "vanilla"]:
        d = mean[v] - van
        verdict = "within noise" if abs(d / van) <= band else "OUTSIDE noise"
        print(f"   {v:<9} vs vanilla: {100 * d / van:+6.2f}%  {d:+8.1f} s/pass  "
              f"{1000 * d / nq:+8.0f} ms/query  -> {verdict}")

    # per-query rep-to-rep noise (vanilla), for the per-query plot's error bars
    if len(reps) > 1 and "vanilla" in t:
        diffs = [abs(t["vanilla"][reps[0]][q] - t["vanilla"][reps[1]][q]) / statistics.mean(
                 [t["vanilla"][reps[0]][q], t["vanilla"][reps[1]][q]]) for q in common]
        print(f"   vanilla per-query rep-to-rep difference: median {100 * statistics.median(diffs):.1f}%, "
              f"max {100 * max(diffs):.1f}%")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for d in sys.argv[1:]:
        summarize(d)


if __name__ == "__main__":
    main()
