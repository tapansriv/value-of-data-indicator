"""Task-value generation for the Redbench IMDb workload (R3D4).

Produces SEVERAL NAMED VALUE-ASSIGNMENT SCHEMES rather than one. Each is a plausible
organizational story about where value comes from, and they span the range from
"value aligns with frequency" to "value is the opposite of frequency". The point of the
experiment is what VDI does across that range, so the assignment must be an axis, not a
constant.

  constant          every task worth the same. The degenerate reference: with no value
                    information VDI reduces toward frequency. Answers "what if the
                    estimates carry nothing?" (R1W3/R1E4).
  frequency_aligned value proportional to execution count -- "the queries everyone runs
                    are the ones that matter", e.g. a dashboard many people depend on.
                    This is the arm where VDI should cost nothing.
  tiered            a few designated business-critical tasks at high value, the rest at
                    baseline, assigned INDEPENDENTLY of frequency. The most realistic
                    organizational story: a CDO names a handful of critical reports.
                    Mirrors custom_values.py (1000 / 100 / 1) and the three-tier split in
                    clustering/schema/tpcds_query_tiers.json.
  independent       value drawn from a heavy-tailed spread, independent of frequency.
                    Continuous counterpart of `tiered`.
  rare_critical     value ANTI-correlated with frequency: the rarely-run tasks are the
                    valuable ones -- a quarterly regulatory report, a disaster-recovery
                    query. This is also the R2W1/R2D5/MW2 "important data that is rarely
                    used" case, so the same run answers that thread.
  runtime_proxy     value proportional to real Redshift execution duration. KEPT ONLY AS A
                    LABELLED COMPARATOR, never the default: it asserts that long-running
                    means valuable, which is an assumption about cost, not worth, and is
                    exactly the kind of unjustified constant R2W4 objects to. Useful
                    because many systems implicitly assume it -- report it as such.

Also supports `--rho R` for a continuous Gaussian-copula sweep when a smooth x-axis is
wanted alongside the named schemes.

Column keys are qualified `table.column`: IMDb's 108 table-columns share only 38 bare
names (`id` is in all 21 tables), so the TPC-DS pipeline's bare-name keys would mis-credit
value across tables.

Outputs per scheme, in the shapes clustering/src/rank.py consumes:
  values/imdb_data_val_cols_<scheme>.json   {trial: {table.column: value}}
  values/imdb_query_values_<scheme>.csv     per-query values, per trial
  values/imdb_frequency_cols.json           {table.column: count}   (scheme-independent)
"""
import csv, json, math, argparse
from collections import Counter
from pathlib import Path
from statistics import NormalDist
import numpy as np

HERE = Path(__file__).resolve().parent
ND = NormalDist()
HIGH, MID, LOW = 1000.0, 100.0, 1.0      # as in custom_values.py
SCHEMES = ["constant", "frequency_aligned", "tiered", "independent",
           "rare_critical", "runtime_proxy"]


def spearman(a, b):
    def rk(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0]*len(v); i = 0
        while i < len(o):
            j = i
            while j+1 < len(o) and v[o[j+1]] == v[o[i]]: j += 1
            for k in range(i, j+1): r[o[k]] = (i+j)/2 + 1
            i = j+1
        return r
    ra, rb = rk(a), rk(b); n = len(a)
    ma, mb = sum(ra)/n, sum(rb)/n
    num = sum((x-ma)*(y-mb) for x, y in zip(ra, rb))
    da = math.sqrt(sum((x-ma)**2 for x in ra)); db = math.sqrt(sum((y-mb)**2 for y in rb))
    return num/(da*db) if da and db else 0.0


def assign(scheme, f, rt, rng, z1):
    """-> per-query values. f = execution counts, rt = mean real runtime per query."""
    n = len(f)
    if scheme == "constant":
        return np.ones(n)
    if scheme == "frequency_aligned":
        return f.astype(float).copy()
    if scheme == "runtime_proxy":
        return np.where(rt > 0, rt, np.median(rt[rt > 0]) if (rt > 0).any() else 1.0)
    if scheme == "tiered":
        v = np.full(n, LOW)
        idx = rng.permutation(n)                       # independent of frequency
        n1 = max(1, round(0.03*n)); n2 = max(1, round(0.12*n))
        v[idx[:n1]] = HIGH; v[idx[n1:n1+n2]] = MID
        return v
    if scheme == "independent":
        return np.exp(1.5*rng.standard_normal(n))
    if scheme == "rare_critical":
        # value decreasing in frequency rank, with noise so it is not a pure inversion
        order = np.argsort(np.argsort(-f))             # 0 = most frequent
        base = np.exp(1.5*(order/max(n-1, 1)*2 - 1)*1.5)
        return base*np.exp(0.3*rng.standard_normal(n))
    raise ValueError(scheme)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schemes", nargs="+", default=SCHEMES, choices=SCHEMES)
    ap.add_argument("--rho", type=float, nargs="*", default=[],
                    help="also emit continuous Gaussian-copula sweeps at these rho")
    ap.add_argument("--num-trials", type=int, default=100)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    out = HERE/"values"; out.mkdir(exist_ok=True)
    cols_in_q = json.load(open(HERE/"imdb_columns_in_queries.json"))
    registry = json.load(open(HERE/"imdb_schema_registry.json"))
    json.dump({t: [f"{t}.{c}" for c in cs] for t, cs in registry.items()},
              open(HERE/"imdb_schema_registry_qualified.json", "w"), indent=4, sort_keys=True)
    all_cols = [f"{t}.{c}" for t, cs in registry.items() for c in cs]

    freq, rt_sum = Counter(), Counter()
    for r in csv.DictReader(open(HERE/"stream.csv")):
        q = r["query_file"]; freq[q] += 1
        try: rt_sum[q] += float(r["exec_ms"])
        except (ValueError, KeyError): pass
    queries = sorted(freq)
    f = np.array([freq[q] for q in queries], float)
    rt = np.array([rt_sum[q]/freq[q] for q in queries], float)
    n = len(queries)
    print(f"{n} distinct queries, {int(f.sum()):,} executions (max {int(f.max()):,}, "
          f"median {int(np.median(f))})\n")

    freq_cols = {c: 0 for c in all_cols}
    for q, cnt in freq.items():
        for t, cs in cols_in_q.get(q, {}).items():
            for c in cs: freq_cols[f"{t}.{c}"] += cnt
    json.dump(freq_cols, open(out/"imdb_frequency_cols.json", "w"), indent=4, sort_keys=True)

    order = sorted(range(n), key=lambda i: (f[i], queries[i]))
    z1 = np.empty(n)
    for pos, i in enumerate(order): z1[i] = ND.inv_cdf((pos+0.5)/n)

    rng = np.random.default_rng(args.seed)
    jobs = [(s, None) for s in args.schemes] + [(f"rho{r:+.2f}".replace('.','').replace('+','p').replace('-','m'), r) for r in args.rho]
    print(f"{'scheme':20s} {'rho(value, frequency)':>22s}  {'value spread (max/median)':>26s}")
    for name, rho in jobs:
        dv, qv, rhos, spreads = {}, {}, [], []
        deterministic = name in ("constant", "frequency_aligned", "runtime_proxy")
        trials = 1 if deterministic else args.num_trials
        for trial in range(trials):
            if rho is None:
                vals = assign(name, f, rt, rng, z1)
            else:
                y = rho*z1 + math.sqrt(max(0.0, 1-rho**2))*rng.standard_normal(n)
                vals = np.exp(1.5*y)
            rhos.append(spearman(list(f), list(vals)))
            med = np.median(vals[vals > 0]) if (vals > 0).any() else 1.0
            spreads.append(vals.max()/med if med else float("nan"))
            colval = {c: 0.0 for c in all_cols}
            for i, q in enumerate(queries):
                refs = [f"{t}.{c}" for t, cs in cols_in_q.get(q, {}).items() for c in cs]
                if not refs: continue
                share = vals[i]*freq[q]/len(refs)
                for c in refs: colval[c] += share
            dv[str(trial)] = colval
            qv[str(trial)] = {q: float(vals[i]) for i, q in enumerate(queries)}
        # a constant/deterministic scheme is replicated so rank.py can index any trial
        if deterministic:
            for t_ in range(1, args.num_trials):
                dv[str(t_)] = dv["0"]; qv[str(t_)] = qv["0"]
        json.dump(dv, open(out/f"imdb_data_val_cols_{name}.json", "w"), indent=4, sort_keys=True)
        with open(out/f"imdb_query_values_{name}.csv", "w", newline="") as fp:
            w = csv.writer(fp); w.writerow(["query_id"]+[str(i) for i in range(args.num_trials)])
            for q in queries:
                w.writerow([q]+[f"{qv[str(i)][q]:.6f}" for i in range(args.num_trials)])
        print(f"{name:20s} {np.mean(rhos):>22.3f}  {np.mean(spreads):>26.1f}")


if __name__ == "__main__":
    main()
