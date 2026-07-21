    # df["bytes_percent_diff"] = df["bytes_vod"] / df["bytes_freq"]
    # df["t_percent_diff"] = df["t_vod"] / df["t_freq"]
    # df["rows_percent_diff"] = df["rows_vod"] / df["rows_freq"]

    # df["rows_vod_random"] = 100 * (df["rows_random"] - df["rows_vod"]) / df["rows_random"]
    # df["rows_freq_random"] = 100 * (df["rows_random"] - df["rows_freq"]) / df["rows_random"]


    # foo = df.sort_values(by="value", ascending=False)
    # print(foo.head(10))

    # for k in [1, 3, 5, 10, 25, 50, len(df)]:
    #     agg_df = df.nlargest(k, "value")[["bytes_vod", "bytes_freq", "bytes_random", "t_random", "t_vod", "t_freq", "rows_vod", "rows_freq", "rows_random"]].sum()
    #     t_percent_diff = 100 * (agg_df["t_freq"] - agg_df["t_vod"]) / agg_df["t_freq"]
    #     b_percent_diff = 100 * (agg_df["bytes_freq"] - agg_df["bytes_vod"]) / agg_df["bytes_freq"]

    #     r_percent_diff = 100 * (agg_df["rows_freq"] - agg_df["rows_vod"]) / agg_df["rows_freq"]
    #     r1_percent_diff = 100 * (agg_df["rows_random"] - agg_df["rows_freq"]) / agg_df["rows_random"]
    #     r2_percent_diff = 100 * (agg_df["rows_random"] - agg_df["rows_vod"]) / agg_df["rows_random"]

    #     r_percent_diff = 100 * (agg_df["bytes_freq"] - agg_df["bytes_vod"]) / agg_df["bytes_freq"]
    #     r1_percent_diff = 100 * (agg_df["bytes_random"] - agg_df["bytes_freq"]) / agg_df["bytes_random"]
    #     r2_percent_diff = 100 * (agg_df["bytes_random"] - agg_df["bytes_vod"]) / agg_df["bytes_random"]


    #     # print(f"{b_percent_diff:.2f}% reduction in bytes read for top {k} value queries")
    #     # print(f"{t_percent_diff:.2f}% reduction in runtime for top {k} value queries")
    #     print(f"{r_percent_diff:.2f}% reduction in rows read for top {k} value queries")
    #     print(f"{r1_percent_diff:.2f}% reduction in rows read for top {k} value queries")
    #     print(f"{r2_percent_diff:.2f}% reduction in rows read for top {k} value queries")
    #     print("")

    # # # Display basic info
    # # print(f"Loaded {len(df)} rows")
    # # print("\nDataFrame shape:", df.shape)
    # # print("\nDataFrame columns:", df.columns.tolist())
    # # print("\nFirst few rows:")
    # # print(df.head(10))
    # # print("\nDataFrame info:")
    # # print(df.info())

