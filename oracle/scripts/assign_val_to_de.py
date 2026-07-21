import json 
import math
import time
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

def compute_boris_metric(qdm, unique, relative_query_frequencies, query_set):
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

    with open("../data/boris_data_val_tbls.json", 'w') as fp:
        json.dump(boris_tables, fp, indent=4, sort_keys=True)

    with open("../data/boris_data_val_cols.json", 'w') as fp:
        json.dump(boris_columns, fp, indent=4, sort_keys=True)

    with open("../data/boris_data_val_rgs_tbls.json", 'w') as fp:
        json.dump(boris_data_value_for_rgs_tbls, fp, indent=4, sort_keys=True)

def compute_value_metric(qdm, unique, counts, query_set, divide, distro):
    # For cardinality-weighted method
    cardinality = {"tpcds": json.load(open("./tpcds_cardinality.json")), 
                   "tpch": json.load(open("./tpch_cardinality.json"))}
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

    with open(f"../data/data_val_tbls_{distro}_{divide}.json", 'w') as fp:
        json.dump(dvt, fp, indent=4, sort_keys=True)

    with open(f"../data/total_vals_{distro}.json", 'w') as fp:
        json.dump(total_values, fp, indent=4, sort_keys=True)

    with open(f"../data/data_val_cols_{distro}_{divide}.json", 'w') as fp:
        json.dump(dvc, fp, indent=4, sort_keys=True)

    if divide != "cardinality":
        with open(f"../data/data_val_rgs_tbls_{distro}_{divide}.json", 'w') as fp:
            json.dump(dvrt, fp, indent=4, sort_keys=True)

def compute_query_set():
    query_set = []
    with open("../drill_logs/tpch_completed.json") as fp:
        completed = json.load(fp)
        q = [("tpch", i) for i in completed]
        query_set.extend(q)

    with open("../tpcds_drill_logs/tpcds_completed.json") as fp:
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
    def __init__(self, num_trials, distro):
        df1 = pd.read_csv(f"../data/tpch_query_values_{distro}.csv")
        df2 = pd.read_csv(f"../data/tpcds_query_values_{distro}.csv")

        # can also derive this from the number of columns (minus one) in df1.shape 
        self.num_trials = num_trials 

        # values for queries
        df1p = df1.set_index("query_id").to_dict("index")
        df2p = df2.set_index("query_id").to_dict("index")
        self.values = {"tpch": df1p, "tpcds": df2p}

        # get relevant columns/tables for query
        f = open("../data/tpch_columns_in_queries.json")
        qdict1 = json.load(f)
        f = open("../data/tpcds_columns_in_queries.json")
        qdict2 = json.load(f)
        self.qdict = {"tpch": qdict1, "tpcds": qdict2}

        # have list of all tables, columns in DB
        tpch_columns = [x.strip() for x in open("../data/column_names.csv").readlines()]
        tpcds_columns = [x.strip() for x in
                         open("../../tpcds_schema/tpcds_column_names.csv").readlines()]
        self.columns = tpch_columns + tpcds_columns

        tpch_tables = [x.strip() for x in open("../data/table_names.csv").readlines()]
        self.tables = tpch_tables + tpcds_tables

    def get_rel_tbls(self, schema, qry):
        # get relevant tables for a query within a schema
        return self.qdict[schema][str(qry)]

    def get_rg_info(self, schema, qry):
        # get row-group info for a query 
        if schema == "tpch":
            rg_info = json.load(open(f"../drill_logs/{schema}_{qry}/access.json"))
        elif schema == "tpcds":
            rg_info = json.load(open(f"../tpcds_drill_logs/{schema}_{qry}/access.json"))
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
    args = parser.parse_args()


    query_set = compute_query_set()
    num_queries = len(query_set)
    print(f"Number of queries in the set: {num_queries}")


    start = time.time()
    unique, counts, relative_query_frequencies = generate_query_sample(args.num_samples, 
                                                                       num_queries, args.seed)
    NORMAL_DISTRO = "normal"
    qdm = QueryDataManager(args.num_trials, NORMAL_DISTRO)
    compute_boris_metric(qdm, unique, relative_query_frequencies, query_set)
    compute_value_metric(qdm, unique, counts, query_set, "equal", NORMAL_DISTRO)
    compute_value_metric(qdm, unique, counts, query_set, "full", NORMAL_DISTRO)
    compute_value_metric(qdm, unique, counts, query_set, "cardinality", NORMAL_DISTRO)

    ZIPF_DISTRO = "zipf"
    qdm = QueryDataManager(args.num_trials, ZIPF_DISTRO)
    compute_value_metric(qdm, unique, counts, query_set, "equal", ZIPF_DISTRO)
    compute_value_metric(qdm, unique, counts, query_set, "full", ZIPF_DISTRO)
    compute_value_metric(qdm, unique, counts, query_set, "cardinality", ZIPF_DISTRO)

