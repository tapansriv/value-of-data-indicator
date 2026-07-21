import json
import numpy as np

import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

# Define paths relative to script location
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
CSV_PATH = PROJECT_ROOT / "value_generation" / "tpcds_query_values_custom.csv"

def load_json_field(json_path, field_name):
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            return data.get(field_name, None)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None

def load_profiles_to_dataframe(iter_):
    """
    Load profile data from JSON files and CSV into a pandas DataFrame.
    
    Returns:
        pandas.DataFrame with columns:
        - query_id: Query identifier (query_01, query_02, etc.)
        - value_total_bytes_read: From value JSON files
        - value_latency: From value JSON files
        - frequency_total_bytes_read: From frequency JSON files
        - frequency_latency: From frequency JSON files
        - query_value: From CSV file
    """
    PROFILES_DIR = PROJECT_ROOT / "data"/ f"profiles_{iter_}"
    VALUE_DIR = PROFILES_DIR / "value"
    FREQUENCY_DIR = PROFILES_DIR / "frequency"
    RANDOM_DIR = PROFILES_DIR / "random"
    PLAIN_DIR = PROJECT_ROOT / "data" / "plain"

    # Load CSV data
    vals = pd.read_csv(CSV_PATH)


    # Initialize list to store rows
    rows = []

    # Iterate through query numbers 1-99
    for query_num in range(1, 100):
        # Format query number with leading zero (01, 02, ..., 99)
        query_num_str = f"{query_num:02d}"
        query_id = f"{query_num_str}.sql"

        # Construct file paths
        value_json_path = VALUE_DIR / f"{query_num_str}_value.json"
        frequency_json_path = FREQUENCY_DIR / f"{query_num_str}_frequency.json"
        random_json_path = RANDOM_DIR / f"{query_num_str}_random.json"
        plain_json_path = PLAIN_DIR / f"{query_num_str}_plain.json"

        # Load data from value JSON
        value_total_bytes_read = load_json_field(value_json_path, "total_bytes_read")
        value_latency = load_json_field(value_json_path, "latency")
        value_rows = load_json_field(value_json_path, "cumulative_rows_scanned")

        # Load data from frequency JSON
        frequency_total_bytes_read = load_json_field(frequency_json_path, "total_bytes_read")
        frequency_latency = load_json_field(frequency_json_path, "latency")
        frequency_rows = load_json_field(frequency_json_path, "cumulative_rows_scanned")

        # Load data from random JSON
        random_bytes = load_json_field(random_json_path, "total_bytes_read")
        random_latency = load_json_field(random_json_path, "latency")
        random_rows = load_json_field(random_json_path, "cumulative_rows_scanned")


        # Load data from value JSON
        plain_total_bytes_read = load_json_field(plain_json_path, "total_bytes_read")
        plain_latency = load_json_field(plain_json_path, "latency")
        plain_rows = load_json_field(plain_json_path, "cumulative_rows_scanned")

        # Get query value from CSV
        query_value = vals[vals['query_id'] == query_id][str(iter_)].values[0]
        # print(query_value)
        # print(type(query_value))

        # Create row dictionary
        row = {
            'query_id': query_id,
            'bytes_vod': value_total_bytes_read,
            't_vod': value_latency,
            'rows_vod': value_rows,
            'bytes_freq': frequency_total_bytes_read,
            't_freq': frequency_latency,
            'rows_freq': frequency_rows,
            'bytes_random': random_bytes,
            't_random': random_latency,
            'rows_random': random_rows,
            'bytes_plain': plain_total_bytes_read,
            't_plain': plain_latency,
            'rows_plain': plain_rows,
            'value': query_value
        }
        
        rows.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    return df


if __name__ == "__main__":
    # Load the data
    VALUE_ITERS = [0, 1, 2, 3, 4]
    dfs = {}
    for iter_ in VALUE_ITERS:
        output_path = Path(f"../data/profiles_combined_{iter_}.csv")
        if not output_path.exists():
            df = load_profiles_to_dataframe(iter_)
            df.to_csv(output_path, index=False)
            print(f"\nSaved to {output_path}")
        else:
            df = pd.read_csv(output_path)
        dfs[iter_] = df

    red = "#E65742"
    orange = "#FE9C22"
    yellow = "#F8DD3D"
    green = "#ADDC5A"
    blue = "#1F63A9"

    k_values = [1, 3, 5, 10, 25, len(df)]
    percent_diffs = {k: [] for k in k_values}

    for k in k_values:
        for iter_ in VALUE_ITERS:
            df = dfs[iter_]
            agg_df = df.nlargest(k, "value")[["bytes_freq", "bytes_vod"]].sum()
            percent_diff = 100 * (agg_df["bytes_freq"] - agg_df["bytes_vod"]) / agg_df["bytes_freq"]
            percent_diffs[k].append(float(percent_diff))
        # print(f"{percent_diff:.2f}% reduction in bytes scanned for top {k} value queries")
        print(percent_diffs[k])

    values = np.array(list(percent_diffs.values()))  # shape: (num_keys, 5)
    x_labels = [str(k) for k in k_values]
    x_labels[-1] = "All"
    num_groups = len(k_values)
    num_bars = values.shape[1]
    x = np.arange(num_groups)
    width = 0.15

    # fig, ax = plt.subplots(figsize=(8, 5))
    # for i in range(num_bars):
    #     ax.bar(
    #         x + i * width,
    #         values[:, i],
    #         width,
    #         label=f"Value {i}"
    #     )
    # ax.set_xticks(x + width * (num_bars - 1) / 2)
    # ax.set_xticklabels(x_labels)
    # ax.set_ylabel("Bytes Read")
    # ax.legend()
    # plt.tight_layout()
    # plt.show()
    # plt.clf()

    workload_values = {k: [] for k in VALUE_ITERS}
    for iter_ in VALUE_ITERS:
        df = dfs[iter_]
        agg = df["value"] * (df["bytes_plain"] / df["bytes_vod"])
        vod_value = agg.sum()
        agg = df["value"] * (df["bytes_plain"] / df["bytes_freq"])
        freq_value = agg.sum()
        agg = df["value"] * (df["bytes_plain"] / df["bytes_random"])
        rand_value = agg.sum()

        agg = df["value"]
        plain_value = agg.sum()

        workload_values[iter_].extend([vod_value, freq_value, rand_value, plain_value])
        print(f"Iter {iter_}: VOD: {vod_value:.2f}, Freq: {freq_value:.2f}, Rand: {rand_value:.2f}, Plain: {plain_value:.2f}")

        freq_diff = 100 * (vod_value - freq_value) / freq_value
        rand_diff = 100 * (vod_value - rand_value) / rand_value
        print(f"Iter {iter_}: Freq: {freq_diff:.5f}% diff, Rand: {rand_diff:.2f}% diff")

    values = np.array(list(workload_values.values()))  # shape: num value iters, 3)
    # x_labels = [1, 50, 100, 500, 1000]
    x_labels = ["Constant", "Value 50" , "Value 100", "Value 500", "Value 1000"]
    group_labels = ["Value of Data", "Frequent", "Random", "No Sort"]
    x2 = "#F0964D"
    x3 = "#E4B935"

    colors = [x3, red, blue, green]
    num_groups = len(VALUE_ITERS)
    num_bars = values.shape[1]
    x = np.arange(num_groups)
    width = 0.15

    font = {'size': 14}
    plt.rc('font', **font)
    fig, ax = plt.subplots(figsize=(7.5, 3.5))
    for i in range(num_bars):
        ax.bar(
            x + i * width,
            values[:, i],
            width,
            label=group_labels[i],
            color=colors[i],
        )
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_xticks(x + width * (num_bars - 1) / 2)
    ax.set_xticklabels(x_labels)
    ax.set_xlabel("Maximum Query Value")
    ax.set_ylabel("Workload Utility")
    ax.legend()
    plt.tight_layout()
    plt.savefig("workload_value.pdf")
    plt.show()

    


    # plt.figure(figsize=(7, 4))
    # plt.bar(x_positions, percent_diffs, color=orange)
    # plt.xticks(ticks=list(x_positions), labels=x_labels)
    # plt.xlabel("Number of top-value queries")
    # plt.ylabel("% Difference in Bytes Read")
    # # plt.ylim(top=63)
    # plt.grid(axis='y', alpha=0.3, linestyle='--')

    # filename = f"partitioning_bytes_scanned_diff.pdf"
    # plt.tight_layout()
    # plt.savefig(filename)
    # plt.close()
    # plt.clf()

    # width = 0.35  # width of bars
    # x_positions = np.arange(len(k_values))
    # plt.figure(figsize=(8, 6))
    # plt.bar(x_positions - width/2, bytes_freq_vals, width, label='Frequency', color=red)  # orange-ish
    # plt.bar(x_positions + width/2, bytes_vod_vals, width, label='Value of Data', color=green)  # green-ish

    # plt.xticks(x_positions, [str(k) for k in k_values])
    # plt.xlabel("Number of top-value queries (k)")
    # plt.ylabel("Aggregated Bytes Read")
    # plt.title("Aggregated Bytes Read by Strategy Across Different k")
    # plt.legend()
    # plt.grid(axis='y', linestyle='--', alpha=0.5)
    # plt.tight_layout()

    # plt.show()
















