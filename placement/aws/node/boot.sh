#!/bin/bash
# Runs once on every placement node as root, as EC2 user-data. 20_launch.sh prepends:
#   VDI_PLACE_RUN VDI_MAX_MIN
# Carries no secret (only the run name and the lifetime). Each node is standalone: Spark
# runs in local mode, started later by 30_run.sh through node/run_node.sh.
set -euo pipefail
exec >/var/log/vdi-boot.log 2>&1
set -x

# Dead-man's switch: the instance is launched with shutdown behaviour = terminate, so this
# bounds its lifetime even if every laptop-side teardown fails. 25_extend.sh resets it.
systemd-run --unit="vdi-deadman-$(date +%s)" --on-active="${VDI_MAX_MIN}min" /bin/systemctl poweroff

# install -d forces ownership even if the directory exists in the image (spark-scale lesson:
# a root-owned scratch dir baked into the AMI broke Spark).
install -d -o ubuntu -g ubuntu /home/ubuntu/vdi-place /opt/vdi-place
echo "run=$VDI_PLACE_RUN booted_utc=$(date -u +%FT%TZ) max_min=$VDI_MAX_MIN" > /home/ubuntu/vdi-place/BOOT_INFO
chown ubuntu:ubuntu /home/ubuntu/vdi-place/BOOT_INFO
