"""Offline claims audit for the VDI IAM template, organised as the real workflow.

Evaluates identity-based policies: Allow and explicit Deny (Deny wins),
action/resource wildcards, StringEquals / StringLike / ArnLike conditions, IAM
policy variables, and AWS managed policies the template attaches (verified
local copies in this directory). An API call is allowed only if EVERY resource
it authorizes is allowed.

Does NOT model: SCPs (the account is in an Organization), permission boundaries,
session policies, resource-based policies, or permissions the principal already
had before the stack. It checks what the TEMPLATE grants, nothing more.
"""
import fnmatch, json, os, sys
D = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
def load(n):
    f = f"{D}/{n}.json"
    return json.load(open(f))["Statement"] if os.path.exists(f) else []

ACCT, REG = "123456789012", "us-east-2"  # placeholder; must match render.py
def arn(kind, rid, region=REG):
    if kind in ("image", "snapshot"): return f"arn:aws:ec2:{region}::{kind}/{rid}"
    return f"arn:aws:ec2:{region}:{ACCT}:{kind}/{rid}"
DATA, DS, RES = "vod-tpch-1tb", "vod-tpcds-1tb", f"vdi-spark-scale-results-{ACCT}"
S3 = lambda b, k=None: f"arn:aws:s3:::{b}" + (f"/{k}" if k else "")
SSMDOC = lambda d: (f"arn:aws:ssm:{REG}:{ACCT}:document/{d}" if d == "SSM-SessionManagerRunShell"
                    else f"arn:aws:ssm:{REG}::document/{d}")

def as_list(x): return x if isinstance(x, list) else [x]
def glob(p, v): return fnmatch.fnmatchcase(v.lower(), p.lower())
def subvars(s, ctx): return s.replace("${aws:username}", ctx.get("aws:username", "\0"))

def cond_ok(cond, ctx):
    for op, kv in (cond or {}).items():
        for key, want in kv.items():
            have = ctx.get(key)
            if have is None: return False
            want = as_list(want)
            if op == "StringEquals" and have not in want: return False
            if op in ("StringLike", "ArnLike") and not any(glob(w, have) for w in want): return False
            if op not in ("StringEquals", "StringLike", "ArnLike"): raise ValueError(op)
    return True

def matches(s, action, r, c):
    return (any(glob(a, action) for a in as_list(s["Action"]))
            and any(glob(subvars(p, c), r) for p in as_list(s["Resource"]))
            and cond_ok(s.get("Condition"), c))

def allowed(stmts, action, resources, ctx):
    """resources: list of (arn, resource_tags) that the API authorizes."""
    for r, rtags in resources:
        c = dict(ctx); c.update({f"aws:ResourceTag/{k}": v for k, v in rtags.items()})
        if any(s["Effect"] == "Deny" and matches(s, action, r, c) for s in stmts): return False
        if not any(s["Effect"] == "Allow" and matches(s, action, r, c) for s in stmts): return False
    return True

OP = load("operator") + load("operator-network")
for _arn in json.load(open(f"{D}/operator-managed-arns.json")):
    OP += json.load(open(f"{HERE}/aws-{_arn.rsplit('/', 1)[1]}.json"))["Statement"]
NODE = load("node-role-inline")
base = {"aws:RequestedRegion": REG, "aws:username": "tapan"}
def ctx(**kw): c = dict(base); c.update(kw); return c
WEST = ctx(**{"aws:RequestedRegion": "us-west-2"})
def op(a, *res, c=None): return allowed(OP, a, [(r, {}) for r in res], c or ctx())
def node(a, *res): return allowed(NODE, a, [(r, {}) for r in res], base)
def launch(region=REG, itype="r7g.2xlarge", key=True, profile=True):
    c = ctx(**{"aws:RequestedRegion": region, "ec2:InstanceType": itype})
    res = [arn(k, "*", region) for k in ("instance", "volume", "network-interface")] + \
          [arn("image", "ami-1", region), arn("subnet", "subnet-default-a", region), arn("security-group", "sg-cluster", region)]
    if key: res.append(arn("key-pair", "vdi-spark", region))
    ok = op("ec2:RunInstances", *res, c=c)
    if profile: ok = ok and allowed(OP, "iam:PassRole", [(f"arn:aws:iam::{ACCT}:role/vdi-spark-node", {})], ctx(**{"iam:PassedToService": "ec2.amazonaws.com"}))
    return ok

CASES = [
 # ============ 0. one-time network: default VPC public subnets, SG with no inbound from outside
 ("0 create cluster security group in default VPC", True, op("ec2:CreateSecurityGroup", arn("security-group", "*"), arn("vpc", "vpc-default"))),
 ("0 allow all traffic between cluster nodes (self-referencing rule)", True, op("ec2:AuthorizeSecurityGroupIngress", arn("security-group", "sg-cluster"))),
 ("0 optional: S3 gateway endpoint on default route table", True, op("ec2:CreateVpcEndpoint", arn("vpc-endpoint", "*"), arn("vpc", "vpc-default"), arn("route-table", "rtb-default"))),
 ("0 optional: private subnet + NAT gateway + Elastic IP, if ever wanted", True, op("ec2:CreateSubnet", arn("subnet", "*"), arn("vpc", "vpc-1")) and op("ec2:CreateNatGateway", arn("natgateway", "*"), arn("subnet", "s-1")) and op("ec2:AllocateAddress", arn("elastic-ip", "*"))),
 ("0 optional: cluster placement group", True, op("ec2:CreatePlacementGroup", arn("placement-group", "*"))),
 # ============ 1. SSH key
 ("1 import SSH public key as key pair", True, op("ec2:ImportKeyPair", arn("key-pair", "*"))),
 # ============ 2. build: builder with internet, or build on every node; bake AMI; share binary via S3
 ("2 launch builder/nodes with key pair + node role + big root volume", True, launch()),
 ("2 launch ANY instance type (e.g. r7gd with NVMe, or x86)", True, launch(itype="r7gd.4xlarge") and launch(itype="r7i.2xlarge")),
 ("2 bake AMI from builder", True, op("ec2:CreateImage", arn("instance", "i-builder"), arn("image", "*"), arn("snapshot", "*"))),
 ("2 node: upload built Spark tarball to S3", True, node("s3:PutObject", S3(RES, "artifacts/spark-vod-rg.tgz"))),
 ("2 node: pull Spark tarball from S3", True, node("s3:GetObject", S3(RES, "artifacts/spark-vod-rg.tgz"))),
 ("2 operator: upload tarball from laptop", True, op("s3:PutObject", S3(RES, "artifacts/spark-vod-rg.tgz"))),
 # ============ 3. access: terminal SSH over SSM, scp/rsync, Spark UI tunnel
 ("3 ssh / scp / rsync over SSM (AWS-StartSSHSession)", True, op("ssm:StartSession", arn("instance", "i-node"), SSMDOC("AWS-StartSSHSession"))),
 ("3 port-forward Spark UI", True, op("ssm:StartSession", arn("instance", "i-node"), SSMDOC("AWS-StartPortForwardingSession"))),
 ("3 run a command on all nodes (Run Command)", True, op("ssm:SendCommand", arn("instance", "i-node"), SSMDOC("AWS-RunShellScript"))),
 ("3 node: SSM agent can register and open channels", True, node("ssm:UpdateInstanceInformation", "*") and node("ssmmessages:OpenDataChannel", "*") and node("ec2messages:GetMessages", "*")),
 # ============ 4. run: Spark reads data in S3, writes usage logs / results / event logs
 ("4 node: list + read TPC-H data (s3a)", True, node("s3:ListBucket", S3(DATA)) and node("s3:GetObject", S3(DATA, "lineitem.parquet"))),
 ("4 node: read TPC-DS data (later experiments)", True, node("s3:GetObject", S3(DS, "store_sales.parquet"))),
 ("4 node: write listener usage logs (s3a, incl. temp objects + multipart)", True, all(node(a, S3(RES, "usage-logs/_temporary/x")) for a in ["s3:PutObject", "s3:DeleteObject", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"]) and node("s3:ListBucketMultipartUploads", S3(RES))),
 ("4 node: sync result CSVs / Spark event logs to S3 before shutdown", True, node("s3:PutObject", S3(RES, "results/run1/x.csv")) and node("s3:PutObject", S3(RES, "spark-events/app-1"))),
 ("4 node: S3-to-S3 copy (aws s3 cp copies object tags)", True, node("s3:GetObjectTagging", S3(DATA, "x")) and node("s3:PutObjectTagging", S3(RES, "x"))),
 ("4 node: write/overwrite in ANY bucket (e.g. regenerate TPC-DS item)", True, node("s3:PutObject", S3(DS, "item.parquet"))),
 ("4 node: list all buckets (aws s3 ls)", True, node("s3:ListAllMyBuckets", "*")),
 # ============ 5. manage + resize
 ("5 stop / start / reboot / terminate any Ohio instance", True, all(op(a, arn("instance", "i-node")) for a in ["ec2:StopInstances", "ec2:StartInstances", "ec2:RebootInstances", "ec2:TerminateInstances"])),
 ("5 change instance type of a stopped node", True, op("ec2:ModifyInstanceAttribute", arn("instance", "i-node"))),
 ("5 attach / detach / resize extra EBS volumes", True, op("ec2:CreateVolume", arn("volume", "*")) and op("ec2:AttachVolume", arn("volume", "vol-1"), arn("instance", "i-node")) and op("ec2:ModifyVolume", arn("volume", "vol-1"))),
 ("5 attach node role to a running instance", True, op("ec2:AssociateIamInstanceProfile", arn("instance", "i-node"))),
 # ============ 6. cost + quota
 ("6 Cost Explorer query + forecast", True, op("ce:GetCostAndUsage", "*") and op("ce:GetCostForecast", "*")),
 ("6 view bills / invoices / budgets", True, op("billing:GetBillingData", "*") and op("invoicing:GetInvoicePDF", "*") and op("budgets:ViewBudget", f"arn:aws:budgets::{ACCT}:budget/vdi-spark-scale-monthly")),
 ("6 request vCPU quota increase", True, op("servicequotas:RequestServiceQuotaIncrease", "*")),
 # ============ 7. teardown
 ("7 terminate, deregister AMI, delete snapshots/SG/key/endpoint/volumes", True, all([op("ec2:TerminateInstances", arn("instance", "i-node")), op("ec2:DeregisterImage", arn("image", "ami-1")), op("ec2:DeleteSnapshot", arn("snapshot", "snap-1")), op("ec2:DeleteSecurityGroup", arn("security-group", "sg-cluster")), op("ec2:DeleteKeyPair", arn("key-pair", "vdi-spark")), op("ec2:DeleteVpcEndpoints", arn("vpc-endpoint", "vpce-1")), op("ec2:DeleteVolume", arn("volume", "vol-1"))])),
 # ============ fences that must hold
 ("F any EC2 action outside us-east-2", False, launch(region="us-west-2") or op("ec2:TerminateInstances", arn("instance", "i-w", "us-west-2"), c=WEST)),
 ("F buy Reserved Instances (1-3 yr commitment)", False, op("ec2:PurchaseReservedInstancesOffering", "*")),
 ("F buy a Capacity Block / host reservation", False, op("ec2:PurchaseCapacityBlock", "*") or op("ec2:PurchaseHostReservation", "*")),
 ("F pass any role other than the node role", False, allowed(OP, "iam:PassRole", [(f"arn:aws:iam::{ACCT}:role/Admin", {})], ctx(**{"iam:PassedToService": "ec2.amazonaws.com"}))),
 ("F pass the node role to a non-EC2 service", False, allowed(OP, "iam:PassRole", [(f"arn:aws:iam::{ACCT}:role/vdi-spark-node", {})], ctx(**{"iam:PassedToService": "lambda.amazonaws.com"}))),
 ("F create IAM roles / attach policies to self", False, op("iam:CreateRole", f"arn:aws:iam::{ACCT}:role/x") or op("iam:AttachUserPolicy", f"arn:aws:iam::{ACCT}:user/tapan")),
 ("F modify/delete the budget alert", False, op("budgets:ModifyBudget", f"arn:aws:budgets::{ACCT}:budget/vdi-spark-scale-monthly")),
 ("F change billing preferences / payment methods", False, op("billing:UpdateBillingPreferences", "*") or op("payments:UpdatePaymentPreferences", "*")),
 ("F SSM documents other than shell/SSH/run-script/port-forward", False, op("ssm:SendCommand", arn("instance", "i-node"), SSMDOC("AWS-ApplyPatchBaseline"))),
 ("F end someone else's SSM session", False, op("ssm:TerminateSession", f"arn:aws:ssm:{REG}:{ACCT}:session/alice-0abc")),
 ("F operator reads Parameter Store", False, op("ssm:GetParameters", f"arn:aws:ssm:{REG}:{ACCT}:parameter/p")),
 ("F node: any EC2 API", False, node("ec2:DescribeInstances", "*")),
 ("F node: read Parameter Store secrets", False, node("ssm:GetParameters", f"arn:aws:ssm:{REG}:{ACCT}:parameter/p")),
 ("F node: create or delete buckets", False, node("s3:CreateBucket", S3("new")) or node("s3:DeleteBucket", S3(DATA))),
 ("F node: change object ACLs or object lock", False, node("s3:PutObjectAcl", S3(DATA, "x")) or node("s3:PutObjectRetention", S3(DATA, "x"))),
 ("F node: change bucket policy / public access", False, node("s3:PutBucketPolicy", S3(DATA)) or node("s3:PutBucketPublicAccessBlock", S3(DATA))),
 # ============ operator S3 (full, by choice)
 ("S operator: full S3 incl. bucket admin", True, op("s3:CreateBucket", S3("new")) and op("s3:PutObject", S3(DATA, "x")) and op("s3:PutBucketVersioning", S3(DATA))),
]
fails = 0
for claim, want, got in CASES:
    ok = want == got
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  expect {'ALLOW' if want else 'DENY ':5s} got {'ALLOW' if got else 'DENY ':5s}  {claim}")
print(f"\n{len(CASES) - fails}/{len(CASES)} claims hold, {fails} violated")
sys.exit(1 if fails else 0)
