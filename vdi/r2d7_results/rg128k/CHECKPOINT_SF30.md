# Checkpoint SF30 — rg128k rerun (record, not a gate)

Written after the SF30 capture. Capture dir `sf30/capture`; per-query JSON `sf30/pruning.json`; authored-query acceptance `sf30/rg_selective_acceptance.json`.

## 1. Row groups per table, old (128 MiB) vs new (128,000 rows)

SF30: row counts identical to old Parquet for 24/24 tables; mismatches []
| table | rows | RGs old (128 MiB) | RGs new (128k rows) | new rows/RG min–max | bytes old | bytes new |
|---|---:|---:|---:|---|---:|---:|
| call_center | 6 | 1 | 1 | 6–6 | 10,554 | 10,554 |
| catalog_page | 11,718 | 1 | 1 | 11,718–11,718 | 695,460 | 695,460 |
| catalog_returns | 4,322,293 | 3 | 34 | 98,293–128,000 | 315,134,377 | 310,264,723 |
| catalog_sales | 43,204,059 | 23 | 338 | 68,059–128,000 | 3,190,128,186 | 3,076,791,302 |
| customer | 433,000 | 1 | 4 | 49,000–128,000 | 23,180,731 | 23,482,470 |
| customer_address | 216,000 | 1 | 2 | 88,000–128,000 | 4,310,117 | 4,387,440 |
| customer_demographics | 1,920,800 | 1 | 16 | 800–128,000 | 7,825,107 | 7,789,031 |
| date_dim | 73,049 | 1 | 1 | 73,049–73,049 | 1,868,849 | 1,844,190 |
| household_demographics | 7,200 | 1 | 1 | 7,200–7,200 | 31,096 | 31,096 |
| income_band | 20 | 1 | 1 | 20–20 | 1,255 | 1,255 |
| inventory | 31,321,566 | 2 | 245 | 89,566–128,000 | 165,866,455 | 119,598,740 |
| item | 40,000 | 1 | 1 | 40,000–40,000 | 3,903,558 | 3,917,745 |
| promotion | 411 | 1 | 1 | 411–411 | 27,551 | 27,551 |
| reason | 75 | 1 | 1 | 75–75 | 2,481 | 2,481 |
| ship_mode | 20 | 1 | 1 | 20–20 | 2,700 | 2,700 |
| store | 78 | 1 | 1 | 78–78 | 17,356 | 17,356 |
| store_returns | 8,636,578 | 4 | 68 | 60,578–128,000 | 506,868,560 | 492,316,040 |
| store_sales | 86,406,277 | 29 | 676 | 6,277–128,000 | 3,994,951,074 | 3,971,931,595 |
| time_dim | 86,400 | 1 | 1 | 86,400–86,400 | 1,150,514 | 1,128,498 |
| warehouse | 6 | 1 | 1 | 6–6 | 4,605 | 4,605 |
| web_page | 468 | 1 | 1 | 468–468 | 12,625 | 12,625 |
| web_returns | 2,160,540 | 2 | 17 | 112,540–128,000 | 157,304,348 | 157,004,718 |
| web_sales | 21,598,604 | 11 | 169 | 94,604–128,000 | 1,454,184,473 | 1,449,862,400 |
| web_site | 26 | 1 | 1 | 26–26 | 12,040 | 12,040 |
errors: []

Every non-final row group has exactly 128,000 rows (verify.py assertion with RG_ROWS=128000; the last row group of each file holds the remainder).

## 2. Authored queries 132–163

| q | tmpl | base | target | added predicate | RGs read / total | frac | base reads | rows returned | accepted |
|---|---|---|---|---|---:|---:|---:|---:|---|
| 132 | A1 | q3 | store_sales | `store_sales.ss_ticket_number <= 74595` | 7/676 | 1.04% | 676 | 80 | yes |
| 133 | A2 | q3 | store_sales | `store_sales.ss_ticket_number <= 362614` | 34/676 | 5.03% | 676 | 100 | yes |
| 134 | A3 | q3 | store_sales | `store_sales.ss_ticket_number <= 725356` | 68/676 | 10.06% | 676 | 100 | yes |
| 135 | A4 | q3 | store_sales | `store_sales.ss_ticket_number <= 1802721` | 169/676 | 25.00% | 676 | 100 | yes |
| 136 | B1 | q12 | web_sales | `ws_order_number <= 21334` | 2/169 | 1.18% | 169 | 100 | yes |
| 137 | B2 | q12 | web_sales | `ws_order_number <= 85396` | 8/169 | 4.73% | 169 | 100 | yes |
| 138 | B3 | q12 | web_sales | `ws_order_number <= 181326` | 17/169 | 10.06% | 169 | 100 | yes |
| 139 | B4 | q12 | web_sales | `ws_order_number <= 448142` | 42/169 | 24.85% | 169 | 100 | yes |
| 140 | C1 | q20 | catalog_sales | `cs_sold_date_sk BETWEEN 2451944 AND 2451974` | 4/338 | 1.18% | 338 | 100 | yes |
| 141 | C2 | q20 | catalog_sales | `cs_sold_date_sk BETWEEN 2451915 AND 2452004` | 10/338 | 2.96% | 338 | 100 | yes |
| 142 | C3 | q20 | catalog_sales | `cs_sold_date_sk BETWEEN 2451870 AND 2452049` | 31/338 | 9.17% | 338 | 100 | yes |
| 143 | C4 | q20 | catalog_sales | `cs_sold_date_sk BETWEEN 2451777 AND 2452141` | 68/338 | 20.12% | 338 | 100 | yes |
| 144 | D1 | q22 | inventory | `inv_date_sk BETWEEN 2451697 AND 2451726` | 5/245 | 2.04% | 245 | 100 | yes |
| 145 | D2 | q22 | inventory | `inv_date_sk BETWEEN 2451697 AND 2451788` | 14/245 | 5.71% | 245 | 100 | yes |
| 146 | D3 | q22 | inventory | `inv_date_sk BETWEEN 2451697 AND 2451879` | 26/245 | 10.61% | 245 | 100 | yes |
| 147 | D4 | q22 | inventory | `inv_date_sk BETWEEN 2451697 AND 2452061` | 50/245 | 20.41% | 245 | 100 | yes |
| 148 | E1 | q84 | store_returns | `sr_ticket_number <= 106939` | 1/68 | 1.47% | 68 | 52 | yes |
| 149 | E2 | q84 | store_returns | `sr_ticket_number <= 747697` | 7/68 | 10.29% | 68 | 100 | yes |
| 150 | E3 | q84 | store_returns | `sr_ticket_number <= 1816451` | 17/68 | 25.00% | 68 | 100 | yes |
| 151 | E4 | q84 | store_returns | `sr_ticket_number <= 3630679` | 34/68 | 50.00% | 68 | 100 | yes |
| 152 | F1 | q91 | catalog_returns | `cr_returned_date_sk BETWEEN 2451514 AND 2451544` | 7/34 | 20.59% | 34 | 6 | yes |
| 153 | F2 | q91 | catalog_returns | `cr_returned_date_sk BETWEEN 2451455 AND 2451544` | 8/34 | 23.53% | 34 | 6 | yes |
| 154 | F3 | q91 | catalog_returns | `cr_returned_date_sk BETWEEN 2451365 AND 2451544` | 11/34 | 32.35% | 34 | 6 | yes |
| 155 | F4 | q91 | catalog_returns | `cr_returned_date_sk BETWEEN 2451180 AND 2451544` | 13/34 | 38.24% | 34 | 6 | yes |
| 156 | G1 | q30 | web_returns | `wr_order_number <= 106991` | 1/17 | 5.88% | 17 | 100 | yes |
| 157 | G2 | q30 | web_returns | `wr_order_number <= 320155` | 3/17 | 17.65% | 17 | 100 | yes |
| 158 | G3 | q30 | web_returns | `wr_order_number <= 427061` | 4/17 | 23.53% | 17 | 100 | yes |
| 159 | G4 | q30 | web_returns | `wr_order_number <= 960807` | 9/17 | 52.94% | 17 | 100 | yes |
| 160 | H1 | q26 | customer_demographics | `cd_demo_sk <= 128000` | 1/16 | 6.25% | 16 | 100 | yes |
| 161 | H2 | q26 | customer_demographics | `cd_demo_sk <= 256000` | 2/16 | 12.50% | 16 | 100 | yes |
| 162 | H3 | q26 | customer_demographics | `cd_demo_sk <= 512000` | 4/16 | 25.00% | 16 | 100 | yes |
| 163 | H4 | q26 | customer_demographics | `cd_demo_sk <= 1024000` | 8/16 | 50.00% | 16 | 100 | yes |

### Queries 100–131 (the pre-existing extra queries)

| q | rows | tables with RGs skipped (read/total) | big tables read |
|---|---:|---|---|
| 100 | 20 | none | store_sales 676/676 |
| 101 | 46 | none | store_sales 676/676 |
| 102 | 97 | none | store_sales 676/676 |
| 103 | 100 | none | store_sales 676/676 |
| 104 | 20 | none | store_sales 676/676 |
| 105 | 46 | none | store_sales 676/676 |
| 106 | 97 | none | store_sales 676/676 |
| 107 | 100 | none | store_sales 676/676 |
| 108 | 100 | none | web_sales 169/169 |
| 109 | 100 | none | web_sales 169/169 |
| 110 | 100 | none | web_sales 169/169 |
| 111 | 100 | none | web_sales 169/169 |
| 112 | 100 | customer 1/4 | catalog_sales 338/338, customer 1/4, customer_address 2/2 |
| 113 | 100 | customer 1/4 | catalog_sales 338/338, customer 1/4, customer_address 2/2 |
| 114 | 100 | customer 2/4 | catalog_sales 338/338, customer 2/4, customer_address 2/2 |
| 115 | 100 | customer 3/4 | catalog_sales 338/338, customer 3/4, customer_address 2/2 |
| 116 | 100 | none | catalog_sales 338/338, customer 4/4, customer_address 2/2 |
| 117 | 100 | none | catalog_sales 338/338, customer 4/4, customer_address 2/2 |
| 118 | 100 | none | catalog_sales 338/338, customer 4/4, customer_address 2/2 |
| 119 | 100 | none | catalog_sales 338/338, customer 4/4, customer_address 2/2 |
| 120 | 100 | none | customer 4/4, customer_address 2/2, customer_demographics 16/16, store_returns 68/68 |
| 121 | 100 | none | customer 4/4, customer_address 2/2, customer_demographics 16/16, store_returns 68/68 |
| 122 | 100 | none | customer 4/4, customer_address 2/2, customer_demographics 16/16, store_returns 68/68 |
| 123 | 100 | none | customer 4/4, customer_address 2/2, customer_demographics 16/16, store_returns 68/68 |
| 124 | 48 | none | customer 4/4, customer_address 2/2, customer_demographics 16/16, web_returns 17/17 |
| 125 | 100 | none | customer 4/4, customer_address 2/2, customer_demographics 16/16, web_returns 17/17 |
| 126 | 100 | none | customer 4/4, customer_address 2/2, customer_demographics 16/16, web_returns 17/17 |
| 127 | 100 | none | customer 4/4, customer_address 2/2, customer_demographics 16/16, web_returns 17/17 |
| 128 | 3 | none | catalog_returns 34/34, customer 4/4, customer_address 2/2, customer_demographics 16/16 |
| 129 | 5 | none | catalog_returns 34/34, customer 4/4, customer_address 2/2, customer_demographics 16/16 |
| 130 | 6 | none | catalog_returns 34/34, customer 4/4, customer_address 2/2, customer_demographics 16/16 |
| 131 | 6 | none | catalog_returns 34/34, customer 4/4, customer_address 2/2, customer_demographics 16/16 |

## 3. Queries 1–99 at 128,000-row row groups

99 of queries 1–99 captured cleanly. Queries 1–99 that skip any row group of any table: [16].

- q16: new catalog_returns 9/34, catalog_sales 321/338; old catalog_sales 10/23

| table | queries reading it (new) | mean RGs read/total new | queries pruning new | queries reading it (old) | mean read/total old | queries pruning old |
|---|---:|---:|---:|---:|---:|---:|
| call_center | 3 | 1.0000 | 0 | 3 | 1.0000 | 0 |
| catalog_page | 2 | 1.0000 | 0 | 2 | 1.0000 | 0 |
| catalog_returns | 13 | 0.9434 | 1 | 12 | 1.0000 | 0 |
| catalog_sales | 38 | 0.9987 | 1 | 38 | 0.9851 | 1 |
| customer | 28 | 1.0000 | 0 | 28 | 1.0000 | 0 |
| customer_address | 28 | 1.0000 | 0 | 28 | 1.0000 | 0 |
| customer_demographics | 13 | 1.0000 | 0 | 13 | 1.0000 | 0 |
| date_dim | 89 | 1.0000 | 0 | 89 | 1.0000 | 0 |
| household_demographics | 13 | 1.0000 | 0 | 13 | 1.0000 | 0 |
| income_band | 2 | 1.0000 | 0 | 2 | 1.0000 | 0 |
| inventory | 6 | 1.0000 | 0 | 6 | 1.0000 | 0 |
| item | 52 | 1.0000 | 0 | 52 | 1.0000 | 0 |
| promotion | 6 | 1.0000 | 0 | 5 | 1.0000 | 0 |
| reason | 3 | 1.0000 | 0 | 3 | 1.0000 | 0 |
| ship_mode | 3 | 1.0000 | 0 | 3 | 1.0000 | 0 |
| store | 33 | 1.0000 | 0 | 33 | 1.0000 | 0 |
| store_returns | 16 | 1.0000 | 0 | 16 | 1.0000 | 0 |
| store_sales | 66 | 1.0000 | 0 | 66 | 1.0000 | 0 |
| time_dim | 5 | 1.0000 | 0 | 5 | 1.0000 | 0 |
| warehouse | 8 | 1.0000 | 0 | 8 | 1.0000 | 0 |
| web_page | 3 | 1.0000 | 0 | 3 | 1.0000 | 0 |
| web_returns | 11 | 1.0000 | 0 | 11 | 1.0000 | 0 |
| web_sales | 36 | 1.0000 | 0 | 36 | 1.0000 | 0 |
| web_site | 5 | 1.0000 | 0 | 5 | 1.0000 | 0 |

**Findings, SF30.** At 128,000-row row groups no original query (1–99) skips row groups through its
own predicates on `customer_demographics` or `customer`, contrary to the plan's expectation:
`customer_demographics` cycles gender × marital × education every 70 rows, so every one of its 16 row
groups covers every value (see `sf30/order_profile.csv`), and the `customer` filters are not on
`c_customer_sk`. The only query in 1–99 with skipped row groups is q16. It skips the last 17 of 338
`catalog_sales` row groups (`cs_ship_date_sk` min ≥ 2452602 in each) and reads 9/34 `catalog_returns`.
q16 has no literal on either column (its date filter is on `date_dim`), so this is a runtime effect;
the cause was not identified. The first run also read only 10/23 `catalog_sales` row groups for q16, and
AQE skipped its `catalog_returns` scan entirely. Of 100–131, only 112–115 skip row groups (`customer`
1/1/2/3 of 4), as expected; every one of them still reads all of its fact table.

## 4. Driver memory and event-log size (SF30)

- Capture 04:27:15–04:44:27Z (17 min, 163 queries). 162/163 clean; q23 stmt 0 failed with the known
  `Decimal.toBigDecimal` NPE; retried 06:35Z after SF100 (both statements ok on the first retry), then `convert` rerun → 163/163.
- Event log: **481 MiB** (504,464,772 B) vs 194 MiB (203,510,263 B) in the first run (2.5×; stop line 1.95 GB).
- Driver JVM RSS peak **45.5 GB** (48 GB heap cap; sampled every 30 s in `capture_monitor.log`); no OOM.
  Minimum available host memory during the SF30 capture: 15.1 GB (of 62 GB).
