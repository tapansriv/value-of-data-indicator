from matplotlib.lines import Line2D
import math
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import json
import numpy as np
import re
from argparse import ArgumentParser

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
    boris_table_values_aggregates = json.load(open(f"../data/boris_data_val_tbls.json"))
    if normalized:
        total = sum([boris_table_values_aggregates[tbl] for tbl in boris_table_values_aggregates])
        for tbl in boris_table_values_aggregates:
            x = boris_table_values_aggregates[tbl]
            boris_table_values_aggregates[tbl] = x / total

    boris_column_values = json.load(open(f"../data/boris_data_val_cols.json"))
    boris_column_table_aggregates = {tbl: 0 for tbl in tables}
    for col in boris_column_values:
        tbl = get_table_for_column(col, tpch_cols_in_tbls, tpcds_cols_in_tbls)
        boris_column_table_aggregates[tbl] += boris_column_values[col]
    if normalized:
        total = sum([boris_column_table_aggregates[tbl] for tbl in boris_column_table_aggregates])
        for tbl in boris_column_table_aggregates:
            x = boris_column_table_aggregates[tbl]
            boris_column_table_aggregates[tbl] = x / total

    boris_rg_values = json.load(open(f"../data/boris_data_val_rgs_tbls.json"))
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

    subset_tables = ["date_dim", "tpcds.customer", "store_sales", "store",
                     "web_sales", "lineitem", "orders"]#, "part"]

    # CONSTS 
    X = 14.4
    Y = 7
    R = 45
    font = {'size': 24}
    plt.rc('font', **font)

    labels = [t.capitalize() for t in subset_tables]
    labels[1] = "Customer"
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
        l = labels[i]
        y = boris_vals[l.lower()]
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
    ax.set_xticks(positions, labels)#, rotation=R, ha='right')
    ax.set_xlabel("Table Name")
    ax.set_ylabel("% of Total Value" if normalized else "Total Value")
    ax.set_ylim([-0.05, 1.0] if normalized else None)

    legend_handles = [
        Patch(facecolor=full_color, label="Full"),
        Patch(facecolor=equal_color, label="Equal"),
        Patch(facecolor=card_color, label="Cardinality"),
        boris_handle
    ]

    ax.legend(handles=legend_handles, loc="upper right")
    plt.tight_layout()
    normstr = "normalized" if normalized else "absolute"
    plt.savefig(f"../figs/{distro}_{gran}_divide_compare_{normstr}.pdf")


def graph_divide_comp(tables, tpch_cols_in_tbls, tpcds_cols_in_tbls, distro, normalized=True):
    boris_table_values, _, _ = collect_boris_data(tables, tpch_cols_in_tbls, tpcds_cols_in_tbls)

    full_table_vals = json.load(open(f"../data/data_val_tbls_{distro}_full.json"))
    equal_table_vals = json.load(open(f"../data/data_val_tbls_{distro}_equal.json"))
    card_table_vals = json.load(open(f"../data/data_val_tbls_{distro}_cardinality.json"))

    full_cols_vals = json.load(open(f"../data/data_val_cols_{distro}_full.json"))
    equal_cols_vals = json.load(open(f"../data/data_val_cols_{distro}_equal.json"))
    card_cols_vals = json.load(open(f"../data/data_val_cols_{distro}_cardinality.json"))

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

    task_values = json.load(open(f"../data/total_vals_{distro}.json"))
    data_table_values = json.load(open(f"../data/data_val_tbls_{distro}_equal.json"))
    data_column_values = json.load(open(f"../data/data_val_cols_{distro}_equal.json"))
    data_rg_values = json.load(open(f"../data/data_val_rgs_tbls_{distro}_equal.json"))

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

    subset_tables = ["date_dim", "tpcds.customer","store", "store_sales", "web_sales", "lineitem",
         "orders"]#, "part"]
    # subset_tables = tables

    # CONSTS 
    font = {'size': 24}
    plt.rc('font', **font)
    X = 14.4
    Y = 7
    R = 45

    labels = [t.capitalize() for t in subset_tables]
    labels[1] = "Customer"
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
        l = labels[i]
        ax.scatter(positions[i] - width, boris_table_values_aggregates[l.lower()],
                   color=red, alpha=1.0, edgecolor='k', zorder=5, label="Foo")
        ax.scatter(positions[i], boris_column_table_aggregates[l.lower()],
                   color=red, alpha=1.0, edgecolor='k', zorder=5)
        ax.scatter(positions[i]+width, boris_rg_values_aggregates[l.lower()],
                   color=red, alpha=1.0, edgecolor='k', zorder=5)


    ax.set_xlim(-1.1, 16.1)
    ax.set_ylim(-0.05, 1.006 if normalized else 26904.52984889749)

    ax.set_xticks(positions, labels)#, rotation=R, ha='right')
    ax.set_xlabel("Table Name")
    ax.set_ylabel("% of Total Value" if normalized else "Total Value")

    boris_handle = Line2D([0], [0], marker='o', color=red, 
                          label="Frequency Value", markeredgecolor='k')
    legend_handles = [
        Patch(facecolor=blue, label="Table"),
        Patch(facecolor=yellow, label="Column"),
        Patch(facecolor=green, label="Row Group"),
        boris_handle
    ]
    ax.legend(handles=legend_handles, loc="upper right")
    plt.tight_layout()
    normstr = "normalized" if normalized else "absolute"
    # lims = ax.get_xlim()
    # print(lims)
    # lims = ax.get_ylim()
    # print(lims)
    plt.savefig(f"../figs/{distro}_granularity_compare_{normstr}.pdf")


if __name__ == "__main__":
    parser = ArgumentParser(description="Run time-series oracle")
    parser.add_argument("--distro", choices=["normal", "zipf"], default="zipf",
                        help="Distribution choice")
    parser.add_argument("--num-trials", type=int, default=100, 
                        help="Number of different value generation trials that were run")
    args = parser.parse_args()

    # TPCH/TPCDS tables and columns
    tpcds_tables = ["call_center", "catalog_page", "catalog_returns",
            "catalog_sales", "tpcds.customer", "customer_address",
            "customer_demographics", "date_dim", "household_demographics",
            "income_band", "inventory", "item", "promotion", "reason", "ship_mode",
            "store", "store_returns", "store_sales", "time_dim", "warehouse",
            "web_page", "web_returns", "web_sales", "web_site"]

    tpch_tables = [x.strip() for x in open("../data/table_names.csv").readlines()]
    assert len(set(tpcds_tables) & set(tpch_tables)) == 0
    tables = tpcds_tables + tpch_tables
    tpch_cols_in_tbls = json.load(open("../data/tpch_columns_in_tables.json"))
    tpcds_cols_in_tbls = json.load(open("../../tpcds_schema/tpcds_columns_in_tables.json"))

    graph_divide_comp(tables, tpch_cols_in_tbls, tpcds_cols_in_tbls, "normal", normalized=True)
    graph_divide_comp(tables, tpch_cols_in_tbls, tpcds_cols_in_tbls, "zipf", normalized=True)

    graph_granularity_comp(tables, tpch_cols_in_tbls, tpcds_cols_in_tbls,
                           "normal", normalized=False)
    graph_granularity_comp(tables, tpch_cols_in_tbls, tpcds_cols_in_tbls, "zipf",
                      normalized=True)

