
    # data_table_values = json.load(open(f"../data/data_val_tbls.json"))
    # data_column_values = json.load(open(f"../data/data_val_cols.json"))
    # data_rg_values = json.load(open(f"../data/data_val_rgs_tbls.json"))

    # data_table_values_final = {tbl: [] for tbl in tables}
    # data_column_table_final = {tbl: [] for tbl in tables}
    # data_rg_values_final = {tbl: [] for tbl in tables}

    # for iter_ in range(args.num_trials):
    #     iter_key = str(iter_)

    #     total_value = total_values[iter_key]

    #     table_values = data_table_values[iter_key]
    #     column_values = data_column_values[iter_key]
    #     rg_values = data_rg_values[iter_key]

    #     # table aggregates normalized
    #     for tbl in data_table_values_final:
    #         data_table_values_final[tbl].append(table_values[tbl] / total_value)

    #     # column aggregates normalized
    #     data_column_table_aggregates = {tbl: 0 for tbl in tables}
    #     for col in column_values:
    #         tbl = get_table_for_column(col, tpch_cols_in_tbls, tpcds_cols_in_tbls)
    #         data_column_table_aggregates[tbl] += column_values[col]
    #     
    #     for tbl in tables: 
    #         norm_val_for_iter = data_column_table_aggregates[tbl] / total_value
    #         data_column_table_final[tbl].append(norm_val_for_iter)
    #     
    #     # rg aggregates normalized
    #     for tbl in rg_values:
    #         tot = 0
    #         for k in rg_values[tbl]:
    #             tot += rg_values[tbl][k]
    #         # avg = 0
    #         # if len(rg_values[tbl]) > 0:
    #         #     avg = tot / len(rg_values[tbl])
    #         data_rg_values_final[tbl].append((tot / total_value))

    # 
    # red = "#E65742"
    # orange = "#FE9C22"
    # yellow = "#F8DD3D"
    # green = "#ADDC5A"
    # blue = "#1F63A9"

    # # subset_tables = ["tpcds.customer", "store", "store_sales", "web_sales", "lineitem",
    # #      "orders", "part", "supplier"]
    # subset_tables = tables

    # # CONSTS 
    # X = 20
    # Y = 10
    # R = 45

    # labels = [t.capitalize() for t in subset_tables]
    # data1 = [data_table_values_final[t] for t in subset_tables]
    # data2 = [data_column_table_final[t] for t in subset_tables] 
    # data3 = [data_rg_values_final[t] for t in subset_tables]

    # fig, ax = plt.subplots(figsize=(X, Y))

    # positions = np.arange(len(labels)) * 2.5  # spacing
    # width = 0.6  # box width

    # # Boxplots
    # bp1 = ax.boxplot(data1, positions=positions - width, widths=width, patch_artist=True,
    #                  boxprops=dict(facecolor=blue), medianprops=dict(color='black'), 
    #                  tick_labels=labels)
    # # bp2 = ax.boxplot(data2, positions=positions, widths=width, patch_artist=True,
    # #                  boxprops=dict(facecolor=yellow),
    # #                  medianprops=dict(color='black'))

    # # bp3 = ax.boxplot(data3, positions=positions + width, widths=width, patch_artist=True,
    # #                  boxprops=dict(facecolor=green),
    # #                  medianprops=dict(color='black'))


    # for i in range(len(labels)):
    #     l = labels[i]
    #     ax.scatter(positions[i] - width, boris_table_values_aggregates[l.lower()],
    #                color=red, alpha=1.0, edgecolor='k', zorder=5)
    #     # ax.scatter(positions[i], boris_column_table_aggregates[l.lower()],
    #     #            color=red, alpha=1.0, edgecolor='k', zorder=5)
    #     # ax.scatter(positions[i]+width, boris_rg_values_aggregates[l.lower()],
    #     #            color=red, alpha=1.0, edgecolor='k', zorder=5)
    # # Axis formatting
    # ax.set_xticks(positions, labels, rotation=R, ha='right')
    # plt.tight_layout()
    # plt.savefig(f"../figs/{args.distro}_granularity_scatter.pdf")






# ====================================================================================








    # labels = [t.capitalize() for t in tables]
    # data1 = [data_table_values_final[t] for t in tables]
    # data2 = [data_column_table_final[t] for t in tables] 
    # data3 = [data_rg_values_final[t] for t in tables] 
    # 
    # fig, ax = plt.subplots(figsize=(X, Y))
    # 
    # positions = np.arange(len(labels)) * 2.5  # spacing
    # width = 0.6  # box width
    # 
    # # Boxplots
    # bp1 = ax.boxplot(data1, positions=positions, widths=width, patch_artist=True,
    #                  boxprops=dict(facecolor='lightblue'), medianprops=dict(color='blue'), 
    #                  tick_labels=labels)
    # 
    # for i in range(len(labels)):
    #     l = labels[i]
    #     ax.scatter(positions[i], boris_table_values_aggregates[l.lower()],
    #                color='darkred', alpha=1.0, edgecolor='k', zorder=5)
    # 
    # ax.set_xticks(positions, labels, rotation=R, ha='right')
    # plt.savefig('../figs/normal_vs_boris_tables.pdf')
    # 
    # plt.clf()

    # labels = [t.capitalize() for t in tables]
    # data1 = [data_table_values_final[t] for t in tables]
    # data2 = [data_column_table_final[t] for t in tables] 
    # data3 = [data_rg_values_final[t] for t in tables] 
    # 
    # fig, ax = plt.subplots(figsize=(X, Y))
    # 
    # positions = np.arange(len(labels)) * 2.5  # spacing
    # width = 0.6  # box width
    # 
    # # Boxplots
    # bp1 = ax.boxplot(data2, positions=positions, widths=width, patch_artist=True,
    #                  boxprops=dict(facecolor='bisque'),
    #                  medianprops=dict(color='orange'), 
    #                  tick_labels=labels)
    # 
    # for i in range(len(labels)):
    #     l = labels[i]
    #     ax.scatter(positions[i], boris_column_table_aggregates[l.lower()],
    #                color='darkred', alpha=1.0, edgecolor='k', zorder=5)
    # 
    # ax.set_xticks(positions, labels, rotation=R, ha='right')
    # plt.savefig('../figs/normal_vs_boris_columns.pdf')
    # 
    # plt.clf()

    # labels = [t.capitalize() for t in tables]
    # data1 = [data_table_values_final[t] for t in tables]
    # data2 = [data_column_table_final[t] for t in tables] 
    # data3 = [data_rg_values_final[t] for t in tables] 
    # 
    # fig, ax = plt.subplots(figsize=(X, Y))
    # 
    # positions = np.arange(len(labels)) * 2.5  # spacing
    # width = 0.6  # box width
    # 
    # # Boxplots
    # bp1 = ax.boxplot(data3, positions=positions, widths=width, patch_artist=True,
    #                  boxprops=dict(facecolor='lightgreen'),
    #                  medianprops=dict(color='green'), 
    #                  tick_labels=labels)
    # 
    # for i in range(len(labels)):
    #     l = labels[i]
    #     ax.scatter(positions[i], boris_rg_values_aggregates[l.lower()],
    #                color='darkred', alpha=1.0, edgecolor='k', zorder=5)
    # 
    # ax.set_xticks(positions, labels, rotation=R, ha='right')
    # plt.savefig('../figs/normal_vs_boris_rgs.pdf')

