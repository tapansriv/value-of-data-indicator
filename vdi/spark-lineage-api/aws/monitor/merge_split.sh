#!/bin/bash
# usage: merge_split.sh <out-run-id> <run-id-rep1> <run-id-rep2>  -- combine a size split across two
# clusters into one dir (rep1 from the first, rep2 from the second) for overhead_summary/validate.
set -eu
cd "$(dirname "$0")/../../benchmarking/data/ec2"
out=$1 a=$2 b=$3
rm -rf "$out"; mkdir -p "$out/usage_logs"
cp -R "$a/rep1" "$out/rep1"; cp -R "$b/rep2" "$out/rep2"
[ -d "$a/usage_logs/rep1" ] && cp -R "$a/usage_logs/rep1" "$out/usage_logs/rep1"
[ -d "$b/usage_logs/rep2" ] && cp -R "$b/usage_logs/rep2" "$out/usage_logs/rep2"
echo "merged from $a (rep1) and $b (rep2)" > "$out/MERGED_FROM.txt"
echo "merged into data/ec2/$out"
