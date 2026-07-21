import json
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

# Define paths relative to script location
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
PROFILES_DIR = PROJECT_ROOT / "profiles_v1"
VALUE_DIR = PROFILES_DIR / "value"
FREQUENCY_DIR = PROFILES_DIR / "frequency"
PLAIN_DIR = PROFILES_DIR / "plain"
CSV_PATH = PROJECT_ROOT / "value_generation" / "tpcds_query_values_custom_v2.csv"


def load_json_field(json_path, field_name):
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            return data.get(field_name, None)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None

def load_profiles_to_dataframe():
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
    # Load CSV data
    csv_df = pd.read_csv(CSV_PATH)
    
    # Create a mapping from query_id to query_value
    # The CSV has columns: index, query_id, and a numeric value column (header is "0")
    # We'll use query_id as the key
    query_value_map = {}
    for _, row in csv_df.iterrows():
        query_id = row['query_id']
        # The third column (index 2) contains the query value
        query_value = row.iloc[2]  # Get the value from the third column
        query_value_map[query_id] = query_value
    
    # Initialize list to store rows
    rows = []
    
    # Iterate through query numbers 1-99
    for query_num in range(1, 100):
        # Format query number with leading zero (01, 02, ..., 99)
        query_num_str = f"{query_num:02d}"
        query_id = f"query_{query_num_str}"

        # Construct file paths
        value_json_path = VALUE_DIR / f"{query_num_str}_value.json"
        frequency_json_path = FREQUENCY_DIR / f"{query_num_str}_frequency.json"
        plain_json_path = PLAIN_DIR / f"{query_num_str}_plain.json"

        # Load data from value JSON
        value_total_bytes_read = load_json_field(value_json_path, "total_bytes_read")
        value_latency = load_json_field(value_json_path, "latency")
        value_rows = load_json_field(value_json_path, "cumulative_rows_scanned")

        # Load data from frequency JSON
        frequency_total_bytes_read = load_json_field(frequency_json_path, "total_bytes_read")
        frequency_latency = load_json_field(frequency_json_path, "latency")
        frequency_rows = load_json_field(frequency_json_path, "cumulative_rows_scanned")

        # Load data from plain JSON
        plain_bytes = load_json_field(plain_json_path, "total_bytes_read")
        plain_latency = load_json_field(plain_json_path, "latency")
        plain_rows = load_json_field(plain_json_path, "cumulative_rows_scanned")
        
        # Get query value from CSV
        query_value = query_value_map.get(query_id, None)

        # Create row dictionary
        row = {
            'query_id': query_id,
            'bytes_vod': value_total_bytes_read,
            't_vod': value_latency,
            'rows_vod': value_rows,
            'bytes_freq': frequency_total_bytes_read,
            't_freq': frequency_latency,
            'rows_freq': frequency_rows,
            'bytes_plain': plain_bytes,
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
    df = load_profiles_to_dataframe()
    df["bytes_percent_diff"] = df["bytes_vod"] / df["bytes_freq"]
    df["t_percent_diff"] = df["t_vod"] / df["t_freq"]
    df["rows_percent_diff"] = df["rows_vod"] / df["rows_freq"]

    df["rows_vod_plain"] = 100 * (df["rows_plain"] - df["rows_vod"]) / df["rows_plain"]
    df["rows_freq_plain"] = 100 * (df["rows_plain"] - df["rows_freq"]) / df["rows_plain"]


    foo = df.sort_values(by="value", ascending=False)
    print(foo.head(10))

    for k in [1, 3, 5, len(df)]:
        agg_df = df.nlargest(k, "value")[["bytes_vod", "bytes_freq", "t_vod", "t_freq", "rows_vod", "rows_freq", "rows_plain"]].sum()
        t_percent_diff = 100 * (agg_df["t_freq"] - agg_df["t_vod"]) / agg_df["t_freq"]
        b_percent_diff = 100 * (agg_df["bytes_freq"] - agg_df["bytes_vod"]) / agg_df["bytes_freq"]
        r_percent_diff = 100 * (agg_df["rows_freq"] - agg_df["rows_vod"]) / agg_df["rows_freq"]

        r1_percent_diff = 100 * (agg_df["rows_plain"] - agg_df["rows_freq"]) / agg_df["rows_plain"]
        r2_percent_diff = 100 * (agg_df["rows_plain"] - agg_df["rows_vod"]) / agg_df["rows_plain"]


        # print(f"{b_percent_diff:.2f}% reduction in bytes read for top {k} value queries")
        # print(f"{t_percent_diff:.2f}% reduction in runtime for top {k} value queries")
        print(f"{r_percent_diff:.2f}% reduction in rows read for top {k} value queries")
        print(f"{r1_percent_diff:.2f}% reduction in rows read for top {k} value queries")
        print(f"{r2_percent_diff:.2f}% reduction in rows read for top {k} value queries")
        print("")

    # # Display basic info
    # print(f"Loaded {len(df)} rows")
    # print("\nDataFrame shape:", df.shape)
    # print("\nDataFrame columns:", df.columns.tolist())
    # print("\nFirst few rows:")
    # print(df.head(10))
    # print("\nDataFrame info:")
    # print(df.info())

    # # Optionally save to CSV
    # output_path = Path("../profiles_combined.csv")
    # df.to_csv(output_path, index=False)
    # print(f"\nSaved to {output_path}")

    red = "#E65742"
    orange = "#FE9C22"
    yellow = "#F8DD3D"
    green = "#ADDC5A"
    blue = "#1F63A9"

    k_values = [1, 3, 5, 10, 25, len(df)]
    percent_diffs = []

    for k in k_values:
        agg_df = df.nlargest(k, "value")[["rows_freq", "rows_vod"]].sum()
        percent_diff = 100 * (agg_df["rows_freq"] - agg_df["rows_vod"]) / agg_df["rows_freq"]
        percent_diffs.append(percent_diff)
        print(f"{percent_diff:.2f}% reduction in rows scanned for top {k} value queries")

    x_positions = range(len(k_values))
    x_labels = [str(k) for k in k_values]
    x_labels[-1] = "All"

    plt.figure(figsize=(12, 6))
    plt.bar(x_positions, percent_diffs, color=orange)
    plt.xticks(ticks=list(x_positions), labels=x_labels)
    plt.xlabel("Number of top-value queries")
    plt.ylabel("Percent Difference in Total Rows Scanned (VOD vs Frequency)")
    # plt.ylim(top=63)
    plt.grid(axis='y', alpha=0.3, linestyle='--')

    filename = f"partitioning_rows_scanned_diff.pdf"
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

















