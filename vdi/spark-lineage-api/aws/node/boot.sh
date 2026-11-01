#!/bin/bash
# Runs once on every cluster node as root, as EC2 user-data. 20_launch.sh prepends:
#   VDI_ROLE (driver|worker) VDI_CLUSTER VDI_MAX_MIN, and VDI_MASTER_IP for workers.
# Carries no secret: only the master's private IP and the cluster name (SECRETS.md).
#
# The driver node runs the standalone master and the application driver (client mode),
# and no worker, so every worker hosts exactly one executor at every cluster size.
set -euo pipefail
exec >/var/log/vdi-boot.log 2>&1
set -x

# Dead-man's switch: the instance is launched with shutdown behaviour = terminate, so this
# bounds its lifetime even if every laptop-side teardown fails.
systemd-run --unit="vdi-deadman-$(date +%s)" --on-active="${VDI_MAX_MIN}min" /bin/systemctl poweroff

set +x   # keep the IMDS session token out of the boot log
TOKEN="$(curl -fsS -X PUT http://169.254.169.254/latest/api/token \
    -H 'X-aws-ec2-metadata-token-ttl-seconds: 300')"
IP="$(curl -fsS -H "X-aws-ec2-metadata-token: $TOKEN" \
    http://169.254.169.254/latest/meta-data/local-ipv4)"
unset TOKEN
set -x

# install -d forces ownership even if the directory already exists: the first AMI
# (20261005-030749) carries a root-owned spark-local from the builder's smoke test, which
# a plain `mkdir -p` as ubuntu silently left in place, so Spark could not create its
# scratch dirs.
install -d -o ubuntu -g ubuntu /home/ubuntu/spark-local /home/ubuntu/spark-logs \
    /home/ubuntu/spark-work /home/ubuntu/vdi /home/ubuntu/vdi/eventlogs
echo "export SPARK_LOCAL_IP=$IP" >> /opt/spark/conf/spark-env.sh

case "$VDI_ROLE" in
    driver)
        echo "export SPARK_MASTER_HOST=$IP" >> /opt/spark/conf/spark-env.sh
        sudo -u ubuntu /opt/spark/sbin/start-master.sh
        ;;
    worker)
        # All 8 cores and most of the memory are offered; the executor itself is sized
        # by run_matrix.sh (7 cores, 48g), identically at every cluster size.
        sudo -u ubuntu /opt/spark/sbin/start-worker.sh "spark://$VDI_MASTER_IP:7077" \
            --cores 8 --memory 60g
        ;;
    *) echo "unknown VDI_ROLE=$VDI_ROLE"; exit 1 ;;
esac
