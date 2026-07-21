To rerun the benchmarking experiment:

Ensure Spark is installed (Spark 3.5.5 with Scala 2.13). You can use the following:

```bash
curl -L https://downloads.apache.org/spark/spark-3.5.5/spark-3.5.5-bin-hadoop3-scala2.13.tgz | tar -xz
mv spark-3.5.5-bin-hadoop3-scala2.13 spark
export SPARK_HOME=~/spark
export PATH=$SPARK_HOME/bin:$PATH
```

Ensure Java 17 is installed

Regenerate the jars for the various listener variations by adding the relevant .scala file from the listener_versions folder to target/scala-2.13/

The main experiment script is run_listeners_r1to9.sh (it currently runs the experiment 9 times). It does not include the vanilla (baseline Spark with no listener) experiment. To run the baseline vanilla code, use the run_vanilla.sh script.

The results are output to the following files:

listener_register_results_r1to9.csv
listener_bare_results_r1to9.csv
listener_nowrite_results_r1to9.csv
listener_full_results_r1to9.csv
vanilla_results_r1to9.csv (if you ran the vanilla experiment)

Each CSV has the schema: query, dataset, run_number, <variant_time_column>

Merge all the output CSVs on (query, dataset, run_number)

Use the code in benchmarking_final.ipynb to group the data, compute overheads, and create the visualizations.



