# Secrets and account identifiers for the EC2 runs

This repo (`TheDataStation/value-of-data-metric`) is **private**: it is where development
happens. Its contents are published once, by syncing into `vdi/` of the **public** artifact
repo `tapansriv/value-of-data-indicator` (the URL the paper cites), whose `spark/` and
`parquet-java/` submodules point at the public forks. Anything committed here therefore
becomes public at that sync. So the rule is simple: **nothing account-specific is ever
committed.** This file says where each sensitive thing lives instead, and how it reaches
the cluster.

## Where each thing lives

| What | Sensitivity | Lives in | Reaches nodes via |
|---|---|---|---|
| Laptop AWS credentials (IAM user `tapan`) | **secret** | macOS Keychain via `aws-vault` (see below); never in the repo | never. Nodes use the instance role |
| Node AWS credentials | **secret**, short-lived | nowhere on disk: instance role `vdi-spark-node`, rotated by AWS | instance metadata, IMDSv2 only |
| SSH private key, laptop to nodes | **secret** | `~/.ssh/vdi-spark`, mode 600 | never. Only the public half is imported as a key pair |
| Node-to-node SSH key | n/a | **does not exist**: workers start themselves from user-data | — |
| Account ID, organization ID, VPC ID, results bucket name | identifying, not secret | `~/.config/vdi-spark/env`, mode 600, outside every repo | the launch script passes only what a node needs (bucket name, master IP) |
| Data bucket names (`vod-tpch-1tb`, `vod-tpcds-1tb`) | low; the buckets are private | the config above, and cited in docs | user-data / script arguments |

The config lives *outside* the repo on purpose. A gitignored file inside the tree
would still be missed by new worktrees (they don't share untracked files) and swept
up by the artifact sync, which copies directories.

## Setup, once per machine

```bash
mkdir -p ~/.config/vdi-spark && chmod 700 ~/.config/vdi-spark
cp spark-lineage-api/aws/env.example ~/.config/vdi-spark/env && chmod 600 ~/.config/vdi-spark/env
$EDITOR ~/.config/vdi-spark/env                # fill in the (guarded) values
spark-lineage-api/aws/git-hooks/install.sh     # the leak guard, below
```

Scripts in `aws/` begin with:

```bash
. "$(dirname "$0")/env.sh"
vdi_check_account     # refuses to run if the active credentials are for another account
```

## Laptop credentials: move the long-lived keys into the Keychain

As of 2026-09-27 the `tapan` access key sits in plain text in `~/.aws/credentials`.
Any process or backup that reads the home directory gets a key that never expires
and holds `ec2:*` and `s3:*`. `aws-vault` keeps the key in the macOS Keychain
and hands each command short-lived STS credentials instead:

```bash
brew install aws-vault
# import straight from the existing file; pasting at the hidden prompt is error-prone
# (a stray space or truncated secret fails later with SignatureDoesNotMatch)
AWS_ACCESS_KEY_ID="$(aws configure get aws_access_key_id)" \
AWS_SECRET_ACCESS_KEY="$(aws configure get aws_secret_access_key)" \
  aws-vault add vdi --env
aws-vault exec vdi -- aws sts get-caller-identity
# once that prints user/tapan, delete the two key lines under [default] in
# ~/.aws/credentials; keep region in ~/.aws/config
```

From then on, prefix every AWS-touching command with `aws-vault exec vdi --`. For
example, once the planned launch script exists (`REVISION_SCALEUP.md` §9; not yet
written), a 4-node cluster would be started with:

```bash
aws-vault exec vdi -- spark-lineage-api/aws/20_launch.sh 4   # billable: starts EC2 instances
```

This needs no admin change. If the admin later adds MFA to the user, add
`mfa_serial` to the profile and `aws-vault` will prompt for it. Rotate the access key
(IAM console → Security credentials) if it was ever copied anywhere else.

## Rules for launch scripts

- **No secret in user-data, launch templates, tags or AMIs.** Any process on the node
  can read user-data from instance metadata, and anyone with
  `ec2:DescribeInstanceAttribute` can too. User-data carries only the master's private
  IP, the bucket name and the tag.
- **Require IMDSv2** (`--metadata-options HttpTokens=required,HttpPutResponseHopLimit=1`)
  so an SSRF in anything running on a node can't lift the instance-role credentials.
- **Never bake credentials or private keys into an AMI.** `ec2:*` includes making an
  image public (`iam/README.md`, "Never bake credentials into an AMI").
- **Workers start themselves** with `sbin/start-worker.sh spark://<master-ip>:7077`
  from user-data. `sbin/start-workers.sh` would need a private key on the master that
  opens every worker.
- **Clone forks over HTTPS** or pull a source tarball from S3, so no GitHub key lands
  on a node.

Parameter Store and Secrets Manager are deliberately **not** used: the IAM design
denies them to both the operator and the nodes (`iam/README.md`, History), and the
design above leaves no secret that would need them. If one appears (say, an API
token), that is an admin change to the template, not a workaround.

## The leak guard

`git-hooks/pre-commit`, installed into the clone's shared hooks directory so it covers
every worktree, refuses a commit that adds:

- an AWS access key ID (`AKIA…`/`ASIA…`), a secret-key or session-token field set to a value, or a
  private key block;
- an ARN containing a real account ID (AWS's placeholder `123456789012` is allowed);
- any (guarded) value from `~/.config/vdi-spark/env`: account ID, organization ID,
  VPC ID. The hook reads the values locally, so they never have to appear in the repo
  to be checked.

For a genuine false positive, `git commit --no-verify`, deliberately.
The hook only sees new commits; it is not a history scanner.
