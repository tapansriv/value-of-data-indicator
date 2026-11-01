# Run monitoring helpers (R2D16)

Used from the laptop while EC2 runs are live. All read-only except `finish_run.sh`, which tears
the cluster down after fetching and validating. Each AWS call goes through `aws-vault exec vdi`.
State (lines/alerts already reported) lives in `~/.config/vdi-spark/state/`, so re-arming a
watcher after a restart does not repeat old events.

| Script | Does |
|---|---|
| `watch_all.sh <cluster>:<run-id> ...` | every 5 min, print new variant ends / FAILED / ABORT / MATRIX lines from each run's `matrix.log` |
| `watch_health.sh <cluster>:<run-id> ...` | every 20 min, run `45_status.sh`; print WARN/ALERT changes, and a progress line every ~2 h |
| `watch_run.sh <cluster> <run-id> [skip]` | single-run variant of `watch_all.sh` (with driver-log error lines) |
| `finish_run.sh <cluster> <run-id>` | fetch results + usage logs, summarize event logs on the driver, `validate_run.py`, then `99_teardown.sh` (only if MATRIX_DONE was fetched) |
| `merge_split.sh <out> <run-rep1> <run-rep2>` | combine a size split across two clusters (rep 1 / rep 2) into one `data/ec2/<out>` for `overhead_summary.py` |

Example (the N=1 runs):

    aws/monitor/watch_all.sh    n1c:n1-v3b-r1 n1d:n1-v3b-r2
    aws/monitor/watch_health.sh n1c:n1-v3b-r1 n1d:n1-v3b-r2
    aws/monitor/finish_run.sh   n1c n1-v3b-r1      # when MATRIX COMPLETE
    aws/monitor/finish_run.sh   n1d n1-v3b-r2
    aws/monitor/merge_split.sh  n1-v3 n1-v3b-r1 n1-v3b-r2
