import json 
import math
import os
import subprocess
import time
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from argparse import ArgumentParser

tpcds_tables = ["call_center", "catalog_page", "catalog_returns",
        "catalog_sales", "tpcds.customer", "customer_address",
        "customer_demographics", "date_dim", "household_demographics",
        "income_band", "inventory", "item", "promotion", "reason", "ship_mode",
        "store", "store_returns", "store_sales", "time_dim", "warehouse",
        "web_page", "web_returns", "web_sales", "web_site"]

def get_table_for_column(col):
    tpch_cols_in_tbls = json.load(open("../data/tpch_columns_in_tables.json"))
    tpcds_cols_in_tbls = json.load(open("../../tpcds_schema/tpcds_columns_in_tables.json"))
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

DEFAULT_OUT_DIR = "../data"


class Inputs:
    """Where a run's inputs live. The defaults reproduce the original Drill-based layout
    (TPC-H + TPC-DS, logs under ../drill_logs and ../tpcds_drill_logs, SF30 cardinality).

    The R2D7 Spark capture is TPC-DS only and keeps everything per scale factor under
    /mnt/tpcds/results/sf<N>: point logs_dir at the spark_rg_to_access.py output and
    the other paths at that SF's files, and set tpcds_only.
    """
    def __init__(self, logs_dir=None, values_dir="../data",
                 columns_in_queries="../data/tpcds_columns_in_queries.json",
                 cardinality="./tpcds_cardinality.json", tpcds_only=False,
                 query_set=None):
        self.tpch_logs_dir = "../drill_logs"
        self.tpcds_logs_dir = logs_dir or "../tpcds_drill_logs"
        self.values_dir = values_dir
        self.columns_in_queries = columns_in_queries
        self.cardinality = cardinality
        self.tpcds_only = tpcds_only
        # JSON list of TPC-DS query numbers overriding tpcds_completed.json, e.g. the
        # queries that completed at every scale factor so the SFs share one history
        self.query_set = query_set

    def schemas(self):
        return ["tpcds"] if self.tpcds_only else ["tpch", "tpcds"]

    def as_dict(self):
        return dict(vars(self))


def _git_revision():
    """Best-effort git commit of the checkout this script runs from."""
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        rev = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=here,
                                      stderr=subprocess.DEVNULL).decode().strip()
        dirty = subprocess.call(["git", "diff", "--quiet", "HEAD"], cwd=here,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL) != 0
        return rev + ("-dirty" if dirty else "")
    except Exception:
        return "unknown"


def write_manifest(out_dir, args, distros, query_set, unique, counts, inputs):
    """Record the exact constants behind a run alongside its results.

    Every result directory has to be self-describing: the revision will be
    re-run at least once before the final submission, and a sweep is only
    interpretable if each point states the history size and seed it came from.
    """
    manifest = {
        "num_samples": args.num_samples,
        "seed": args.seed,
        "num_trials": args.num_trials,
        "distros": list(distros),
        "query_set_size": len(query_set),
        "distinct_queries_drawn": int(len(unique)),
        "queries_never_drawn": len(query_set) - int(len(unique)),
        # min/max are over the queries that were drawn at least once
        "min_query_count": int(counts.min()),
        "max_query_count": int(counts.max()),
        "out_dir": os.path.abspath(out_dir),
        "inputs": {k: (os.path.abspath(v) if isinstance(v, str) else v)
                   for k, v in inputs.as_dict().items()},
        "git_revision": _git_revision(),
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as fp:
        json.dump(manifest, fp, indent=4, sort_keys=True)
    return manifest


def compute_boris_metric(qdm, unique, relative_query_frequencies, query_set,
                         out_dir=DEFAULT_OUT_DIR):
    # initialize baseline collection (boris's metric)
    boris_columns = {l: 0 for l in qdm.columns}
    boris_tables = {t: 0 for t in qdm.tables}
    boris_data_value_for_rgs_tbls = {t: {} for t in qdm.tables}

    # assign values for the baseline (boris's metric)
    # this is dependent on the relative frequency of each query
    # boris's metric doesn't depend on query values, so this is done just once
    # whereas the other methods will generate one assignment of value to DEs per
    # trial of value generation
    for qry_num in unique:
        # get relevant tables, columns, and row groups
        schema, qry = query_set[qry_num]
        tbls = qdm.get_rel_tbls(schema, qry)

        rel_tbls = [t for t in tbls if len(tbls[t]) > 0]
        rel_cols = []
        for t in tbls:
            rel_cols.extend(tbls[t])

        rg_info = qdm.get_rg_info(schema, qry)
        qry_info_index = 0
        while qry_info_index < len(rg_info):
            if "SET" in rg_info[qry_info_index]['query']: 
                qry_info_index += 1
            else: 
                break

        rga = rg_info[qry_info_index]["data_elements"]
        unique_rga = set([(x['file'], x['row_group']) for x in rga])

        # for boris: value is relative frequency, don't need to multiply by number
        # of time occurred because relative frequency already captures that
        boris_value = relative_query_frequencies[qry_num] 

        # assign query value to each data element. Append to list to enable
        # different aggregation methods post-hoc before writing to a json file
        for t in rel_tbls:
            tname = t
            if schema == "tpcds" and t == "customer":
                tname = "tpcds.customer"
            boris_tables[tname] += boris_value
        for c in rel_cols:
            boris_columns[c] += boris_value

        for val in unique_rga:
            tbl, rg = val
            if schema == "tpcds" and tbl == "customer":
                tbl = "tpcds.customer"
            if rg not in boris_data_value_for_rgs_tbls[tbl]: 
                boris_data_value_for_rgs_tbls[tbl][rg] = 0
            boris_data_value_for_rgs_tbls[tbl][rg] += boris_value

    with open(os.path.join(out_dir, "boris_data_val_tbls.json"), 'w') as fp:
        json.dump(boris_tables, fp, indent=4, sort_keys=True)

    with open(os.path.join(out_dir, "boris_data_val_cols.json"), 'w') as fp:
        json.dump(boris_columns, fp, indent=4, sort_keys=True)

    with open(os.path.join(out_dir, "boris_data_val_rgs_tbls.json"), 'w') as fp:
        json.dump(boris_data_value_for_rgs_tbls, fp, indent=4, sort_keys=True)

def compute_value_metric(qdm, unique, counts, query_set, divide, distro,
                         out_dir=DEFAULT_OUT_DIR):
    # For cardinality-weighted method
    cardinality = qdm.cardinality
    dvt = {}
    dvc = {}
    dvrt = {}
    total_values = {}
    for iter_ in range(qdm.num_trials):
        # initialize data collection for a trial of value assignment
        data_value_for_tables = {t: 0 for t in qdm.tables}
        data_value_for_columns = {l: 0 for l in qdm.columns}
        data_value_for_rg_tbls = {t: {} for t in qdm.tables}

        total_value_for_iter = compute_total_value(unique, counts, query_set, qdm, iter_)
        total_values[str(iter_)] = total_value_for_iter

        for i in range(len(unique)):
            qry_num = unique[i]

            # get relevant tables, columns, and row groups
            schema, qry = query_set[qry_num]
            tbls = qdm.get_rel_tbls(schema, qry)

            rel_tbls = [t for t in tbls if len(tbls[t]) > 0]
            rel_cols = []
            # card_rel_tbls = [cardinality[schema][t] for t in rel_tbls]
            # card_rel_tbls = [x / sum(card_rel_tbls) for x in card_rel_tbls]
            for t in tbls:
                rel_cols.extend(tbls[t])

            rg_info = qdm.get_rg_info(schema, qry)
            qry_info_index = 0
            while qry_info_index < len(rg_info):
                if "SET" in rg_info[qry_info_index]['query']: 
                    qry_info_index += 1
                else: 
                    break

            rga = rg_info[qry_info_index]["data_elements"]
            unique_rga = set([(x['file'], x['row_group']) for x in rga])

            # do value for query across all runs all at once for efficiency
            value = qdm.get_query_value(schema, qry, str(iter_)) * int(counts[i])

            if divide == "equal":
                if len(rel_tbls) == 0 or len(rel_cols) == 0 or len(unique_rga) == 0:
                    print(f"Query {qry}, {schema} no rel tables, columns, or row groups.")
                tval = (value / len(rel_tbls)) if len(rel_tbls) > 0 else 0
                cval = (value / len(rel_cols)) if len(rel_cols) > 0 else 0
                rgval = (value / len(unique_rga)) if len(unique_rga) > 0 else 0
            elif divide == "full": 
                tval = value
                cval = value
                rgval = value
            elif divide == "cardinality":
                card_rel_tbls = {t: cardinality[schema][t] for t in rel_tbls}
                total_cardinality = sum(card_rel_tbls.values())
                card_rel_tbls_norm = {t: (x / total_cardinality) for t, x in card_rel_tbls.items()}
                
                # cardinality only defined for tables, columns
                tval = {tbl: value * norm_card for tbl, norm_card in card_rel_tbls_norm.items()}
                total_val = sum(tval.values())
                assert math.isclose(total_val, value), f"rip query {qry}, {schema}"

                tbls_for_cols = {c: get_table_for_column(c) for c in rel_cols}
                card_rel_cols = {c: cardinality[schema][tbls_for_cols[c]] for c in rel_cols}
                total_cardinality = sum(card_rel_cols.values())
                card_rel_cols_norm = {c: (x / total_cardinality) for c, x in card_rel_cols.items()}

                cval = {col: value * norm_card for col, norm_card in card_rel_cols_norm.items()}
                total_val = sum(cval.values())
                assert math.isclose(total_val, value), f"rip query {qry}, {schema}"
            else:
                raise ValueError("Invalid value for --divide argument")

            for t in rel_tbls:
                tname = t
                if schema == "tpcds" and t == "customer":
                    tname = "tpcds.customer"
                if divide == "cardinality":
                    data_value_for_tables[tname] += tval[t]
                else:
                    data_value_for_tables[tname] += tval
            for c in rel_cols:
                if divide == "cardinality":
                    data_value_for_columns[c] += cval[c]
                else:
                    data_value_for_columns[c] += cval

            if divide != "cardinality":
                for val in unique_rga:
                    tbl, rg = val
                    if schema == "tpcds" and tbl == "customer":
                        tbl = "tpcds.customer"

                    if rg not in data_value_for_rg_tbls[tbl]: 
                        data_value_for_rg_tbls[tbl][rg] = 0
                    data_value_for_rg_tbls[tbl][rg] += rgval
            
        # assign DE value assignment to the trial number
        dvt[str(iter_)] = data_value_for_tables
        dvc[str(iter_)] = data_value_for_columns
        dvrt[str(iter_)] = data_value_for_rg_tbls

    with open(os.path.join(out_dir, f"data_val_tbls_{distro}_{divide}.json"), 'w') as fp:
        json.dump(dvt, fp, indent=4, sort_keys=True)

    with open(os.path.join(out_dir, f"total_vals_{distro}.json"), 'w') as fp:
        json.dump(total_values, fp, indent=4, sort_keys=True)

    with open(os.path.join(out_dir, f"data_val_cols_{distro}_{divide}.json"), 'w') as fp:
        json.dump(dvc, fp, indent=4, sort_keys=True)

    if divide != "cardinality":
        with open(os.path.join(out_dir, f"data_val_rgs_tbls_{distro}_{divide}.json"), 'w') as fp:
            json.dump(dvrt, fp, indent=4, sort_keys=True)

def compute_query_set(inputs):
    query_set = []
    if not inputs.tpcds_only:
        with open(os.path.join(inputs.tpch_logs_dir, "tpch_completed.json")) as fp:
            completed = json.load(fp)
            q = [("tpch", i) for i in completed]
            query_set.extend(q)

    with open(inputs.query_set or
              os.path.join(inputs.tpcds_logs_dir, "tpcds_completed.json")) as fp:
        completed = json.load(fp)
        q = [("tpcds", i) for i in completed]
        query_set.extend(q)
    return query_set

def generate_query_sample(num_samples, num_queries, seed):
    rng = np.random.default_rng(seed)
    sampled_queries = rng.integers(num_queries, size=num_samples)
    unique, counts = np.unique(sampled_queries, return_counts=True)
    assert len(unique) == len(counts)

    relative_query_frequencies = {}
    for i in range(len(unique)):
        freq = counts[i] / num_samples
        relative_query_frequencies[unique[i]] = freq
    return unique, counts, relative_query_frequencies

def compute_total_value(unique, counts, query_set, qdm, iter_): 
    total_value = 0
    for i in range(len(unique)):
        qry_num = unique[i]
        schema, qry = query_set[qry_num]
        value = qdm.get_query_value(schema, qry, str(iter_)) * int(counts[i])
        total_value += value
    return total_value

# class to abstract away accessing information about queries
class QueryDataManager:
    def __init__(self, num_trials, distro, inputs=None):
        inputs = inputs or Inputs()
        self.inputs = inputs

        # can also derive this from the number of columns (minus one) in df1.shape 
        self.num_trials = num_trials 

        # values for queries
        df2 = pd.read_csv(os.path.join(inputs.values_dir, f"tpcds_query_values_{distro}.csv"))
        self.values = {"tpcds": df2.set_index("query_id").to_dict("index")}

        # get relevant columns/tables for query
        self.qdict = {"tpcds": json.load(open(inputs.columns_in_queries))}

        # For cardinality-weighted method
        self.cardinality = {"tpcds": json.load(open(inputs.cardinality))}

        # have list of all tables, columns in DB
        tpcds_columns = [x.strip() for x in
                         open("../../tpcds_schema/tpcds_column_names.csv").readlines()]
        self.columns = tpcds_columns
        self.tables = list(tpcds_tables)

        if not inputs.tpcds_only:
            df1 = pd.read_csv(os.path.join(inputs.values_dir, f"tpch_query_values_{distro}.csv"))
            self.values["tpch"] = df1.set_index("query_id").to_dict("index")
            self.qdict["tpch"] = json.load(open("../data/tpch_columns_in_queries.json"))
            self.cardinality["tpch"] = json.load(open("./tpch_cardinality.json"))
            tpch_columns = [x.strip() for x in open("../data/column_names.csv").readlines()]
            self.columns = tpch_columns + tpcds_columns
            tpch_tables = [x.strip() for x in open("../data/table_names.csv").readlines()]
            self.tables = tpch_tables + tpcds_tables

    def get_rel_tbls(self, schema, qry):
        # get relevant tables for a query within a schema
        return self.qdict[schema][str(qry)]

    def get_rg_info(self, schema, qry):
        # get row-group info for a query 
        if schema == "tpch":
            logs_dir = self.inputs.tpch_logs_dir
        elif schema == "tpcds":
            logs_dir = self.inputs.tpcds_logs_dir
        rg_info = json.load(open(os.path.join(logs_dir, f"{schema}_{qry}", "access.json")))
        return rg_info

    def get_query_value(self, schema, qry, iter_):
        return self.values[schema][f"query_{qry}"][iter_]

if __name__ == "__main__":
    parser = ArgumentParser(description="Run time-series oracle")
    parser.add_argument("-n", "--num-samples", type=int, default=1500, 
                        help="Number of queries that run")
    parser.add_argument("--num-trials", type=int, default=100, 
                        help="Number of different value generation trials that were run")
    parser.add_argument("-s", "--seed", type=int, default=42, help="Random seed")
    parser.add_argument("-o", "--out-dir", default=DEFAULT_OUT_DIR,
                        help="Directory to write results into. Defaults to the "
                             "shared ../data so existing pipelines are unchanged; "
                             "point a sweep at ../data/sweep/N<n>_s<seed> so runs "
                             "do not overwrite each other.")
    parser.add_argument("--distro", choices=["normal", "zipf", "both"], default="both",
                        help="Task-value distribution to compute. Sec 4.4 reports zipf "
                             "only, so a sweep can halve its runtime with --distro zipf.")
    parser.add_argument("--logs-dir", default=None,
                        help="TPC-DS row-group logs (tpcds_<N>/access.json + "
                             "tpcds_completed.json). Default: ../tpcds_drill_logs")
    parser.add_argument("--values-dir", default="../data",
                        help="Directory holding tpcds_query_values_<distro>.csv")
    parser.add_argument("--columns-in-queries", default="../data/tpcds_columns_in_queries.json",
                        help="Columns each TPC-DS query references, for the query set in use")
    parser.add_argument("--cardinality", default="./tpcds_cardinality.json",
                        help="TPC-DS table cardinalities for the scale factor in use")
    parser.add_argument("--tpcds-only", action="store_true",
                        help="Leave TPC-H out of the query set (R2D7 Spark capture)")
    parser.add_argument("--query-set", default=None,
                        help="JSON list of TPC-DS query numbers to use instead of "
                             "<logs-dir>/tpcds_completed.json")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    inputs = Inputs(logs_dir=args.logs_dir, values_dir=args.values_dir,
                    columns_in_queries=args.columns_in_queries,
                    cardinality=args.cardinality, tpcds_only=args.tpcds_only,
                    query_set=args.query_set)

    query_set = compute_query_set(inputs)
    num_queries = len(query_set)
    print(f"Number of queries in the set: {num_queries}")


    start = time.time()
    unique, counts, relative_query_frequencies = generate_query_sample(args.num_samples, 
                                                                       num_queries, args.seed)
    print(f"History N={args.num_samples} seed={args.seed}: "
          f"{len(unique)}/{num_queries} distinct queries drawn")

    distros = ["normal", "zipf"] if args.distro == "both" else [args.distro]

    # the frequency baseline does not depend on task values, so it is computed
    # once per history regardless of which distributions are requested
    qdm = QueryDataManager(args.num_trials, distros[0], inputs)
    compute_boris_metric(qdm, unique, relative_query_frequencies, query_set,
                         out_dir=args.out_dir)

    for distro in distros:
        qdm = QueryDataManager(args.num_trials, distro, inputs)
        for divide in ["equal", "full", "cardinality"]:
            compute_value_metric(qdm, unique, counts, query_set, divide, distro,
                                 out_dir=args.out_dir)

    write_manifest(args.out_dir, args, distros, query_set, unique, counts, inputs)
    print(f"Wrote results for N={args.num_samples} seed={args.seed} to {args.out_dir} "
          f"in {time.time() - start:.1f}s")
