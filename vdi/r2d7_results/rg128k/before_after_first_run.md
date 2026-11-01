# Before/after: first R2D7 run vs rg128k rerun

Old: `/home/cc/value_of_data/value-of-data-metric/r2d7_results` (128 MiB RGs, 99 queries). New: `/mnt/tpcds/results_rg128k` (128,000-row RGs, query_set_131). zipf, N=1500, seed 42, 100 trials. Median share of total value, in %. Full CSV: `before_after_first_run.csv`.

## fig3_full

| table | SF30 old | SF30 new | SF60 old | SF60 new | SF100 old | SF100 new |
|---|---:|---:|---:|---:|---:|---:|
| date_dim | 18.17 | 19.18 | 18.17 | 19.18 | 18.17 | 19.18 |
| store_sales | 14.13 | 11.22 | 14.13 | 11.22 | 14.13 | 11.22 |
| tpcds.customer | 4.81 | 5.38 | 4.81 | 5.38 | 4.81 | 5.38 |
| store | 6.36 | 4.36 | 6.36 | 4.36 | 6.36 | 4.36 |
| catalog_sales | 7.66 | 8.15 | 7.66 | 8.15 | 7.66 | 8.15 |
| web_sales | 7.20 | 6.07 | 7.20 | 6.07 | 7.20 | 6.07 |
| inventory | 0.58 | 0.93 | 0.58 | 0.93 | 0.58 | 0.93 |
| customer_demographics | 1.95 | 2.94 | 1.95 | 2.94 | 1.95 | 2.94 |
| household_demographics | 1.85 | 2.22 | 1.85 | 2.22 | 1.85 | 2.22 |
| item | 10.93 | 12.65 | 10.93 | 12.65 | 10.93 | 12.65 |
| catalog_returns | 2.19 | 2.35 | 2.19 | 2.35 | 2.19 | 2.35 |
| store_returns | 2.84 | 1.99 | 2.84 | 1.99 | 2.84 | 1.99 |
| web_returns | 1.81 | 1.52 | 1.81 | 1.52 | 1.81 | 1.52 |

## fig3_equal

| table | SF30 old | SF30 new | SF60 old | SF60 new | SF100 old | SF100 new |
|---|---:|---:|---:|---:|---:|---:|
| date_dim | 19.42 | 20.72 | 19.42 | 20.72 | 19.42 | 20.72 |
| store_sales | 16.04 | 11.96 | 16.04 | 11.96 | 16.04 | 11.96 |
| tpcds.customer | 4.36 | 4.50 | 4.36 | 4.50 | 4.36 | 4.50 |
| store | 6.20 | 4.08 | 6.20 | 4.08 | 6.20 | 4.08 |
| catalog_sales | 6.61 | 7.22 | 6.61 | 7.22 | 6.61 | 7.22 |
| web_sales | 6.92 | 5.79 | 6.92 | 5.79 | 6.92 | 5.79 |
| inventory | 0.61 | 1.06 | 0.61 | 1.06 | 0.61 | 1.06 |
| customer_demographics | 1.40 | 2.21 | 1.40 | 2.21 | 1.40 | 2.21 |
| household_demographics | 1.69 | 1.67 | 1.69 | 1.67 | 1.69 | 1.67 |
| item | 12.54 | 14.82 | 12.54 | 14.82 | 12.54 | 14.82 |
| catalog_returns | 1.49 | 1.61 | 1.49 | 1.61 | 1.49 | 1.61 |
| store_returns | 2.14 | 1.49 | 2.14 | 1.49 | 2.14 | 1.49 |
| web_returns | 1.34 | 1.29 | 1.34 | 1.29 | 1.34 | 1.29 |

## fig3_cardinality

| table | SF30 old | SF30 new | SF60 old | SF60 new | SF100 old | SF100 new |
|---|---:|---:|---:|---:|---:|---:|
| date_dim | 0.13 | 0.20 | 0.06 | 0.10 | 0.04 | 0.06 |
| store_sales | 56.77 | 42.07 | 56.84 | 42.13 | 56.47 | 42.06 |
| tpcds.customer | 0.30 | 0.68 | 0.33 | 0.78 | 0.42 | 0.98 |
| store | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| catalog_sales | 17.17 | 19.68 | 17.17 | 19.73 | 16.32 | 18.81 |
| web_sales | 11.67 | 10.06 | 11.69 | 10.07 | 11.68 | 10.07 |
| inventory | 1.65 | 3.60 | 1.69 | 3.62 | 2.26 | 4.07 |
| customer_demographics | 0.48 | 1.22 | 0.25 | 0.68 | 0.15 | 0.42 |
| household_demographics | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| item | 0.35 | 0.27 | 0.35 | 0.26 | 0.36 | 0.28 |
| catalog_returns | 1.04 | 2.18 | 1.07 | 2.41 | 1.06 | 2.45 |
| store_returns | 2.07 | 2.41 | 2.13 | 2.54 | 2.13 | 2.55 |
| web_returns | 0.81 | 1.68 | 0.81 | 1.68 | 0.79 | 1.59 |

## fig4_column

| table | SF30 old | SF30 new | SF60 old | SF60 new | SF100 old | SF100 new |
|---|---:|---:|---:|---:|---:|---:|
| date_dim | 15.48 | 15.67 | 15.48 | 15.67 | 15.48 | 15.67 |
| store_sales | 19.45 | 14.32 | 19.45 | 14.32 | 19.45 | 14.32 |
| tpcds.customer | 4.96 | 5.68 | 4.96 | 5.68 | 4.96 | 5.68 |
| store | 4.46 | 2.83 | 4.46 | 2.83 | 4.46 | 2.83 |
| catalog_sales | 8.29 | 9.16 | 8.29 | 9.16 | 8.29 | 9.16 |
| web_sales | 8.07 | 6.45 | 8.07 | 6.45 | 8.07 | 6.45 |
| inventory | 0.77 | 1.38 | 0.77 | 1.38 | 0.77 | 1.38 |
| customer_demographics | 1.51 | 2.08 | 1.51 | 2.08 | 1.51 | 2.08 |
| household_demographics | 1.41 | 1.33 | 1.41 | 1.33 | 1.41 | 1.33 |
| item | 12.62 | 16.85 | 12.62 | 16.85 | 12.62 | 16.85 |
| catalog_returns | 1.26 | 1.54 | 1.26 | 1.54 | 1.26 | 1.54 |
| store_returns | 2.04 | 1.42 | 2.04 | 1.42 | 2.04 | 1.42 |
| web_returns | 1.32 | 1.18 | 1.32 | 1.18 | 1.32 | 1.18 |

## fig4_rowgroup

| table | SF30 old | SF30 new | SF60 old | SF60 new | SF100 old | SF100 new |
|---|---:|---:|---:|---:|---:|---:|
| date_dim | 3.48 | 1.34 | 2.11 | 1.00 | 1.29 | 0.64 |
| store_sales | 48.11 | 40.40 | 50.13 | 40.75 | 50.63 | 40.59 |
| tpcds.customer | 0.93 | 1.27 | 0.57 | 1.69 | 0.40 | 2.21 |
| store | 0.86 | 0.03 | 0.46 | 0.02 | 0.28 | 0.01 |
| catalog_sales | 17.99 | 18.84 | 18.91 | 19.02 | 18.98 | 18.23 |
| web_sales | 11.22 | 9.80 | 11.68 | 9.58 | 12.35 | 9.50 |
| inventory | 0.52 | 3.23 | 0.56 | 3.43 | 1.11 | 4.01 |
| customer_demographics | 0.38 | 1.81 | 0.23 | 1.33 | 0.15 | 0.92 |
| household_demographics | 0.41 | 0.12 | 0.25 | 0.08 | 0.16 | 0.06 |
| item | 2.62 | 1.32 | 1.76 | 1.07 | 1.16 | 1.27 |
| catalog_returns | 0.88 | 1.46 | 0.89 | 1.66 | 1.12 | 1.72 |
| store_returns | 1.60 | 1.94 | 1.89 | 1.93 | 2.02 | 1.88 |
| web_returns | 0.78 | 1.01 | 0.79 | 0.85 | 0.75 | 0.66 |

## Cross-SF stability (zipf)

| metric | first run | rerun |
|---|---|---|
| Spearman column/cardinality | 0.992–0.998 | 0.990–0.997 |
| Spearman column/equal | 1.000–1.000 | 1.000–1.000 |
| Spearman column/frequency | 1.000–1.000 | 1.000–1.000 |
| Spearman column/full | 1.000–1.000 | 1.000–1.000 |
| Spearman rowgroup/equal | 0.950–0.986 | 0.962–0.990 |
| Spearman rowgroup/frequency | 0.956–0.990 | 0.993–0.998 |
| Spearman rowgroup/full | 0.964–0.995 | 0.989–0.997 |
| Spearman table/cardinality | 0.981–0.994 | 0.992–0.998 |
| Spearman table/equal | 1.000–1.000 | 1.000–1.000 |
| Spearman table/frequency | 1.000–1.000 | 1.000–1.000 |
| Spearman table/full | 1.000–1.000 | 1.000–1.000 |
| strategy order same at every SF (table) | 24/24 [] | 22/23 ['catalog_returns'] |
| strategy order same at every SF (column) | 23/23 [] | 22/22 [] |
| granularity order differs across SFs | ['inventory'] | ['catalog_returns'] |
| VDI vs frequency flips (table) | [] of 24 | [] of 24 |
| VDI vs frequency flips (column) | [] of 24 | [] of 24 |
| VDI vs frequency flips (rowgroup) | ['catalog_returns'] of 14 | ['inventory'] of 12 |
| Full/Equal identical across SFs | True | True |

## Cross-SF stability (normal)

| metric | first run | rerun |
|---|---|---|
| Spearman column/cardinality | 0.994–0.999 | 0.986–0.996 |
| Spearman column/equal | 1.000–1.000 | 1.000–1.000 |
| Spearman column/frequency | 1.000–1.000 | 1.000–1.000 |
| Spearman column/full | 1.000–1.000 | 1.000–1.000 |
| Spearman rowgroup/equal | 0.894–0.972 | 0.978–0.995 |
| Spearman rowgroup/frequency | 0.956–0.990 | 0.993–0.998 |
| Spearman rowgroup/full | 0.957–0.990 | 0.993–0.998 |
| Spearman table/cardinality | 0.990–0.997 | 0.991–0.999 |
| Spearman table/equal | 1.000–1.000 | 1.000–1.000 |
| Spearman table/frequency | 1.000–1.000 | 1.000–1.000 |
| Spearman table/full | 1.000–1.000 | 1.000–1.000 |
| strategy order same at every SF (table) | 23/24 ['catalog_returns'] | 24/24 [] |
| strategy order same at every SF (column) | 24/24 [] | 24/24 [] |
| granularity order differs across SFs | ['catalog_returns', 'inventory', 'store_returns'] | ['customer_demographics', 'web_returns'] |
| VDI vs frequency flips (table) | [] of 24 | [] of 24 |
| VDI vs frequency flips (column) | [] of 24 | [] of 24 |
| VDI vs frequency flips (rowgroup) | [] of 15 | ['inventory'] of 14 |
| Full/Equal identical across SFs | True | True |
