import argparse
import os
import numpy as np
import pandas as pd
from argparse import ArgumentParser
from typing import List
import matplotlib.pyplot as plt

list_num_des_per_task = [14, 9, 10, 55, 35, 17, 19, 14, 4, 23, 37, 11, 21, 37,
                         11, 17, 26, 27, 20, 11, 11, 12, 25, 27, 30, 19, 18, 4,
                         29, 26, 35, 7, 20, 19, 20, 12, 11, 12, 20, 15, 8, 10,
                         10, 12, 14, 24, 34, 16, 45, 24, 15, 10, 13, 24, 10, 20,
                         30, 17, 12, 20, 21, 13, 13, 88, 18, 28, 17, 25, 20, 10,
                         23, 31, 19, 30, 49, 17, 32, 29, 20, 45, 28, 11, 17, 15,
                         29, 8, 12, 11, 14, 9, 22, 7, 11, 17, 18, 10, 12, 11,
                         13]

class DataElement:
    def __init__(self, de_id: str): 
        self.de_id = de_id
        self.cleaned = False
        self.value = 0
        self.access_count = 0
    def reset(self):
        self.cleaned = False

class UtilityFunction:
    def __init__(self, sensitivity: str):
        assert sensitivity in ["high", "medium", "low"], f"Invalid sensitivity: {sensitivity}"
        self.sensitivity = sensitivity

    def compute_utility(self, data_elements: List[DataElement]) -> float:
        cleaned_count = sum(1 for de in data_elements if de.cleaned)
        cleaned_percent = cleaned_count / len(data_elements)
        min_utility = 0.2
        threshold = 0
        if self.sensitivity == "high":
            threshold = 1.0
        elif self.sensitivity == "medium":
            threshold = 0.5
        else:  # low sensitivity
            threshold = 0.25

        slope = (1.0 - min_utility) / threshold 
        if cleaned_percent >= threshold:
            return 1.0
        else:
            return min_utility + slope * cleaned_percent

class Task:
    def __init__(self, task_id: str, required_des: List[DataElement],
                 utility_func: UtilityFunction):
        self.task_id = task_id
        self.required_des = required_des
        self.utility_func = utility_func
        self.value = 0
    def reset(self):
        for de in self.required_des:
            de.reset()
        # self.value = 0

def generate_values(task_keys: List[str], distribution: str, num_tasks: int, num_trials: int):
    # draw samples from underlying supported distributions
    samples = []
    if distribution == "normal":
        samples = np.random.normal(50, 15, size=(num_tasks, num_trials))
    elif distribution == "zipf":
        # using parameter of 2.0
        samples = np.random.zipf(2.0, size=(num_tasks, num_trials))
    df = pd.DataFrame(samples)
    df["query_id"] = task_keys
    df.to_csv(f"task_values_{distribution}.csv", index=False)

def value_of_data_cleaning(data_elements: List[DataElement], num_des_to_clean: int): 
    assert sum([de.cleaned for de in data_elements]) == 0, f"Expected {num_des_to_clean} cleaned DEs, got {sum([de.cleaned for de in data_elements])}"
    de_values = []
    for de in data_elements:
        de_values.append((de, de.value))
    sorted_de_values = sorted(de_values, key=lambda x: x[1], reverse=True)
    des_to_clean = sorted_de_values[:num_des_to_clean]
    for de, val in des_to_clean:
        de.cleaned = True
    assert sum([de.cleaned for de in data_elements]) == num_des_to_clean, f"Expected {num_des_to_clean} cleaned DEs, got {sum([de.cleaned for de in data_elements])}"

def random_cleaning(data_elements: List[DataElement], num_des_to_clean: int):
    assert sum([de.cleaned for de in data_elements]) == 0, f"Expected {num_des_to_clean} cleaned DEs, got {sum([de.cleaned for de in data_elements])}"
    des_to_clean = np.random.choice(data_elements, size=num_des_to_clean, replace=False)
    for de in des_to_clean:
        de.cleaned = True
    assert sum([de.cleaned for de in data_elements]) == num_des_to_clean, f"Expected {num_des_to_clean} cleaned DEs, got {sum([de.cleaned for de in data_elements])}"

def task_value_cleaning(data_elements: List[DataElement], tasks: List[Task], num_des_to_clean: int):
    assert sum([de.cleaned for de in data_elements]) == 0, f"Expected {num_des_to_clean} cleaned DEs, got {sum([de.cleaned for de in data_elements])}"
    num_cleaned = 0

    # find the task with highest value
    tasks_sorted = sorted(tasks, key=lambda x: x.value, reverse=True)
    for task in tasks_sorted:
        for de in task.required_des:
            if not de.cleaned:
                de.cleaned = True
                num_cleaned += 1
            if num_cleaned >= num_des_to_clean:
                assert sum([de.cleaned for de in data_elements]) == num_des_to_clean, f"Expected {num_des_to_clean} cleaned DEs, got {sum([de.cleaned for de in data_elements])}"
                return
    assert sum([de.cleaned for de in data_elements]) == num_des_to_clean, f"Expected {num_des_to_clean} cleaned DEs, got {sum([de.cleaned for de in data_elements])}"

def frequently_accessed_cleaning(data_elements: List[DataElement], num_des_to_clean: int):
    assert sum([de.cleaned for de in data_elements]) == 0, f"Expected {num_des_to_clean} cleaned DEs, got {sum([de.cleaned for de in data_elements])}"
    de_access_counts = []
    for de in data_elements:
        de_access_counts.append((de, de.access_count))
    sorted_de_access = sorted(de_access_counts, key=lambda x: x[1], reverse=True)
    des_to_clean = sorted_de_access[:num_des_to_clean]
    for de, count in des_to_clean:
        de.cleaned = True
    assert sum([de.cleaned for de in data_elements]) == num_des_to_clean, f"Expected {num_des_to_clean} cleaned DEs, got {sum([de.cleaned for de in data_elements])}"


def compute_value_utility(task_list: List[Task]) -> float:
    total_utility = 0
    avg_util = 0
    for task in task_list:
        utility = task.utility_func.compute_utility(task.required_des)
        total_utility += utility * task.value
        avg_util += utility
    avg_util = avg_util / len(task_list)
    # print(f"Average Utility across tasks: {avg_util}")
    return total_utility, avg_util

def run_trial(task_list, task_values, data_elements, num_des_to_clean, trial): 
    # given list of tasks, data elements, run the experiment for one set of task
    # values
    trial_values = task_values[str(trial)].to_list()
    for i, task in enumerate(task_list):
        task.value = trial_values[i]

    NUM_SEED_QUERY_ITERS = 10
    for task in task_list:
        val_to_add = NUM_SEED_QUERY_ITERS * task.value / len(task.required_des)
        for de in task.required_des:
            de.value += val_to_add
            de.access_count += NUM_SEED_QUERY_ITERS

    # Implement cleaning strategies
    # 1. Value of Data Cleaning
    value_of_data_cleaning(data_elements, num_des_to_clean)
    vod_util, vod_avg_util = compute_value_utility(task_list)
    for task in task_list:
        task.reset()
    for de in data_elements:
        de.reset()


    # 2. Random Cleaning
    random_cleaning(data_elements, num_des_to_clean)
    rand_util, rand_avg_util = compute_value_utility(task_list)
    for task in task_list:
        task.reset()
    for de in data_elements:
        de.reset()

    # 3. Task Value Cleaning
    task_value_cleaning(data_elements, task_list, num_des_to_clean)
    task_util, task_avg_util = compute_value_utility(task_list)
    for task in task_list:
        task.reset()
    for de in data_elements:
        de.reset()
    # 4. Frequently Accessed Cleaning
    frequently_accessed_cleaning(data_elements, num_des_to_clean)
    freq_util, freq_avg_util = compute_value_utility(task_list)

    # print(f"Trial {trial}: VoDC Utility: {vod_util}, Random Utility: {rand_util}, Task Value Utility: {task_util}, Frequently Accessed Utility: {freq_util}")

    result = [trial, vod_util, rand_util, task_util, freq_util,
              vod_avg_util, rand_avg_util, task_avg_util, freq_avg_util]

    result = {
              "trial": trial,
              "vod_utility": vod_util,
              "random_utility": rand_util,
              "task_value_utility": task_util,
              "frequently_accessed_utility": freq_util,
              "vod_avg_utility": vod_avg_util,
              "random_avg_utility": rand_avg_util,
              "task_value_avg_utility": task_avg_util,
              "frequently_accessed_avg_utility": freq_avg_util
             }  
    df = pd.DataFrame([result])
    for task in task_list:
        task.reset()
    for de in data_elements:
        de.reset()
        de.value = 0
    return df

def run_experiment(task_keys, task_values, num_data_elements, num_trials, num_des_to_clean):
    # define the mapping from tasks to DEs, ids
    de_keys = ["de_{}".format(i) for i in range(num_data_elements)]
    de_list = []
    for de_id in de_keys:
        de = DataElement(de_id)
        de_list.append(de)

    sensitivities = ["high", "medium", "low"]
    task_list = []
    for task_id in task_keys: 
        # number of DEs accessed should be not constant across all tasks, 
        # we model this on the number of columns accessed per query in TPCDS
        num_rel_des = np.random.choice(list_num_des_per_task)
        rel_des = np.random.choice(de_list, size=num_rel_des, replace=False)

        sens = np.random.choice(sensitivities)
        utility_func = UtilityFunction(sens)
        t = Task(task_id, rel_des, utility_func)
        task_list.append(t)

    # run_trial(task_list, task_values, de_list, num_des_to_clean, 0)
    accumulated_df = pd.DataFrame()
    for trial in range(num_trials):
        df = run_trial(task_list, task_values, de_list, num_des_to_clean, trial)
        accumulated_df = pd.concat([accumulated_df, df], ignore_index=True)
    # print("------------------------------")
    # print(accumulated_df)
    return accumulated_df

def agg_data(dfs, budgets, num_trials, xlabels, distro):
    randoms = {t: [] for t in range(num_trials)}
    tasks   = {t: [] for t in range(num_trials)}
    freqs   = {t: [] for t in range(num_trials)}
    values  = {t: [] for t in range(num_trials)}

    d_randoms = {t: [] for t in range(num_trials)}
    d_tasks   = {t: [] for t in range(num_trials)}
    d_freqs   = {t: [] for t in range(num_trials)}
    for df in dfs:
        vod = df["vod_utility"]

        # percent differences
        diff_random = 100 * (vod - df["random_utility"]) / df["random_utility"]
        diff_task   = 100 * (vod - df["task_value_utility"]) / df["task_value_utility"]
        diff_freq   = 100 * (vod - df["frequently_accessed_utility"]) / df["frequently_accessed_utility"]

        for t in range(num_trials):
            randoms[t].append(df["random_utility"][t])
            tasks[t].append(df["task_value_utility"][t])
            freqs[t].append(df["frequently_accessed_utility"][t])
            values[t].append(df["vod_utility"][t])

            d_randoms[t].append(diff_random[t])
            d_tasks[t].append(diff_task[t])
            d_freqs[t].append(diff_freq[t])
    return d_randoms, d_tasks, d_freqs

def plot_custom(randoms, tasks, freqs, num_trials, budgets, xlabels):
    red = "#E65742"
    orange = "#FE9C22"
    yellow = "#F8DD3D"
    green = "#ADDC5A"
    blue = "#1F63A9"
    
    num_budgets = len(budgets)

    for t in range(num_trials):
        if t != 4:
            font = {'size': 19}
            plt.rc('font', **font)
        else: 
            font = {'size': 14}
            plt.rc('font', **font)

        N = len(xlabels)
        x = np.arange(N)
        width = 0.25

        fig, ax = plt.subplots(figsize=(7, 4))
        
        random_means = []
        random_errors = []
        freqs_means = []
        freqs_errors = []
        for i in range(num_budgets):
            m = np.mean(randoms[t][i])
            e = np.std(randoms[t][i])
            random_means.append(m)
            random_errors.append(e)
            print(f"Trial {t}, Budget {budgets[i]}%: Random Mean: {m}, Random Std: {e}")

            m = np.mean(freqs[t][i])
            e = np.std(freqs[t][i])
            freqs_means.append(m)
            freqs_errors.append(e)
            print(f"Trial {t}, Budget {budgets[i]}%: Frequent Mean: {m}, Frequent Std: {e}")

            m = np.mean(tasks[t][i])
            e = np.std(tasks[t][i])
            print(f"Trial {t}, Budget {budgets[i]}%: Task Mean: {m}, Task Std: {e}")

        ax.bar(x - width/2, freqs_means, width, yerr=freqs_errors, capsize=4, label="VOD vs Frequent", color=red)
        ax.bar(x + width/2, random_means,  width, yerr=random_errors, capsize=4, label="VOD vs Random", color=blue)

        ax.set_xticks(x)
        ax.set_xticklabels(xlabels)
        ax.set_xlabel("% of Data Prepared")
        ax.set_ylabel("% Value Change")
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        # ax.set_title("VOD utility improvement over baselines")
        ax.axhline(0, lw=1, color='black')
        ax.set_ylim([-4, 315])

        if t == 0 or t == 4:
            ax.legend()
        fig.tight_layout()
        plt.savefig(f"cleaning_budget_custom_{t}.pdf",
                    bbox_inches='tight')

def plot_grouped_percent_diff(dfs, xlabels, distro):
    """
    dfs: list of pandas DataFrames, each with columns
         ['vod_utility','random_utility','task_value_utility']
    xlabels: list of x-axis labels, same length as dfs
    """
    red = "#E65742"
    orange = "#FE9C22"
    yellow = "#F8DD3D"
    green = "#ADDC5A"
    blue = "#1F63A9"

    means = []
    errors = []

    for df in dfs:
        vod = df["vod_utility"]

        # percent differences
        diff_random = 100 * (vod - df["random_utility"]) / df["random_utility"]
        diff_task   = 100 * (vod - df["task_value_utility"]) / df["task_value_utility"]
        diff_freq  = 100 * (vod - df["frequently_accessed_utility"]) / df["frequently_accessed_utility"]

        # aggregate
        means.append([diff_random.mean(), diff_task.mean(), diff_freq.mean()])
        errors.append([diff_random.std(),  diff_task.std(), diff_freq.std()])

    means = np.array(means)         # shape (N, 3)
    errors = np.array(errors)
    print(means)
    # plotting
    N = len(dfs)
    x = np.arange(N)
    width = 0.25

    # fig, ax = plt.subplots(figsize=(9, 5))
    fig, ax = plt.subplots(figsize=(7, 4))

    ax.bar(x - width,     means[:, 0], width, yerr=errors[:, 0], capsize=4, label="VOD vs Random", color=blue)
    ax.bar(x,             means[:, 1], width, yerr=errors[:, 1], capsize=4,
           label="VOD vs Task Value", color=orange)
    ax.bar(x + width,     means[:, 2], width, yerr=errors[:, 2], capsize=4,
           label="VOD vs Frequent", color=red)


    ax.set_xticks(x)
    ax.set_xticklabels(xlabels)
    ax.set_ylabel("% Difference vs VOD")
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    # ax.set_title("VOD utility improvement over baselines")
    ax.axhline(0, lw=1)
    ax.legend()
    fig.tight_layout()
    # plt.show()
    plt.savefig(f"cleaning_budget_experiment_{distro}.pdf")

def main():
    """ TPCDS has 99 queries and 423 columns """
    parser = argparse.ArgumentParser(description="Compute metrics based on cleaning budget parameters.")
    parser.add_argument("--num-tasks", type=int, default=99, help="Number of Tasks.")
    parser.add_argument("--num-data-elements", type=int, default=425, help="Number of Data Elements.")
    parser.add_argument("--percent-scanned", type=float, default=5,
                        help="Percent of data elements that a task scans (e.g., 25 for 25%).")
    parser.add_argument("--distro", type=str, default="custom", choices=["custom", "normal", "zipf"], help="Distribution choice.")
    parser.add_argument("--num-trials", type=int, default=5, help="Number of trials.")
    # parser.add_argument("--cleaning-budget", type=float, default=5, help="Cleaning budget.")
    args = parser.parse_args()

    num_trials = args.num_trials

    # infer the current query set
    task_keys = ["task_{}".format(i) for i in range(args.num_tasks)]
    task_values = pd.read_csv(f"task_values_{args.distro}.csv")

    budgets = [5, 25, 50, 75, 95]
    des_to_clean_list = [int((budget * args.num_data_elements) / 100) for budget in budgets]

    randoms = {t: [[] for _ in budgets] for t in range(num_trials)}
    tasks   = {t: [[] for _ in budgets] for t in range(num_trials)}
    freqs   = {t: [[] for _ in budgets] for t in range(num_trials)}
    for i in range(100):
        dfs = []
        for num_des_to_clean in des_to_clean_list:
            df = run_experiment(task_keys, task_values, args.num_data_elements,
                           args.num_trials, num_des_to_clean)
            dfs.append(df)
        xlabels = [f"{budget}%" for budget in budgets]
        d_randoms, d_tasks, d_freqs = agg_data(dfs, budgets, args.num_trials, xlabels, args.distro)
        for t in range(num_trials):
            for i in range(len(budgets)):
                randoms[t][i].append(d_randoms[t][i])
                tasks[t][i].append(d_tasks[t][i])
                freqs[t][i].append(d_freqs[t][i])
    plot_custom(randoms, tasks, freqs, num_trials, budgets, xlabels)


    # plot_grouped_percent_diff(dfs, xlabels, args.distro)


    
    # create task objects, DE objects, mapping between 
    # Use task values to infer data values (run 10 times say, use dirty values
    # to calculates utility, then average over trials)
    
    # Question: how do I seed data values? I want this to be dependent on the
    # tasks in question, but then do i assume dirtiness? Do i just assign value
    # based on the task themselves? Arguing then that there's data value, and
    # then there's "utility weighted value" which is the metric of primary
    # concern. Isn't that a bit messy? Talk to Raul about this. 



if __name__ == "__main__":
    main()




