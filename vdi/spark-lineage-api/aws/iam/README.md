# IAM for the Spark scale-up runs (R2D16)

Everything the account admin needs to set up so the EC2 experiments in
`REVISION_SCALEUP.md` can run. Region `us-east-2`. Account-specific values (account ID,
organization, VPC) are kept out of the repo; see `../SECRETS.md`.

| File | For |
|---|---|
| `vdi-spark-scale-setup.yaml` | CloudFormation template: the single source of truth for every permission below |
| `walkthrough.md` | click-by-click guide for the admin, written for someone new to AWS |
| `verify/` | the verification battery; rerun after any template edit (`VENV=<venv> verify/verify.sh`) |

## What the template creates

| Resource | Purpose |
|---|---|
| Role + instance profile `vdi-spark-node` | Identity of the EC2 nodes. **Object read/write in every S3 bucket** (explicit list: list, get, put, delete, tagging, multipart), with no bucket administration (no create/delete bucket, bucket policy, object ACL, object lock or public-access changes). Only the SSM agent's minimum permissions, deliberately *not* `AmazonSSMManagedInstanceCore` (see Verification). **No EC2 or Parameter Store access.** |
| Bucket `vdi-spark-scale-results-<account-id>` | Experiment output, build artifacts, synced logs. Public access blocked, SSE-S3. **`DeletionPolicy: Retain`**, so deleting the stack can't destroy results. |
| Managed policy `vdi-spark-scale-operator` → user `tapan` | **All of EC2 in us-east-2** (`ec2:*`) except long-term purchase commitments, which are explicitly denied; pass only the node role, to EC2 only; SSH/SSM to any us-east-2 instance; **full S3** (`s3:*`); cost forecasts, list prices, vCPU quota requests |
| Group `vdi-spark-scale-billing-readers`, with user `tapan` added | AWS's `AWSBillingReadOnlyAccess` (v28; 77 actions, all Get/List/Describe/View): bills, invoice PDFs, budgets, Cost Explorer, free tier, payment status. **Read-only:** can't change the budget alert, billing preferences or payment methods. |
| Budget `vdi-spark-scale-monthly` | Emails at 50% and 80% actual, and 100% forecast, of a monthly threshold (default $800) |

A `Rules` assertion refuses deployment outside us-east-2.

## Workflow coverage

Checked step by step by the claims audit (`verify/claims_audit.py`, sections 0–7):

| Step | How | Covered by |
|---|---|---|
| 0. Network | Default VPC's public subnets; one security group allowing all traffic **between cluster nodes only**, nothing inbound from the internet; optional free S3 gateway endpoint | `ec2:*` in us-east-2 |
| 1. SSH key | `aws ec2 import-key-pair` | `ec2:*` |
| 2. Build | Build on a builder, or on every node: public subnets give **outbound** internet (Maven Central, GitHub, Thrift). Then bake an AMI, or share the tarball through S3 | `ec2:*`, `iam:PassRole`; node S3 read/write |
| 3. Access | Plain `ssh`/`scp`/`rsync`/`tmux -CC`, and `ssh -L` for the Spark UI, tunneled through SSM (config below) | SSM documents; `ec2:*` for key pairs |
| 4. Run | Spark reads `s3a://vod-tpch-1tb`; the listener writes usage logs, and the harness syncs CSVs and event logs, to `s3a://vdi-spark-scale-results-…` | node S3 read/write |
| 5. Manage | Stop/start/terminate, change instance type, extra EBS volumes, placement groups | `ec2:*` |
| 6. Cost | Cost Explorer, bills, budget, quota requests | billing group + operator |
| 7. Teardown | Terminate, deregister AMI, delete snapshots, security group, key pair, volumes | `ec2:*` |

## Design choices

**The admin runs the template; `tapan` can only pass the role.** Granting a user
`iam:CreateRole` amounts to privilege escalation. So the operator policy grants only
`iam:PassRole`, on this one role, and only to EC2.

**EC2: the template's grant is limited to us-east-2, but that is not a fence.** Live
testing after deployment showed that `tapan` **already had EC2 access in other
regions before the stack** (dry-run `DescribeInstances` and `CreateSecurityGroup` in
us-west-2 were both allowed). The template only adds permissions, so its region
condition narrows *its own* grant, not the user's. A real fence would need an explicit
`Deny` on EC2 outside us-east-2, which would also remove that existing access. Spend in
other regions is still bounded by each region's own vCPU quotas, and the budget alert
covers every region. The template grants `ec2:*` conditioned on
`aws:RequestedRegion = us-east-2`: any instance type, volumes, key pairs, VPCs,
subnets, security groups, endpoints, NAT and internet gateways, Elastic IPs, placement
groups. Chosen after the account inventory showed no other EC2 workloads (below).
**Explicitly denied:** Reserved Instance, host-reservation, Scheduled Instance and
Capacity Block purchases. Those are 1–3-year commitments that can't be undone and
this experiment never needs them. Marketplace AMIs with software charges also stay
unavailable, because subscribing needs `aws-marketplace` permissions, which aren't
granted.

**The vCPU quota is the cost ceiling for instances.** The Running On-Demand Standard
quota covers families A/C/D/H/I/M/R/T/Z; list prices across them run roughly
$0.05–0.10 per vCPU-hour. At a 248-vCPU quota, the worst standard type burns about 2×
the planned r7g rate (~$13/hr at full quota). That's a ballpark from list prices. GPU
and other accelerated families (P, G, Inf, Trn, DL, F, VT) and X/high-memory have
**separate** quotas, typically zero unless raised. `tapan` can request quota
increases himself, and AWS decides them, so the budget alert is the backstop.

**S3: full for the operator, object-level for the nodes.** The operator has `s3:*`.
The nodes can read and write objects in any bucket (Spark via s3a, `aws s3 cp/sync`,
including S3-to-S3 copies, which also copy object tags). They can't create or delete
buckets or change bucket policies, object ACLs, object lock or public access. The
action list is explicit rather than `s3:PutObject*`, which would also have matched
`PutObjectAcl`. **The dataset is no longer write-protected from cluster code.** To
guard against an accidental overwrite, turn on versioning for `vod-tpch-1tb`: storage
cost applies only to objects actually overwritten.

**Never bake credentials into an AMI.** `ec2:*` includes image and snapshot sharing
(`ModifyImageAttribute`, `ModifySnapshotAttribute`), so an AMI can be made public. The
nodes get their credentials from the instance role, and SSH private keys shouldn't be
in the image.

**The nodes can't call the EC2 API.** The launch script passes the master's private IP
into the workers' user-data, so no discovery permissions are needed.

## Network design

Nodes run in the **default VPC's public subnets** (`$VDI_VPC_ID`), with a security
group whose only inbound rule is *all traffic from itself*. Nothing is reachable from
the internet (not SSH, not Spark's 7077/8080/4040), but nodes have outbound internet
through the default internet gateway:

- **Building on nodes works:** Maven Central, GitHub and the Thrift source are
  reachable.
- **SSM works without interface endpoints:** the agent reaches Systems Manager over the
  internet.
- **Spark works across nodes:** standalone master/worker registration, executor-to-driver
  callbacks on random ports, and shuffle all fall under the self-referencing rule.
  Each worker starts itself from user-data (`sbin/start-worker.sh spark://<master-ip>:7077`)
  rather than through `sbin/start-workers.sh`, so nodes never SSH to each other and no
  cluster-internal private key exists to distribute (`../SECRETS.md`).
- **S3:** in-region traffic through the internet gateway is free. The S3 gateway
  endpoint is optional but also free, and keeps S3 traffic on AWS's network.
- **Public IPv4 addresses cost $0.005/hr each**, about $0.15/hr at 29 nodes.

This replaces the earlier private-subnet design, which had no route to the internet.
It would have blocked building Spark on nodes and needed three paid SSM interface
endpoints. If a private subnet is ever wanted, `ec2:*` covers the NAT gateway it
would need.

## Access: plain SSH, carried over SSM

The `AWS-StartSSHSession` document tunnels an ordinary SSH connection through Session
Manager. So `ssh`, `scp`, `rsync`, `ssh -L` (e.g. the Spark UIs on 8080 and 4040) and
`tmux -CC` (per `TMUX.md`) all work from the laptop, with no open port. The SSM shell,
Run Command and port-forwarding documents are also allowed. Session terminate and
resume are limited to `tapan`'s own sessions.

```
# ~/.ssh/config  (needs session-manager-plugin installed locally)
Host i-*
    User ubuntu            # or ec2-user, depending on the AMI
    IdentityFile ~/.ssh/vdi-spark
    ProxyCommand aws ssm start-session --target %h --document-name AWS-StartSSHSession --parameters portNumber=%p --region us-east-2
```

Instance IDs change on every launch, so `20_launch.sh` should write friendly aliases
(`Host spark-master`, `spark-w1`, … with `HostName i-…`) into an included config file.

## Logs and local disk

- **Spark's own logs** (daemon logs, executor stdout/stderr, the work dir) go to each
  node's local disk and need no permissions. They need **space**: r7g has no instance
  store, and many AMIs default to an 8 GB root volume. Launch with a larger gp3 root
  volume via `--block-device-mappings` (100–200 GB), or use `r7gd` (local NVMe) with
  `spark.local.dir` on it. Shuffle at SF1000, more than the logs, is what fills disks.
- **Local logs are lost at termination.** The root volume is deleted with the instance,
  and the dead-man's switch terminates on shutdown. Sync result CSVs and logs to S3
  after each batch (`aws s3 sync`, node role), and set
  `spark.eventLog.dir=s3a://vdi-spark-scale-results-…/spark-events/`.
- **The listener's usage logs must go to S3 on a cluster.** The write runs as a
  distributed Spark job, so a local path scatters task output across nodes and the
  commit fails. The `cols` and `bare` variants used to ignore the path argument and
  hardcode `/tmp/iceberg/warehouse/usage_logs`. That's fixed (2026-09-27): both now
  read `args(3)` like `rowgroup`, so pass an `s3a://` path. `nowrite`, `vanilla` and
  `register` don't write usage logs.
- The per-query CSVs (`appendToCsv`) are written on the driver's local disk, which is
  fine, but include them in the S3 sync.

## Live verification after deployment (2026-09-27)

The stack deployed successfully. Probed as `tapan` using read-only calls, `--dry-run`
requests (evaluated for permission, nothing created), SSM calls against a non-existent
instance ID, and one tiny S3 object written and deleted:

| Check | Result |
|---|---|
| Results bucket | exists; public access fully blocked; SSE-S3 (AES256); stack-tagged |
| Budget | exists; threshold set to **$1,500** by the admin (alerts at $750 and $1,200 actual, $1,500 forecast) |
| vCPU quota (Running On-Demand Standard, us-east-2) | **512**, which already covers {1,4,8,16} in parallel (264). No request needed |
| r7g.2xlarge price (Pricing API) | **$0.4284/hr**, confirming the budget model's assumed price |
| Launch r7g.2xlarge with node role, 150 GB gp3, tags (dry run) | allowed |
| Launch another type; key pair, security group, volume, placement group, VPC (dry run) | allowed |
| **Buy a Reserved Instance (dry run)** | **denied**: the explicit Deny overrides every Allow, including pre-existing ones |
| EC2 in us-west-2 (dry run) | **allowed, from pre-existing permissions** (see EC2 boundary above) |
| Run Command `AWS-RunShellScript` / SSH session `AWS-StartSSHSession` | allowed |
| Run Command with another document | denied |
| Parameter Store read | denied, as designed. Look up AMI IDs with `ec2 describe-images` instead |
| S3 put/get/delete on the results bucket; read the dataset | ok |
| IAM read | denied (no IAM powers) |
| Cost Explorer query + forecast, budget spend | **all work**: neither the root-user billing switch nor the Organization blocks it. September to date: $13.03, forecast $15.03 |

**Not yet verified live: the node role**, meaning the minimal SSM agent permissions and
s3a access from a node. That needs one real instance to boot.

## Offline verification (2026-09-27)

AWS's own checkers (IAM Access Analyzer, the IAM policy simulator,
`cloudformation validate-template`) are all denied to `tapan`, so verification is
offline. All of it lives in `verify/`:

| Check | Result |
|---|---|
| File hygiene: ASCII, no tabs or trailing whitespace, final newline; 13.7 KB, under the 51,200-byte console upload limit | pass |
| `yamllint`, default rules, 120-column lines | clean |
| `cfn-lint` 1.57, errors and warnings, us-east-2 resource schemas | clean |
| Managed-policy size, non-whitespace characters, limit 6,144 | operator 1,730; node inline 891 |
| Parliament 1.6.4 with community auditors | every finding accounted for (below) |
| **Claims audit**: 48 allow/deny tests covering every workflow step (above) and every fence, against the rendered policies plus the AWS managed policies attached through groups; models explicit Deny | **48/48 hold** |

**History.** The first version failed 10 of 53 claims; all were fixed in the template.
The one that still matters: the node role originally used AWS's
`AmazonSSMManagedInstanceCore`, which grants `ssm:GetParameter(s)` on `*` (checked
against AWS's published policy, v2). Through SSM, the operator could therefore read
every Parameter Store value in the account. The tag boundary was later removed by
choice, and EC2 widened to `ec2:*` in us-east-2, after the inventory below. A
workflow audit (2026-09-27) then found gaps a claims-only audit had missed: no
outbound internet for builds, nodes unable to write outside the results bucket or
copy between buckets, and the `cols`/`bare` hardcoded log path.

**Remaining Parliament findings, each checked:**
- *PassRole + RunInstances privilege escalation* (HIGH): justified. The operator holds
  every node-role S3 permission. The only node-role permissions it lacks are the SSM
  agent's own messaging calls, which give no access to data or other resources.
- *Permissions management* (MEDIUM): `iam:PassRole` (scoped), plus S3 policy, ACL and
  public-access actions from `s3:*`, plus image/snapshot sharing from `ec2:*`.
  Intended. See "Never bake credentials into an AMI".
- *Resource `*`* (LOW ×3): `ec2:*`, `s3:*` and the nodes' `s3:GetBucketLocation`. All
  intentional; EC2 is fenced by region.

**What the audit can't cover** (so the first real deployment remains the final test):
service control policies (the account is in an Organization), `tapan`'s *existing*
permissions (the template adds but never removes), and AWS behaviour that differs from
its documentation.

## Seeing costs: two switches IAM can't flip

1. **"IAM user and role access to Billing information"** must be activated once, by the
   account's **root user** (Account page → *IAM user and role access to Billing
   information* → Edit → Activate). Until it is, no IAM policy opens the Billing and Cost
   Management console, which includes Cost Explorer.
2. **This is a member account in an AWS Organization.** Whoever runs the organization's
   management account controls whether member accounts can use Cost Explorer, and
   receives the invoices. Cost allocation tags (for per-project breakdowns) can only be
   activated there too.

**Test after the stack is up:** `aws ce get-cost-and-usage --time-period
Start=YYYY-MM-01,End=YYYY-MM-DD --granularity MONTHLY --metrics UnblendedCost`.
An `AccessDenied` naming an IAM action means the policy is missing; any other refusal
points at switch 1 or 2. Cost Explorer API calls cost $0.01 each.

**Cost data lags by up to about 24 hours**, so it's for accounting, not a real-time kill
switch. During runs, running-instance-hours × price (`budget_model.py`) is the live
estimate; the dead-man's switch and verified teardown are the real guards.

## Tagging: recommended, not required

The policy doesn't require tags, but the scripts should tag everything they create
`project=vdi-spark-scale`. The teardown script finds resources by that tag and then
lists them to confirm none remain, so an untagged instance would escape teardown and
keep billing until the dead-man's switch fires. The tag also enables per-project cost
breakdowns, once activated in the management account.

## Checked facts about the account

- **EC2 inventory in us-east-2 (2026-09-26):** 0 instances, 0 owned AMIs, 0 launch
  templates, 0 VPC endpoints. VPCs: the default (172.31.0.0/16) plus two from earlier,
  unrelated projects, with 8 non-default security groups. This is what justified
  dropping the tag boundary and granting `ec2:*`.
- **EBS default encryption is off, and the default key is AWS-managed**
  (`alias/aws/ebs`). No KMS permissions needed.
- **The data buckets use SSE-S3 (AES256).** No KMS permissions needed for S3 either.
- **The account is in an AWS Organization.** A service control policy
  could deny actions the template allows; the walkthrough tells the admin how to
  recognise that.

## Operational notes

- **Changing instance type within Graviton (ARM) is free**: same AMI, different
  `--instance-type`, and `budget_model.py --price <new $/hr>` to re-budget. **Switching
  to Intel or AMD needs a second, x86 AMI build**, because the ARM image won't boot on
  x86. Keep the type identical across all node counts; changing it mid-matrix confounds
  the node-count axis.
- **Clone the Spark and parquet-java forks over HTTPS** if they're public, or copy a
  source tarball from S3. That avoids putting a GitHub SSH key on a cloud instance.
- **Redeploying after deleting the stack** fails on the results bucket name, because the
  retained bucket still exists. Delete or rename the bucket first.
- **The node role's minimal SSM policy must be confirmed on first boot.** It follows
  AWS's documented minimum for Session Manager and Run Command. If a node doesn't
  appear in SSM, add back only the specific missing action, never the whole managed
  policy.
- **Budget alerts are account-wide.** They cover total monthly spend, including the
  ~700GB already stored in the dataset buckets, not just this project.
