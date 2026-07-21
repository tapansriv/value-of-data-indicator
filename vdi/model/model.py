import numpy as np
import pandas as pd
import json
from typing import List, Dict, Tuple
from statsmodels.regression.mixed_linear_model import MixedLM

supported_granularities = ["column", "table", "row group"]
de_list_files = {
                    "column": "column_names.csv",
                    "table": "table_names.csv",
                }
COL_TBL_QRY = "columns_in_queries.json"
METADATA_PATH = "metadata/"
QRY_VALS = "query_values.csv"

# def ground_truth() -> Dict[str, Tuple[int, int]]:
def ground_truth() -> pd.DataFrame:
    return pd.read_csv(METADATA_PATH + QRY_VALS)


def estimate_value_for_granularity(granularity: str, task_ids: List[str],
                                   agents: List[int] = None, num_agents: int = 10):
    assert granularity in supported_granularities

    # paths
    with open(METADATA_PATH + de_list_files[granularity]) as fp:
        de_names = [name.strip() for name in fp.readlines()]

    # Set random seed for reproducibility

    # Parameters
    num_tasks = len(task_ids)
    num_data_elements = len(de_names)

    # Assign agents to tasks
    if agents is None:
        agents = np.random.choice(range(num_agents), size=num_tasks)

    # Generate task-data usage matrix (sparse)
    task_data_usage = []
    num_des_per_task = {}
    with open(METADATA_PATH + COL_TBL_QRY) as fp:
        qry_de_dict = json.load(fp)

        for t in range(len(task_ids)):
            task = task_ids[t]
            assert task in qry_de_dict
            num_des = 0
            for tbl in qry_de_dict[task]:
                if len(qry_de_dict[task][tbl]) == 0:
                    continue

                # asserted its one of these values already
                if granularity == "table":
                    task_data_usage.append((t, tbl))
                    num_des += 1

                elif granularity == "column":
                    for col in qry_de_dict[task][tbl]:
                        task_data_usage.append((t, col))
                        num_des += 1

                elif granularity == "row group":
                    raise NotImplementedError()
            num_des_per_task[task] = num_des

    # Fetch ground truth task utilities
    ground_truth = pd.read_csv(METADATA_PATH + QRY_VALS) 
    utilities = []
    for task in task_ids:
        task_vals = ground_truth[ground_truth["query_id"] == f"query_{task}"]
        utility = task_vals["data_value"] + task_vals["agent_value"]
        utilities.append(float(utility.iloc[0]))

    # Build dataframe for mixed model
    rows = []
    for (t, d) in task_data_usage:
        task = task_ids[t]
        rows.append({
            "task": task,
            "data_element": d,
            "task_data_key": f"{task}_{d}",
            "agent": agents[t],
            "utility": utilities[t]
        })

    df = pd.DataFrame(rows)

    # Create dummy variables for (task, data) contributions
    X = pd.get_dummies(df["task_data_key"])

    # Add agent group
    df["agent"] = df["agent"].astype("category")

    # Fit mixed model
    model = MixedLM(endog=df["utility"], exog=X, groups=df["agent"])
    result = model.fit(reml=True)

    # Get per-(task, data) contributions
    task_data_contributions = result.fe_params

    # Aggregate total value per data element
    df["contribution"] = df["task_data_key"].map(task_data_contributions)
    data_values = df.groupby("data_element")["contribution"].sum().sort_values(ascending=False)

    print("Estimated data element values (summed across tasks):")
    print(data_values)

if __name__ == '__main__':
    np.random.seed(42)
    num_tasks = 500
    task_ids = [str(t) for t in np.random.randint(1, 23, size=num_tasks)]
    agents = [i for i in range(len(task_ids))]


    lines = [x.strip() for x in open(METADATA_PATH + "column_names.csv").readlines()]
    data_value_for_columns = {l: 0 for l in lines}

    lines = [x.strip() for x in open(METADATA_PATH + "table_names.csv").readlines()]
    data_value_for_tables = {l: 0 for l in lines}

    f = open("metadata/columns_in_queries.json")
    qdict = json.load(f)
    ground_truth = pd.read_csv(METADATA_PATH + QRY_VALS) 
    for qry_str in task_ids:
        qry_num = int(qry_str)
        tbls = qdict[str(qry_num)]
        rel_tbls = [t for t in tbls if len(tbls[t]) > 0]
        rel_cols = []
        for t in tbls:
            rel_cols.extend(tbls[t])

        value = ground_truth["data_value"][qry_num-1]
        tval = value / len(rel_tbls)
        cval = value / len(rel_cols)

        for t in rel_tbls:
            data_value_for_tables[t] += tval
        
        for c in rel_cols:
            data_value_for_columns[c] += cval

    estimate_value_for_granularity("table", task_ids)

    sorted_by_value_desc = dict(sorted(data_value_for_tables.items(), 
                                       key=lambda item: item[1], reverse=True))
    for k in sorted_by_value_desc:
        print(f"{k}: {sorted_by_value_desc[k]}")











