# Authored queries 132–163: pruning and rows returned per SF

Measured by the main capture (`sf<N>/capture`). RGs = target table's row groups read / total. Literals fixed at SF30 calibration. All 32 accepted at every SF (rows ≥ 1, < base, monotone).

| q | tmpl | base → target | added predicate | SF30 RGs | SF30 rows | SF60 RGs | SF60 rows | SF100 RGs | SF100 rows |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| 132 | A1 | q3 → store_sales | `store_sales.ss_ticket_number <= 74595` | 7/676 (1.04%) | 80 | 7/1351 (0.52%) | 100 | 7/2250 (0.31%) | 100 |
| 133 | A2 | q3 → store_sales | `store_sales.ss_ticket_number <= 362614` | 34/676 (5.03%) | 100 | 34/1351 (2.52%) | 100 | 34/2250 (1.51%) | 100 |
| 134 | A3 | q3 → store_sales | `store_sales.ss_ticket_number <= 725356` | 68/676 (10.06%) | 100 | 68/1351 (5.03%) | 100 | 68/2250 (3.02%) | 100 |
| 135 | A4 | q3 → store_sales | `store_sales.ss_ticket_number <= 1802721` | 169/676 (25.00%) | 100 | 169/1351 (12.51%) | 100 | 169/2250 (7.51%) | 100 |
| 136 | B1 | q12 → web_sales | `ws_order_number <= 21334` | 2/169 (1.18%) | 100 | 2/338 (0.59%) | 100 | 2/563 (0.36%) | 100 |
| 137 | B2 | q12 → web_sales | `ws_order_number <= 85396` | 8/169 (4.73%) | 100 | 8/338 (2.37%) | 100 | 8/563 (1.42%) | 100 |
| 138 | B3 | q12 → web_sales | `ws_order_number <= 181326` | 17/169 (10.06%) | 100 | 17/338 (5.03%) | 100 | 17/563 (3.02%) | 100 |
| 139 | B4 | q12 → web_sales | `ws_order_number <= 448142` | 42/169 (24.85%) | 100 | 42/338 (12.43%) | 100 | 42/563 (7.46%) | 100 |
| 140 | C1 | q20 → catalog_sales | `cs_sold_date_sk BETWEEN 2451944 AND 2451974` — 2001-02-03 .. 2001-03-05 (31 days) | 4/338 (1.18%) | 100 | 7/676 (1.04%) | 100 | 12/1125 (1.07%) | 100 |
| 141 | C2 | q20 → catalog_sales | `cs_sold_date_sk BETWEEN 2451915 AND 2452004` — 2001-01-05 .. 2001-04-04 (90 days) | 10/338 (2.96%) | 100 | 20/676 (2.96%) | 100 | 33/1125 (2.93%) | 100 |
| 142 | C3 | q20 → catalog_sales | `cs_sold_date_sk BETWEEN 2451870 AND 2452049` — 2000-11-21 .. 2001-05-19 (180 days) | 31/338 (9.17%) | 100 | 60/676 (8.88%) | 100 | 100/1125 (8.89%) | 100 |
| 143 | C4 | q20 → catalog_sales | `cs_sold_date_sk BETWEEN 2451777 AND 2452141` — 2000-08-20 .. 2001-08-19 (365 days) | 68/338 (20.12%) | 100 | 135/676 (19.97%) | 100 | 225/1125 (20.00%) | 100 |
| 144 | D1 | q22 → inventory | `inv_date_sk BETWEEN 2451697 AND 2451726` — 2000-06-01 .. 2000-06-30 (d_month_seq 1205..1205) | 5/245 (2.04%) | 100 | 12/529 (2.27%) | 100 | 60/3120 (1.92%) | 100 |
| 145 | D2 | q22 → inventory | `inv_date_sk BETWEEN 2451697 AND 2451788` — 2000-06-01 .. 2000-08-31 (d_month_seq 1205..1207) | 14/245 (5.71%) | 100 | 30/529 (5.67%) | 100 | 168/3120 (5.38%) | 100 |
| 146 | D3 | q22 → inventory | `inv_date_sk BETWEEN 2451697 AND 2451879` — 2000-06-01 .. 2000-11-30 (d_month_seq 1205..1210) | 26/245 (10.61%) | 100 | 56/529 (10.59%) | 100 | 323/3120 (10.35%) | 100 |
| 147 | D4 | q22 → inventory | `inv_date_sk BETWEEN 2451697 AND 2452061` — 2000-06-01 .. 2001-05-31 (d_month_seq 1205..1216) | 50/245 (20.41%) | 100 | 109/529 (20.60%) | 100 | 634/3120 (20.32%) | 100 |
| 148 | E1 | q84 → store_returns | `sr_ticket_number <= 106939` | 1/68 (1.47%) | 52 | 1/135 (0.74%) | 90 | 1/225 (0.44%) | 100 |
| 149 | E2 | q84 → store_returns | `sr_ticket_number <= 747697` | 7/68 (10.29%) | 100 | 7/135 (5.19%) | 100 | 7/225 (3.11%) | 100 |
| 150 | E3 | q84 → store_returns | `sr_ticket_number <= 1816451` | 17/68 (25.00%) | 100 | 17/135 (12.59%) | 100 | 17/225 (7.56%) | 100 |
| 151 | E4 | q84 → store_returns | `sr_ticket_number <= 3630679` | 34/68 (50.00%) | 100 | 34/135 (25.19%) | 100 | 34/225 (15.11%) | 100 |
| 152 | F1 | q91 → catalog_returns | `cr_returned_date_sk BETWEEN 2451514 AND 2451544` — 1999-12-01 .. 1999-12-31 (31 days) | 7/34 (20.59%) | 6 | 13/68 (19.12%) | 10 | 20/113 (17.70%) | 30 |
| 153 | F2 | q91 → catalog_returns | `cr_returned_date_sk BETWEEN 2451455 AND 2451544` — 1999-10-03 .. 1999-12-31 (90 days) | 8/34 (23.53%) | 6 | 14/68 (20.59%) | 10 | 22/113 (19.47%) | 30 |
| 154 | F3 | q91 → catalog_returns | `cr_returned_date_sk BETWEEN 2451365 AND 2451544` — 1999-07-05 .. 1999-12-31 (180 days) | 11/34 (32.35%) | 6 | 20/68 (29.41%) | 10 | 31/113 (27.43%) | 30 |
| 155 | F4 | q91 → catalog_returns | `cr_returned_date_sk BETWEEN 2451180 AND 2451544` — 1999-01-01 .. 1999-12-31 (365 days) | 13/34 (38.24%) | 6 | 25/68 (36.76%) | 10 | 41/113 (36.28%) | 30 |
| 156 | G1 | q30 → web_returns | `wr_order_number <= 106991` | 1/17 (5.88%) | 100 | 1/34 (2.94%) | 100 | 1/57 (1.75%) | 100 |
| 157 | G2 | q30 → web_returns | `wr_order_number <= 320155` | 3/17 (17.65%) | 100 | 3/34 (8.82%) | 100 | 3/57 (5.26%) | 100 |
| 158 | G3 | q30 → web_returns | `wr_order_number <= 427061` | 4/17 (23.53%) | 100 | 4/34 (11.76%) | 100 | 4/57 (7.02%) | 100 |
| 159 | G4 | q30 → web_returns | `wr_order_number <= 960807` | 9/17 (52.94%) | 100 | 9/34 (26.47%) | 100 | 9/57 (15.79%) | 100 |
| 160 | H1 | q26 → customer_demographics | `cd_demo_sk <= 128000` | 1/16 (6.25%) | 100 | 1/16 (6.25%) | 100 | 1/16 (6.25%) | 100 |
| 161 | H2 | q26 → customer_demographics | `cd_demo_sk <= 256000` | 2/16 (12.50%) | 100 | 2/16 (12.50%) | 100 | 2/16 (12.50%) | 100 |
| 162 | H3 | q26 → customer_demographics | `cd_demo_sk <= 512000` | 4/16 (25.00%) | 100 | 4/16 (25.00%) | 100 | 4/16 (25.00%) | 100 |
| 163 | H4 | q26 → customer_demographics | `cd_demo_sk <= 1024000` | 8/16 (50.00%) | 100 | 8/16 (50.00%) | 100 | 8/16 (50.00%) | 100 |

Base queries read all target RGs at every SF: True
Accepted at every SF: True
