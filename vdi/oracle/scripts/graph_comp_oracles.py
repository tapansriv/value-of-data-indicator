from matplotlib.lines import Line2D
import math
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import json
import os
import numpy as np
import re
from argparse import ArgumentParser

# Display labels for the tables in subset_tables. Keyed by table name so the
# frequency baseline is looked up by KEY, never by lowercased label: "Customer"
# lowercases to "customer", which is the TPC-H table, while the boxes above it are
# tpcds.customer. That mismatch drew 0.105 where 0.317 belonged (raw) in Fig 3.
TABLE_LABELS = {
    "date_dim": "Date_dim",
    "store_sales": "Store_sales",
    "tpcds.customer": "Customer",
    "lineitem": "Lineitem",
    "store": "Store",
    "household_demographics": "HH_demo",
    "customer_demographics": "Cust_demo",
    "income_band": "Inc_band",
    "item": "Item",
    "catalog_sales": "Catalog_sales",
    "store_returns": "Store_returns",
    "catalog_returns": "Cat_returns",
}


def label_for(tbl):
    return TABLE_LABELS.get(tbl, tbl.capitalize())


# The revision's displayed table set (rationale in plot_divide()).
SUBSET_TABLES = ["date_dim", "store_sales", "tpcds.customer", "lineitem",
                 "store", "household_demographics", "customer_demographics"]


def display_tables():
    """Tables drawn in Figures 3/4. --tables overrides; --tpcds-only drops the TPC-H
    table (lineitem) from the revision set, since the R2D7 capture has no TPC-H."""
    if args.tables:
        return args.tables.split(",")
    if args.tpcds_only:
        return [t for t in SUBSET_TABLES if t not in ("lineitem", "orders")]
    return SUBSET_TABLES


def get_table_for_column(col, tpch_cols_in_tbls, tpcds_cols_in_tbls):
    matches = []
    for tbl in tpch_cols_in_tbls:
        for col2 in tpch_cols_in_tbls[tbl]:
            if col == col2:
                matches.append(tbl)
    for tbl in tpcds_cols_in_tbls:
        for col2 in tpcds_cols_in_tbls[tbl]:
            if col == col2:
                if tbl == "customer":
                    matches.append("tpcds.customer")
                else:
                    matches.append(tbl)
    assert len(matches) == 1, f"Found {matches} for column {col}"
    return matches[0]

def collect_boris_data(tables, tpch_cols_in_tbls, tpcds_cols_in_tbls,
                       normalized=False):
    # accumulate boris data
    boris_table_values_aggregates = json.load(open(f"{args.data_dir}/boris_data_val_tbls.json"))
    if normalized:
        total = sum([boris_table_values_aggregates[tbl] for tbl in boris_table_values_aggregates])
        for tbl in boris_table_values_aggregates:
            x = boris_table_values_aggregates[tbl]
            boris_table_values_aggregates[tbl] = x / total

    boris_column_values = json.load(open(f"{args.data_dir}/boris_data_val_cols.json"))
    boris_column_table_aggregates = {tbl: 0 for tbl in tables}
    for col in boris_column_values:
        tbl = get_table_for_column(col, tpch_cols_in_tbls, tpcds_cols_in_tbls)
        boris_column_table_aggregates[tbl] += boris_column_values[col]
    if normalized:
        total = sum([boris_column_table_aggregates[tbl] for tbl in boris_column_table_aggregates])
        for tbl in boris_column_table_aggregates:
            x = boris_column_table_aggregates[tbl]
            boris_column_table_aggregates[tbl] = x / total

    boris_rg_values = json.load(open(f"{args.data_dir}/boris_data_val_rgs_tbls.json"))
    boris_rg_values_aggregates = {}
    for k in boris_rg_values:
        output = sum([boris_rg_values[k][rg] for rg in boris_rg_values[k]])
        boris_rg_values_aggregates[k] = output

    if normalized:
        total = sum([boris_rg_values_aggregates[tbl] for tbl in boris_rg_values_aggregates])
        for tbl in boris_rg_values_aggregates:
            x = boris_rg_values_aggregates[tbl]
            boris_rg_values_aggregates[tbl] = x / total
    return boris_table_values_aggregates, boris_column_table_aggregates, boris_rg_values_aggregates

def plot_divide(full, equal, card, boris_vals, distro, gran, normalized=True):
    red = "#E65742"
    orange = "#FE9C22"
    lightgreen = "#7F9C64"
    greenblue = "#2CBA9A"

    yellow = "#F8DD3D"
    green = "#ADDC5A"
    blue = "#1F63A9"

    full_color = orange
    equal_color = lightgreen
    card_color = greenblue

    # Pre-revision set, kept for history. Chosen before the frequency baseline was
    # normalized; web_sales and orders are named nowhere in Sec 4.4's prose.
    # subset_tables = ["date_dim", "tpcds.customer", "store_sales", "store",
    #                  "web_sales", "lineitem", "orders"]#, "part"]
    #
    # Revision set: a sample allocated proportionally to a k=7 clustering of all 31
    # non-empty tables over the five behaviours these figures display (VDI/freq,
    # Cardinality/Equal, Full/Equal, Column/Table, RowGroup/Table). Covers 6 of 7
    # clusters and reproduces the population's 3:1 skew toward frequency assigning
    # MORE share than VDI (19 of 31 tables) -- the pre-revision set showed that as
    # 3:2. Keeps every table Sec 4.4 names by name.
    #
    # customer_demographics stands in for income_band, which the clustering picked
    # first: the two carry the same trend (VDI/freq 0.584 vs 0.585, Full/Equal 1.445
    # vs 1.426) but customer_demographics holds 2.7x the value, which halves the
    # figure's dynamic range from 15.4x to 7.5x. It also fills a gap in Fig 4 --
    # RowGroup/Table 0.97, value spread evenly across its 16 row groups, where the
    # rest of the set is either ~0 or > 1.8. The cost is that cluster 0
    # {income_band, call_center} goes unrepresented; every member of it is too
    # low-value to plot, which is itself the point and belongs in the cover letter.
    subset_tables = display_tables()

    # CONSTS 
    X = 14.4
    Y = 7
    R = 45
    font = {'size': 24}
    plt.rc('font', **font)

    labels = [label_for(t) for t in subset_tables]
    data1 = [full[t] for t in subset_tables]
    data2 = [equal[t] for t in subset_tables] 
    data3 = [card[t] for t in subset_tables]

    fig, ax = plt.subplots(figsize=(X, Y))

    positions = np.arange(len(labels)) * 2.5  # spacing
    width = 0.6  # box width

    # Boxplots
    bp1 = ax.boxplot(data1, positions=positions - width, widths=width, patch_artist=True,
                     boxprops=dict(facecolor=full_color), medianprops=dict(color='black'), 
                     tick_labels=labels)
    bp2 = ax.boxplot(data2, positions=positions, widths=width, patch_artist=True,
                     boxprops=dict(facecolor=equal_color),
                     medianprops=dict(color='black'))

    bp3 = ax.boxplot(data3, positions=positions + width, widths=width, patch_artist=True,
                     boxprops=dict(facecolor=card_color),
                     medianprops=dict(color='black'))


    for i in range(len(labels)):
        y = boris_vals[subset_tables[i]]
        left = positions[i] - 1.5 * width
        right = positions[i] + 1.5 * width
        ax.hlines(
            y=y,
            xmin=left,
            xmax=right,
            colors=red,
            linewidth=2.5,
            zorder=5
        )
    # Axis formatting
    boris_handle = Line2D([0], [0],
                          color=red,
                          linewidth=2.5,
                          label="Frequency Value")
    ax.set_xticks(positions, labels, **({"rotation": args.xrot, "ha": "right", "rotation_mode": "anchor"} if args.xrot else {}))
    ax.set_xlabel("Table Name")
    ax.set_ylabel("Fraction of Total Value" if normalized else "Total Value")
    # 0.70 is the knee of the clipping trade-off: over the 2100 plotted points it
    # hides exactly one (store_sales/Cardinality at 0.961) and cuts no box, median
    # or whisker, while giving the smaller tables 1.43x more vertical room. Below
    # ~0.60 the Cardinality upper whiskers (store_sales 0.694, lineitem 0.476)
    # start being cut, and that long upper tail is the defining feature of the
    # strategy. The one point above the limit is marked at the axis edge rather
    # than dropped silently.
    TOP = args.ylim
    ax.set_ylim([-0.05, TOP] if normalized else None)
    if normalized:
        for data, off in [(data1, -width), (data2, 0), (data3, width)]:
            for i in range(len(subset_tables)):
                above = [v for v in data[i] if v > TOP]
                if not above:
                    continue
                ax.plot([positions[i] + off], [TOP], marker="^", color="black",
                        markersize=9, clip_on=False, zorder=6)
                ax.annotate(f"{max(above):.2f}", xy=(positions[i] + off, TOP),
                            xytext=(5, -22), textcoords="offset points", fontsize=16)

    legend_handles = [
        Patch(facecolor=full_color, label="Full"),
        Patch(facecolor=equal_color, label="Equal"),
        Patch(facecolor=card_color, label="Cardinality"),
        boris_handle
    ]

    if args.legend_top:
        ax.legend(handles=legend_handles, loc="lower center", bbox_to_anchor=(0.5, 1.0),
                  ncol=len(legend_handles), frameon=False, handlelength=1.2, columnspacing=1.0)
    else:
        ax.legend(handles=legend_handles, loc="upper right")
    plt.tight_layout()
    normstr = "normalized" if normalized else "absolute"
    plt.savefig(f"{args.fig_dir}/{distro}_{gran}_divide_compare_{normstr}.pdf")


def graph_divide_comp(tables, tpch_cols_in_tbls, tpcds_cols_in_tbls, distro, normalized=True):
    # Forward `normalized`: without it collect_boris_data defaults to False and the
    # red line is the RAW access fraction (summing to ~4.17 across tables, the mean
    # tables-per-query) drawn over boxes that are shares summing to 1. Fig 4 already
    # passed it, so the two figures plotted the same baseline on scales 4.17x apart.
    boris_table_values, _, _ = collect_boris_data(tables, tpch_cols_in_tbls,
                                                  tpcds_cols_in_tbls,
                                                  normalized=normalized)

    full_table_vals = json.load(open(f"{args.data_dir}/data_val_tbls_{distro}_full.json"))
    equal_table_vals = json.load(open(f"{args.data_dir}/data_val_tbls_{distro}_equal.json"))
    card_table_vals = json.load(open(f"{args.data_dir}/data_val_tbls_{distro}_cardinality.json"))

    full_cols_vals = json.load(open(f"{args.data_dir}/data_val_cols_{distro}_full.json"))
    equal_cols_vals = json.load(open(f"{args.data_dir}/data_val_cols_{distro}_equal.json"))
    card_cols_vals = json.load(open(f"{args.data_dir}/data_val_cols_{distro}_cardinality.json"))

    column_names = full_cols_vals["0"].keys()
    full_table_final = {tbl: [] for tbl in tables}
    equal_table_final = {tbl: [] for tbl in tables}
    card_table_final = {tbl: [] for tbl in tables}

    full_cols_final = {tbl: [] for tbl in tables}
    equal_cols_final = {tbl: [] for tbl in tables}
    card_cols_final = {tbl: [] for tbl in tables}

    for iter_ in range(args.num_trials):
        iter_key = str(iter_)

        full_values = full_table_vals[iter_key]
        tot_full = sum([full_values[tbl] for tbl in full_values])
        equal_values = equal_table_vals[iter_key]
        tot_equal = sum([equal_values[tbl] for tbl in equal_values])
        card_values = card_table_vals[iter_key]
        tot_card = sum([card_values[tbl] for tbl in card_values])

        for tbl in tables:
            if normalized:
                full_table_final[tbl].append(full_values[tbl] / tot_full) 
                equal_table_final[tbl].append(equal_values[tbl] / tot_equal)
                card_table_final[tbl].append(card_values[tbl] / tot_card)
            else:
                full_table_final[tbl].append(full_values[tbl]  ) 
                equal_table_final[tbl].append(equal_values[tbl])
                card_table_final[tbl].append(card_values[tbl]  )


        full_values = full_cols_vals[iter_key]
        tot_full = sum([full_values[col] for col in full_values])
        equal_values = equal_cols_vals[iter_key]
        tot_equal = sum([equal_values[col] for col in equal_values])
        card_values = card_cols_vals[iter_key]
        tot_card = sum([card_values[col] for col in card_values])

        # column aggregates normalized
        full_column_table_aggregates = {tbl: 0 for tbl in tables}
        equal_column_table_aggregates = {tbl: 0 for tbl in tables}
        card_column_table_aggregates = {tbl: 0 for tbl in tables}
        for col in column_names:
            tbl = get_table_for_column(col, tpch_cols_in_tbls, tpcds_cols_in_tbls)
            full_column_table_aggregates[tbl] += full_values[col]
            equal_column_table_aggregates[tbl] += equal_values[col]
            card_column_table_aggregates[tbl] += card_values[col]

        for tbl in tables: 
            if normalized:
                full_for_iter  = full_column_table_aggregates[tbl]  / tot_full
                equal_for_iter = equal_column_table_aggregates[tbl] / tot_equal
                card_for_iter  = card_column_table_aggregates[tbl]  / tot_card
            else:
                full_for_iter  = full_column_table_aggregates[tbl] 
                equal_for_iter = equal_column_table_aggregates[tbl]
                card_for_iter  = card_column_table_aggregates[tbl] 
            full_cols_final[tbl].append(full_for_iter)
            equal_cols_final[tbl].append(equal_for_iter)
            card_cols_final[tbl].append(card_for_iter)
    
    plot_divide(full_table_final, equal_table_final, card_table_final,
                boris_table_values, distro, "table", normalized)
    plot_divide(full_cols_final, equal_cols_final, card_cols_final,
                boris_table_values, distro, "column", normalized)


def graph_granularity_comp(tables, tpch_cols_in_tbls, tpcds_cols_in_tbls, distro, normalized=True):
    boris_table_values_aggregates, boris_column_table_aggregates, boris_rg_values_aggregates = collect_boris_data(tables, tpch_cols_in_tbls,
                                                    tpcds_cols_in_tbls,
                                                    normalized=normalized) 

    task_values = json.load(open(f"{args.data_dir}/total_vals_{distro}.json"))
    data_table_values = json.load(open(f"{args.data_dir}/data_val_tbls_{distro}_equal.json"))
    data_column_values = json.load(open(f"{args.data_dir}/data_val_cols_{distro}_equal.json"))
    data_rg_values = json.load(open(f"{args.data_dir}/data_val_rgs_tbls_{distro}_equal.json"))

    data_table_values_final = {tbl: [] for tbl in tables}
    data_column_table_final = {tbl: [] for tbl in tables}
    data_rg_values_final = {tbl: [] for tbl in tables}

    for iter_ in range(args.num_trials):
        iter_key = str(iter_)

        total_value = task_values[iter_key]

        table_values = data_table_values[iter_key]
        tot_table = sum([table_values[tbl] for tbl in table_values])
        assert math.isclose(tot_table, total_value), f"Total value {total_value} does not match sum of table values {tot_table}"

        column_values = data_column_values[iter_key]
        tot_column = sum([column_values[col] for col in column_values])
        assert math.isclose(tot_column, total_value), f"Total value {total_value} does not match sum of column values {tot_column}"

        rg_values = data_rg_values[iter_key]
        tot_rg = sum([rg_values[tbl][rg] for tbl in rg_values for rg in rg_values[tbl]])
        assert math.isclose(tot_rg, total_value), f"Total value {total_value} does not match sum of row group values {tot_rg}"

        # table aggregates normalized
        for tbl in data_table_values_final:
            if normalized:
                data_table_values_final[tbl].append(table_values[tbl] / total_value)
            else:
                data_table_values_final[tbl].append(table_values[tbl])

        # column aggregates normalized
        data_column_table_aggregates = {tbl: 0 for tbl in tables}
        for col in column_values:
            tbl = get_table_for_column(col, tpch_cols_in_tbls, tpcds_cols_in_tbls)
            data_column_table_aggregates[tbl] += column_values[col]

        for tbl in tables: 
            if normalized:
                val_for_iter = data_column_table_aggregates[tbl] / total_value
            else:
                val_for_iter = data_column_table_aggregates[tbl]
            data_column_table_final[tbl].append(val_for_iter)

        # rg aggregates normalized
        for tbl in rg_values:
            tot = 0
            for k in rg_values[tbl]:
                tot += rg_values[tbl][k]
            if normalized:
                data_rg_values_final[tbl].append((tot / total_value))
            else:
                data_rg_values_final[tbl].append(tot)

    red = "#E65742"
    orange = "#FE9C22"
    yellow = "#F8DD3D"
    green = "#ADDC5A"
    blue = "#1F63A9"

    # Pre-revision set, kept for history. See the note in plot_divide().
    # subset_tables = ["date_dim", "tpcds.customer","store", "store_sales", "web_sales", "lineitem",
    #      "orders"]#, "part"]
    # subset_tables = tables
    subset_tables = display_tables()

    # CONSTS 
    font = {'size': 24}
    plt.rc('font', **font)
    X = 14.4
    Y = 7
    R = 45

    labels = [label_for(t) for t in subset_tables]
    data1 = [data_table_values_final[t] for t in subset_tables]
    data2 = [data_column_table_final[t] for t in subset_tables] 
    data3 = [data_rg_values_final[t] for t in subset_tables]

    fig, ax = plt.subplots(figsize=(X, Y))

    positions = np.arange(len(labels)) * 2.5  # spacing
    width = 0.6  # box width

    # Boxplots
    bp1 = ax.boxplot(data1, positions=positions - width, widths=width, patch_artist=True,
                     boxprops=dict(facecolor=blue), medianprops=dict(color='black'), 
                     tick_labels=labels)
    bp2 = ax.boxplot(data2, positions=positions, widths=width, patch_artist=True,
                     boxprops=dict(facecolor=yellow),
                     medianprops=dict(color='black'))

    bp3 = ax.boxplot(data3, positions=positions + width, widths=width, patch_artist=True,
                     boxprops=dict(facecolor=green),
                     medianprops=dict(color='black'))


    for i in range(len(labels)):
        l = subset_tables[i]
        ax.scatter(positions[i] - width, boris_table_values_aggregates[l],
                   color=red, alpha=1.0, edgecolor='k', zorder=5, label="Foo")
        ax.scatter(positions[i], boris_column_table_aggregates[l],
                   color=red, alpha=1.0, edgecolor='k', zorder=5)
        ax.scatter(positions[i]+width, boris_rg_values_aggregates[l],
                   color=red, alpha=1.0, edgecolor='k', zorder=5)


    # 16.1 for the seven-table set, as before; follows the number of tables otherwise
    ax.set_xlim(-1.1, positions[-1] + 1.1)
    # Matched to plot_divide's limit so the two figures share a scale -- they sit
    # adjacent in Sec 4.4 under the same y-label. Costs one point here too
    # (store_sales/RowGroup at 0.958) and no box, median or whisker.
    TOP = args.ylim
    ax.set_ylim(-0.05, TOP if normalized else 26904.52984889749)
    if normalized:
        for data, off in [(data1, -width), (data2, 0), (data3, width)]:
            for i in range(len(subset_tables)):
                above = [v for v in data[i] if v > TOP]
                if not above:
                    continue
                ax.plot([positions[i] + off], [TOP], marker="^", color="black",
                        markersize=9, clip_on=False, zorder=6)
                ax.annotate(f"{max(above):.2f}", xy=(positions[i] + off, TOP),
                            xytext=(5, -22), textcoords="offset points", fontsize=16)

    ax.set_xticks(positions, labels, **({"rotation": args.xrot, "ha": "right", "rotation_mode": "anchor"} if args.xrot else {}))
    ax.set_xlabel("Table Name")
    ax.set_ylabel("Fraction of Total Value" if normalized else "Total Value")

    boris_handle = Line2D([0], [0], marker='o', color=red, 
                          label="Frequency Value", markeredgecolor='k')
    legend_handles = [
        Patch(facecolor=blue, label="Table"),
        Patch(facecolor=yellow, label="Column"),
        Patch(facecolor=green, label="Row Group"),
        boris_handle
    ]
    if args.legend_top:
        ax.legend(handles=legend_handles, loc="lower center", bbox_to_anchor=(0.5, 1.0),
                  ncol=len(legend_handles), frameon=False, handlelength=1.2, columnspacing=1.0)
    else:
        ax.legend(handles=legend_handles, loc="upper right")
    plt.tight_layout()
    normstr = "normalized" if normalized else "absolute"
    # lims = ax.get_xlim()
    # print(lims)
    # lims = ax.get_ylim()
    # print(lims)
    plt.savefig(f"{args.fig_dir}/{distro}_granularity_compare_{normstr}.pdf")


if __name__ == "__main__":
    parser = ArgumentParser(description="Run time-series oracle")
    parser.add_argument("--distro", choices=["normal", "zipf", "both"], default="both",
                        help="Distribution choice")
    parser.add_argument("--num-trials", type=int, default=100, 
                        help="Number of different value generation trials that were run")
    parser.add_argument("--data-dir", default="../data",
                        help="Directory holding the result files to plot. Point this at "
                             "a sweep point (../data/sweep/N<n>_s<seed>) to regenerate the "
                             "figures for that history size. Static schema inputs are "
                             "always read from ../data.")
    parser.add_argument("--fig-dir", default="../figs",
                        help="Directory to write figures into. Give each sweep point its "
                             "own so they do not overwrite each other.")
    parser.add_argument("--tpcds-only", action="store_true",
                        help="Results come from a TPC-DS-only run (R2D7 Spark capture)")
    parser.add_argument("--ylim", type=float, default=0.70,
                        help="Upper y-limit of the normalized figures. 0.70 was chosen on "
                             "the Drill data (hides one point). On the R2D7 Spark data it "
                             "hides 18 and cuts the store_sales whisker; use 1.0 there.")
    parser.add_argument("--legend-top", action="store_true",
                        help="One-row legend above the axes instead of inside (keeps fliers visible)")
    parser.add_argument("--xrot", type=float, default=0,
                        help="Rotate table-name tick labels by this many degrees (0 = none)")
    parser.add_argument("--tables", default=None,
                        help="Comma-separated tables to draw, overriding the default set")
    args = parser.parse_args()

    os.makedirs(args.fig_dir, exist_ok=True)

    # TPCH/TPCDS tables and columns
    tpcds_tables = ["call_center", "catalog_page", "catalog_returns",
            "catalog_sales", "tpcds.customer", "customer_address",
            "customer_demographics", "date_dim", "household_demographics",
            "income_band", "inventory", "item", "promotion", "reason", "ship_mode",
            "store", "store_returns", "store_sales", "time_dim", "warehouse",
            "web_page", "web_returns", "web_sales", "web_site"]

    tpch_tables = [x.strip() for x in open("../data/table_names.csv").readlines()]
    assert len(set(tpcds_tables) & set(tpch_tables)) == 0
    tables = tpcds_tables if args.tpcds_only else tpcds_tables + tpch_tables
    tpch_cols_in_tbls = json.load(open("../data/tpch_columns_in_tables.json"))
    tpcds_cols_in_tbls = json.load(open("../../tpcds_schema/tpcds_columns_in_tables.json"))

    distros = ["normal", "zipf"] if args.distro == "both" else [args.distro]
    for distro in distros:
        graph_divide_comp(tables, tpch_cols_in_tbls, tpcds_cols_in_tbls, distro,
                          normalized=True)
        # normal has historically been plotted on an absolute scale, zipf normalized
        graph_granularity_comp(tables, tpch_cols_in_tbls, tpcds_cols_in_tbls, distro,
                               normalized=(distro == "zipf"))

