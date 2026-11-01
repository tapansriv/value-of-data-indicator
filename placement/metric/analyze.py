import numpy as np
import pandas as pd
import json
from typing import List
import math
import matplotlib.pyplot as plt

import os
import numpy as np
import matplotlib.pyplot as plt

VALUE_ITERS = [0, 1, 2, 3, 4]
# VALUE_ITERS = [0, 1, 3, 4]
# TOP_KS = [1, 3, 5, 10, 15, 20, 99]  # None == ALL
TOP_KS = [1, 3, 10, 20, 99]  # None == ALL

def analyze_across_value_defs(query_keys, cache_size, vod_mode="dynamic"):
    """
    For a fixed cache size and VOD mode, compute percent runtime difference
    vs LRU across value definitions, and plot bars for each TOP-K cutoff.
    """

    # results[k] = list of percent diffs, one per value_iter
    results = {k: [] for k in TOP_KS}

    coldstr = "hot"
    dynstr = "dynamic" if vod_mode == "dynamic" else "static"

    # query_value_file = "../metadata/custom_v3/tpcds_query_values_custom.csv"
    query_value_file = "../metadata/tpcds_query_values_custom.csv"
    distrostr = "custom"
    cstr = str(cache_size)

    print("================================")
    print(f"Running experiment with {coldstr}, {dynstr}, distro={distrostr}, cache_size={cache_size}GB")


    for value_iter in VALUE_ITERS:
        # lrupath = f"../data/customv4/customv3_0_{cstr}"
        # dirpath = f"../data/customv4/customv3_{value_iter}_{cstr}"
        lrupath = f"../data/customv4_mod/customv3_0_{cstr}"
        dirpath = f"../data/customv4_mod/customv3_{value_iter}_{cstr}"
        # lrupath = f"../data/customv3/customv3_0_{cstr}"
        # dirpath = f"../data/customv3/customv3_{value_iter}_{cstr}"
        print(dirpath)

        if not os.path.isdir(dirpath):
            raise ValueError(f"Missing directory: {dirpath}")

        lru_file = f"lru_{coldstr}_static_30gb_aws_{distrostr}_{cstr}.json"
        vod_file = f"vod_{coldstr}_{dynstr}_30gb_aws_{distrostr}_{cstr}.json"
        # --- reuse existing JSON loading logic ---
        lru_path = os.path.join(lrupath, lru_file)
        vod_path = os.path.join(dirpath, vod_file)
        with open(lru_path) as f:
            lru_times = json.load(f)
        with open(vod_path) as f:
            vod_times = json.load(f)

        query_values = pd.read_csv(query_value_file).set_index("query_id")[str(value_iter)].to_dict()
        if value_iter == 0:
            # iter 0 is all equal, want to group by the same queries across iters
            query_values = pd.read_csv(query_value_file).set_index("query_id")["4"].to_dict()



        summary = []
        for query_key in query_keys:
            # pull data
            t_lru = lru_times[query_key]
            t_vod = vod_times[query_key]
            value = query_values[query_key]
            summary.append({
                "query_key": query_key,
                "t_lru": t_lru,
                "t_vod": t_vod,
                "value": value,
            })
        results_df = pd.DataFrame(summary)

        for k in TOP_KS:
            df = results_df.nlargest(k, "value")[["t_lru", "t_vod"]].sum()
            print(df)
            percent_diff = 100 * (df["t_lru"] - df["t_vod"]) / df["t_lru"]
            results[k].append(percent_diff)
            print(f"Value Iter: {value_iter}  {percent_diff:.2f}% reduction in runtime for top {k} value queries")
    plot_value_def_bars(results, cache_size, vod_mode)


def plot_value_def_bars(results, cache_size, vod_mode):
    """
    One bar per value definition, grouped by TOP-K.
    """
    red = "#E65742"
    orange = "#FE9C22"
    yellow = "#F8DD3D"
    green = "#ADDC5A"
    blue = "#1F63A9"
    
    colors = [blue, green, yellow, orange, red] 

    points = np.array(list(results.values())) # shape (num_k, num_value_iters)
    X = 8
    Y = 5.25

    ymin = -80
    ymax = 105

    if cache_size != 5.0:
        font = {'size': 22}
        plt.rc('font', **font)
    else: 
        font = {'size': 18}
        plt.rc('font', **font)
        X = 8
        Y = 4.75

    fig, ax = plt.subplots(figsize=(X, Y))
    labels = ["Constant", "Value 50", "Value 100", "Value 500", "Value 1000"]
    x = np.arange(len(TOP_KS))
    zs = np.zeros(len(TOP_KS))
    width = 0.15

    for i, k in enumerate(VALUE_ITERS):
        ax.bar(
            x + i * width,
            # points[:, i],
            zs,
            width,
            label=labels[i],
            color=colors[i],
        )

    ax.set_xticks(x + width * 2)
    ax.set_yticks([-75, -50, -25, 0, 25, 50, 75, 100])
    ax.set_xticklabels([f"All" if k == 99 else f"{k}" for k in TOP_KS ]) 
    ax.set_xlabel("Number of top-value queries")
    ax.set_ylabel("% Speedup vs LRU")
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim([ymin, ymax])
    # ax.set_title(f"VOD ({vod_mode}) vs LRU\nCache Size = {cache_size}")
    if cache_size in [5.0, 13.75]:
        ax.legend(ncol=2, loc="lower right")

    plt.tight_layout()
    plt.savefig(f"{vod_mode}_cache{str(cache_size).replace('.', 'p')}_value_defs.pdf",
                bbox_inches='tight')
    # plt.show()



def run_experiment(query_keys: List[str], cold: bool, dynamic: bool, distro: str = "normal", 
                   data_dir: str = "../data/custom_value", cache_size: int = 2.75):
    """
    break query keys into one of 4 categories
    pull baseline data for each query, pull lru and vod for each query. pull
    value for each query. compute metric for each . done.  
    """

    """ Pull runtime, value data """
    coldstr = "cold" if cold else "hot"
    dynstr = "dynamic" if dynamic else "static"

    value_iter = "4"
    if distro == "normal":
        distrostr = ""
        query_value_file = "../metadata/tpcds_query_values_mod.csv"
    elif distro == "zipf":
        distrostr = "_zipf"
        query_value_file = "../metadata/tpcds_query_values_zipf_mod.csv"
    elif distro == "custom1":
        distrostr = "_custom1"
        query_value_file = "../metadata/tpcds_query_values_custom.csv"
    elif distro == "custom2":
        value_iter = "1"
        distrostr = "_custom2"
        query_value_file = "../metadata/tpcds_query_values_custom.csv"
    else:
        raise ValueError(f"Unknown distro: {distro}")

    if cache_size != 2.75:
        distrostr += f"_{cache_size}"

    print("================================")
    print(f"Running experiment with {coldstr}, {dynstr}, distro={distro}, cache_size={cache_size}GB")
    results = []

    query_values = pd.read_csv(query_value_file).set_index("query_id")[value_iter].to_dict() # take first draw of values
    with open(f"{data_dir}/lru_{coldstr}_static_30gb_aws{distrostr}.json") as f:
        lru_times = json.load(f)
    with open(f"{data_dir}/vod_{coldstr}_{dynstr}_30gb_aws{distrostr}.json") as f:
        vod_times = json.load(f)


    vod_values = []
    vod_metric = 0
    lru_values = []
    lru_metric = 0
    for query_key in query_keys:
        # pull data
        t_lru = lru_times[query_key]
        t_vod = vod_times[query_key]
        value = query_values[query_key]
        results.append({
            "query_key": query_key,
            "t_lru": t_lru,
            "t_vod": t_vod,
            "value": value,
        })


    results_df = pd.DataFrame(results)

    red = "#E65742"
    orange = "#FE9C22"
    yellow = "#F8DD3D"
    green = "#ADDC5A"
    blue = "#1F63A9"

    k_values = [5, 10, 15, 20, len(results_df)]
    percent_diffs = []

    for k in k_values:
        df = results_df.nlargest(k, "value")[["t_lru", "t_vod"]].sum()
        percent_diff = 100 * (df["t_lru"] - df["t_vod"]) / df["t_lru"]
        percent_diffs.append(percent_diff)
        print(f"{percent_diff:.2f}% reduction in runtime for top {k} value queries")

    x_positions = range(len(k_values))
    x_labels = [str(k) for k in k_values]
    x_labels[-1] = "All"

    plt.figure(figsize=(6, 4))
    plt.bar(x_positions, percent_diffs, color=orange)
    plt.xticks(ticks=list(x_positions), labels=x_labels)
    plt.xlabel("Number of top-value queries")
    plt.ylabel("Percent Runtime Difference (VOD vs LRU)")
    plt.ylim(top=63)
    plt.grid(axis='y', alpha=0.3, linestyle='--')

    cache_size_str = str(cache_size).replace(".", "p")
    filename = f"percent_diff_{coldstr}_{dynstr}_{distro}_cache{cache_size_str}.pdf"
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()


if __name__ == "__main__":
    query_keys = [f"{num:02d}.sql" for num in range(1, 100)]  # TPC-DS has 99 queries
    sizes = [2.75, 3.5, 5.0, 7.5, 13.75]
    for cache_size in sizes:
        analyze_across_value_defs(query_keys, cache_size, vod_mode="dynamic")
        analyze_across_value_defs(query_keys, cache_size, vod_mode="static")


    # query_keys = [f"{num:02d}.sql" for num in range(1, 100)]  # TPC-DS has 99 queries
    # run_experiment(query_keys, cold=False, dynamic=False, distro="custom1", data_dir = "../data/custom_v2")
    # print("================================")
    # run_experiment(query_keys, cold=False, dynamic=True, distro="custom1", data_dir = "../data/custom_v2")
    # print("================================")
    # run_experiment(query_keys, cold=False, dynamic=False, distro="custom1",
    #                data_dir = "../data/custom_v2_5cache", cache_size=5)
    # print("================================")
    # run_experiment(query_keys, cold=False, dynamic=True, distro="custom1",
    #                data_dir = "../data/custom_v2_5cache", cache_size=5)
    # print("================================")



"""
set of queries
assign to each profile by percetnages
compute utility for each given profile
pull real and optimal runtimes from data
pull value from data as well
parameters in run_experiment for vod/lru, cold/hot, static/dynamic
"""
