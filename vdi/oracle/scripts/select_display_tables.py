"""Choose the tables Figures 3/4 display, by a rule that can be rerun.

Each Sec 4.4 claim is a ratio between two boxes (or a box and the frequency marker) for one
table. A table *shows* a pattern in a direction when that ratio is beyond +/-THRESH at every
scale factor. The display set must show every (pattern, direction) that some visible table
shows. It always contains the tables the prose names; the rest is a greedy set cover, ties
broken by value.

  python select_display_tables.py ../../r2d7_results
"""
import sys
import numpy as np
import pandas as pd

R = sys.argv[1] if len(sys.argv) > 1 else "../../r2d7_results"
SFS = [30, 60, 100]
THRESH = 0.10        # ratio beyond 1.10 or below 1/1.10
MIN_SHARE = 0.01     # Equal median >= 1% so the box is legible at ylim 1.0
MIN_COVER = 2
FORCED = ["date_dim", "store_sales", "store", "tpcds.customer"]   # named in the prose

# pattern -> (numerator series, denominator series or ("freq", series))
PATTERNS = {
    "VDI vs frequency (Equal, Table)": ("fig3_equal", ("freq", "fig3_equal")),
    "Cardinality vs Equal (Table)": ("fig3_cardinality", "fig3_equal"),
    "Full vs Equal (Table)": ("fig3_full", "fig3_equal"),
    "Column vs Table (Equal)": ("fig4_column", "fig4_table"),
    "Row Group vs Table (Equal)": ("fig4_rowgroup", "fig4_table"),
}


def ratios(sf):
    d = pd.read_csv(f"{R}/sec44_after/sec44_numbers_spark_sf{sf}.csv")
    med = d.pivot(index="table", columns="series", values="median")
    frq = d.pivot(index="table", columns="series", values="frequency")
    out = {}
    for name, (num, den) in PATTERNS.items():
        dv = frq[den[1]] if isinstance(den, tuple) else med[den]
        out[name] = med[num] / dv
    return pd.DataFrame(out), med["fig3_equal"]


per_sf = {sf: ratios(sf) for sf in SFS}
share = per_sf[SFS[0]][1]
visible = sorted(share[share >= MIN_SHARE].index, key=lambda t: -share[t])

shows = {}   # table -> set of (pattern, direction)
for t in visible:
    s = set()
    for p in PATTERNS:
        r = [per_sf[sf][0].loc[t, p] for sf in SFS]
        if all(x > 1 + THRESH for x in r):
            s.add((p, "higher"))
        elif all(x < 1 / (1 + THRESH) for x in r):
            s.add((p, "lower"))
        elif all(1 / (1 + THRESH) <= x <= 1 + THRESH for x in r):
            s.add((p, "similar"))
    shows[t] = s

from collections import Counter
avail = Counter(k for t in visible for k in shows[t])
want = {k: min(avail[k], 1 if k[1] == "similar" else MIN_COVER) for k in avail}
chosen = list(FORCED)


def deficit(sel):
    have = Counter(k for t in sel for k in shows[t])
    return {k: want[k] - have[k] for k in want if have[k] < want[k]}


while deficit(chosen):
    d = deficit(chosen)
    best = max((t for t in visible if t not in chosen),
               key=lambda t: (sum(1 for k in shows[t] if k in d), share[t]))
    chosen.append(best)

print(f"visible tables (Equal median >= {MIN_SHARE:.0%}): {len(visible)}")
rows = []
for t in visible:
    row = {"table": t, "equal_share_%": round(100 * share[t], 2),
           "chosen": "*" if t in chosen else ""}
    for p in PATTERNS:
        r = [per_sf[sf][0].loc[t, p] for sf in SFS]
        tag = ("+" if (p, "higher") in shows[t] else "-" if (p, "lower") in shows[t]
               else "=" if (p, "similar") in shows[t] else "?")
        row[p.split(" (")[0]] = f"{tag} {np.round(r[0], 2)}/{np.round(r[-1], 2)}"
    rows.append(row)
print(pd.DataFrame(rows).to_string(index=False))
print("\n+ higher, - lower, = within +/-10% at every SF, ? changes across SFs; values SF30/SF100")
print("coverage in display set:")
have = Counter(k for t in chosen for k in shows[t])
for p in PATTERNS:
    print(f"  {p:34s}", "  ".join(f"{d}:{have[(p, d)]}/{avail[(p, d)]}" for d in ("higher", "lower", "similar")))
order = sorted(chosen, key=lambda t: -share[t])
print("\nDISPLAY SET:", ",".join(order))
