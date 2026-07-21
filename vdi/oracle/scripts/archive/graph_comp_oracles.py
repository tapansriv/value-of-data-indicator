import matplotlib.pyplot as plt
import json
import numpy as np
import re


def sum_agg(data):
    output = {k: sum(data[k]) for k in data}
    return output
    
def avg_agg(data):
    output = {}
    for k in data:
        if len(data[k]) > 0:
            output[k] = float(float(sum(data[k])) / float(len(data[k])))
        else: 
            output[k] = 0
    return output

def aggregation_methods(func_, data):
    assert func_ in ["sum", "median", "mean"], "invalid aggregation method"
    if func_ == "sum":
        return sum_agg(data)
    if func_ == "mean": 
        return avg_agg(data)
    raise NotImplementedError()

# CONSTS 
YLIM_MAX = 0.55
X = 36
Y = 12
R = 45

# TPCH/TPCDS Information
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


def graph_method(method: str, aggregation: str, normalized: bool = True, outfile: str = "", ylabel: str = "", 
                 ylimmax: float = YLIM_MAX, figsizeX = X, figsizeY = Y):
    assert method in ["boris", "data", "const"], "invalid method passed"

    prefix = f"../data/{method}_"
    if method == "data":
        prefix = "../data/"

    column_values = json.load(open(f"{prefix}data_val_cols.json"))
    column_table_aggregates = {tbl: [] for tbl in tables}

    for col in column_values:
        matches = []
        for tbl in tpch_cols_in_tbls:
            for col2 in tpch_cols_in_tbls[tbl]:
                if col == col2:
                    matches.append(tbl)
                    break
        for tbl in tpcds_cols_in_tbls:
            for col2 in tpcds_cols_in_tbls[tbl]:
                if col == col2:
                    if tbl == "customer":
                        matches.append("tpcds.customer")
                    else:
                        matches.append(tbl)
                    break

        assert len(matches) == 1, f"{matches}"
        # column_table_aggregates[matches[0]] += column_values[col]
        # column_table_aggregates[matches[0]].extend(column_values[col])
        tot = sum(column_values[col])
        column_table_aggregates[matches[0]].append(tot)
        # if tot > 0: 
        #     column_table_aggregates[matches[0]].append(tot)

        
    table_values = json.load(open(f"{prefix}data_val_tbls.json"))
    table_values2 = {}
    for k in table_values:
        table_values2[k] = [sum(table_values[k])]


    rg_values = json.load(open(f"{prefix}data_val_rgs_tbls.json"))
    rg_values2 = {}
    for k in rg_values: 
        output = []
        for rg in rg_values[k]:
            # output.extend(rg_values[k][rg])
            tot = sum(rg_values[k][rg])
            output.append(tot)
            # if tot > 0:
            #     output.append(tot)
        rg_values2[k] = output


    agg_column = aggregation_methods(aggregation, column_table_aggregates)
    agg_table = aggregation_methods(aggregation, table_values2)
    agg_rgs = aggregation_methods(aggregation, rg_values2)

    # Sample data
    labels = [t.capitalize() for t in tables]
    data1 = [agg_table[t] for t in tables]
    data2 = [agg_column[t] for t in tables]
    data3 = [agg_rgs[t] for t in tables]
    if normalized: 
        data1 = [d / sum(data1) for d in data1]
        data2 = [d / sum(data2) for d in data2]
        data3 = [d / sum(data3) for d in data3]

    print(f"{sum(data1)}, {sum(data2)}, {sum(data3)}")
    fig = plt.figure(figsize=(figsizeX,figsizeY))
    ax = fig.subplots()
    x = np.arange(len(labels))  
    width = 0.2  # Width of the bars

    # Create the bar plots
    ax.bar(x - width, data1, width, label='Table')
    ax.bar(x, data2, width, label='Column')
    plt.bar(x + width, data3, width, label='Row Group')

    # Add labels, title, and legend
    plt.ylabel(ylabel)
    plt.xticks(x, labels, rotation=R, ha='right')
    plt.ylim([0, ylimmax])
    plt.legend()

    plt.savefig(outfile)
    plt.clf()


def graph_broken(method: str, aggregation: str, ylim1: int, ylim2, ylim3, ylim4, 
                 normalized: bool = True, outfile: str="", ylabel: str = "", 
                 figsizeX = X, figsizeY = Y):

    assert method in ["boris", "data", "const"], "invalid method passed"

    prefix = f"../data/{method}_"
    if method == "data":
        prefix = "../data/"

    column_values = json.load(open(f"{prefix}data_val_cols.json"))
    column_table_aggregates = {tbl: [] for tbl in tables}

    for col in column_values:
        matches = []
        for tbl in tpch_cols_in_tbls:
            for col2 in tpch_cols_in_tbls[tbl]:
                if col == col2:
                    matches.append(tbl)
                    break
        for tbl in tpcds_cols_in_tbls:
            for col2 in tpcds_cols_in_tbls[tbl]:
                if col == col2:
                    if tbl == "customer":
                        matches.append("tpcds.customer")
                    else:
                        matches.append(tbl)
                    break

        assert len(matches) == 1, f"{matches}"
        column_table_aggregates[matches[0]].extend(column_values[col])

        
    table_values = json.load(open(f"{prefix}data_val_tbls.json"))
    rg_values = json.load(open(f"{prefix}data_val_rgs_tbls.json"))
    rg_values2 = {}
    for k in rg_values: 
        output = []
        for rg in rg_values[k]:
            output.extend(rg_values[k][rg])
        rg_values2[k] = output

    agg_column = aggregation_methods(aggregation, column_table_aggregates)
    agg_table = aggregation_methods(aggregation, table_values)
    agg_rgs = aggregation_methods(aggregation, rg_values2)

    # Sample data
    labels = [t.capitalize() for t in tables]
    data1 = [agg_table[t] for t in tables]
    data2 = [agg_column[t] for t in tables]
    data3 = [agg_rgs[t] for t in tables]
    if normalized: 
        data1 = [d / sum(data1) for d in data1]
        data2 = [d / sum(data2) for d in data2]
        data3 = [d / sum(data3) for d in data3]

    x = np.arange(len(labels))  # label locations
    width = 0.2  # width of the bars

    # Create two subplots sharing the same x-axis
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(X,Y), 
                                   gridspec_kw={'height_ratios': [1, 2]}
                                   )

    # Hide the spines between ax1 and ax2
    ax1.spines['bottom'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    ax1.tick_params(
        axis='x',          # changes apply to the x-axis
        which='both',      # both major and minor ticks are affected
        bottom=False,      # ticks along the bottom edge are off
        top=False,         # ticks along the top edge are off
        labelbottom=False  # labels along the bottom edge are off)
    )

    # Plot each set of bars on both axes
    ax1.bar(x - width, data1, width, label='Table')
    ax1.bar(x, data2, width, label='Column')
    ax1.bar(x + width, data3, width, label='Row Group')

    ax2.bar(x - width, data1, width, label='Table')
    ax2.bar(x, data2, width, label='Column')
    ax2.bar(x + width, data3, width, label='Row Group')

    # Set y-axis limits
    ax1.set_ylim(ylim3, ylim4)  # outlier range
    ax2.set_ylim(ylim1, ylim2)    # normal range

    d = .5  # proportion of vertical to horizontal extent of the slanted line
    kwargs = dict(marker=[(-1, -d), (1, d)], markersize=12,
                  linestyle="none", color='k', mec='k', mew=1, clip_on=False)
    ax1.plot([0, 1], [0, 0], transform=ax1.transAxes, **kwargs)
    ax2.plot([0, 1], [1, 1], transform=ax2.transAxes, **kwargs)

    # Labels and legend
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=45, ha='right')
    ax1.legend()

    plt.tight_layout()
    plt.subplots_adjust(hspace=0.05)
    plt.savefig(outfile)







graph_broken(method="data", aggregation="sum", normalized=False,
             outfile="../figs/oracle_gran.pdf", 
             ylim1=0, ylim2=2000, ylim3=2000, ylim4=1_000_000)
graph_method(method="data", aggregation="sum", normalized=True,
             outfile="../figs/oracle_gran_norm.pdf", 
             ylabel="Ratio of Total Value")

# graph_method(method="const", aggregation="sum", normalized=False,
#              outfile="../figs/const_oracle_gran.pdf")
graph_broken(method="const", aggregation="sum", normalized=False,
             outfile="../figs/const_oracle_gran.pdf",
             ylim1=0, ylim2=1.75, ylim3=1.75, ylim4=500)
graph_method(method="const", aggregation="sum", normalized=True,
             outfile="../figs/const_oracle_gran_norm.pdf", 
             ylabel="Ratio of Total Value")

graph_method(method="boris", aggregation="sum", normalized=False, outfile="../figs/boris_oracle_gran.pdf")
graph_method(method="boris", aggregation="sum", normalized=True,
             outfile="../figs/boris_oracle_gran_norm.pdf", 
             ylabel="Ratio of Total Value")

graph_broken(method="boris", aggregation="sum", normalized=False,
             outfile="../figs/boris_oracle_abs.pdf", 
             ylim1=0, ylim2=1.75, ylim3=1.75, ylim4=500)

graph_method(method="boris", aggregation="mean", normalized=False,
             outfile="../figs/boris_oracle_abs_mean.pdf", ylimmax=0.6) 

graph_method(method="data", aggregation="mean", normalized=False,
             outfile="../figs/data_oracle_abs_mean.pdf", ylimmax=50000) 


















