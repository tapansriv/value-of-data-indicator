"""Render the CFN template's IAM policies to concrete JSON, resolving intrinsics."""
import json, re, sys
from cfnlint.decode import decode
tpl_path, outdir = sys.argv[1], sys.argv[2]
tpl, errs = decode(tpl_path); assert not errs, errs
P = {k: v.get("Default") for k, v in tpl["Parameters"].items()}
# AWS's documentation placeholder: the audit needs one consistent account ID, not the real one
P.update({"AWS::AccountId": "123456789012", "AWS::Region": "us-east-2", "AWS::Partition": "aws"})
RES = {"ResultsBucket": "vdi-spark-scale-results-123456789012", "NodeRole": "vdi-spark-node",
       "NodeInstanceProfile": "vdi-spark-node"}
ATT = {"NodeRole.Arn": "arn:aws:iam::123456789012:role/vdi-spark-node",
       "ResultsBucket.Arn": "arn:aws:s3:::vdi-spark-scale-results-123456789012"}
def sub(s):
    def rep(m):
        k = m.group(1)
        if k.startswith("!"): return "${" + k[1:] + "}"
        if k in P: return str(P[k])
        if k in ATT: return ATT[k]
        if k in RES: return RES[k]
        raise KeyError(k)
    return re.sub(r"\$\{([^}]+)\}", rep, s)
def r(x):
    if isinstance(x, dict):
        if len(x) == 1:
            k, v = next(iter(x.items()))
            if k == "Fn::Sub": return sub(v if isinstance(v, str) else v[0])
            if k == "Fn::GetAtt": return ATT[".".join(v) if isinstance(v, list) else v]
            if k == "Ref": return P.get(v, RES.get(v))
        return {kk: r(vv) for kk, vv in x.items()}
    if isinstance(x, list): return [r(i) for i in x]
    return x
out = {}
R = tpl["Resources"]
out["node-role-trust"] = r(R["NodeRole"]["Properties"]["AssumeRolePolicyDocument"])
out["node-role-inline"] = {"Version": "2012-10-17", "Statement": [st for pol in R["NodeRole"]["Properties"]["Policies"] for st in r(pol["PolicyDocument"])["Statement"]]}
assert "ManagedPolicyArns" not in R["NodeRole"]["Properties"], "node role still attaches a managed policy"
out["operator"] = r(R["OperatorPolicy"]["Properties"]["PolicyDocument"])
if "OperatorNetworkPolicy" in R:
    out["operator-network"] = r(R["OperatorNetworkPolicy"]["Properties"]["PolicyDocument"])
# AWS managed policies reaching the operator through group membership
groups = {n: r_["Properties"].get("ManagedPolicyArns", []) for n, r_ in R.items() if r_["Type"] == "AWS::IAM::Group"}
op_managed = []
for n, r_ in R.items():
    if r_["Type"] != "AWS::IAM::UserToGroupAddition": continue
    if {"Ref": "OperatorUserName"} not in r_["Properties"]["Users"]: continue
    op_managed += groups[r_["Properties"]["GroupName"]["Ref"]]
json.dump(op_managed, open(f"{outdir}/operator-managed-arns.json", "w"), indent=2)
print(f"operator gets managed policies via groups: {op_managed}")
for k, v in out.items():
    json.dump(v, open(f"{outdir}/{k}.json", "w"), indent=2)
    print(f"rendered {k}.json  ({len(v['Statement'])} statements)")
