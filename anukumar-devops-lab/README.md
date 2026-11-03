# Azure DevOps delivery lab

Independent portfolio project for Anukumar Bendi. AI-assisted implementation;
not employer code or evidence of a production deployment. Explain and test it
yourself before claiming proficiency from it.

## Validation status

Locally checked: Terraform 1.3.1 initialization and validation with AzureRM
4.81.0, provider checksums for Windows/Linux, nine Python unit tests using
mocked Graph responses, and Helm 3.19.0 lint/render.

Not executed: Azure plan/apply, AKS deployment, container startup, Kubernetes
policy/probe behavior, live Graph reads/writes or an Azure DevOps hosted run.
No cloud resources were created. These checks are a starting point, not
evidence of production readiness or a security audit.

## What this demonstrates

- **Terraform:** a resource-group/network module and an opt-in AKS module.
- **Delivery:** reusable Azure DevOps validation template; no automatic apply.
- **Helm:** non-root web workload, probes, resource requests/limits, disruption
  budget and a restricted network policy.
- **Entra:** direct user/group membership reconciliation with dry-run default,
  tenant checks, privileged/dynamic-group rejection, idempotency and read-back.

## Architecture and boundaries

```text
PR -> configured build-validation policy -> reusable validation pipeline
                                      |-> Terraform format/init/validate
                                      |-> Python mocked Graph tests
                                      |-> Helm lint/render -> review artifact

Terraform foundation -> resource group -> VNet -> application subnet + NSG
Terraform opt-in AKS -> managed network -> private AKS API -> Helm workload
Python CLI -> tenant check -> static security group -> membership read/write
```

The foundation VNet is **not wired to AKS**. AKS uses its own managed network,
keeping the demo explicit about what is and is not connected. A private cluster
requires an authorized network-connected operator/agent for kubectl/Helm.
This project does not build that network connection.

Cluster-level OIDC/workload identity is enabled, but the demo application does
not access Azure and has no federated identity or Azure role assignment.
Entra group membership is a separate exercise, not Kubernetes authorization.
The script does not create/delete accounts or grant directory/Azure roles.

## Validate without deploying

Requirements: Terraform >=1.3, Python >=3.10, Helm 3. Use a shell in this folder:

```powershell
terraform fmt -check -recursive infra
terraform -chdir=infra init -backend=false -input=false
terraform -chdir=infra validate
python -m unittest discover -s tests -v
helm lint charts\delivery-demo
helm template demo charts\delivery-demo
```

Initialization downloads the provider; it does not provision infrastructure.
Commit the generated provider lock file; CI uses `-lockfile=readonly`.
Run `terraform -chdir=infra providers lock -platform=linux_amd64 -platform=windows_amd64`
when preparing Linux CI from Windows.

The pipeline expects this folder at `devops-lab` in a repository. If publishing
it as a standalone repository, change `labDirectory` to `.` and the trigger
path to `*` in the entry pipeline. Agents must have compatible Terraform,
Python and Helm; missing tools fail visibly rather than skip checks.
Configure Azure Repos build-validation branch policy separately. No service
connection, Azure credentials or Graph access is required for these checks.
Helm rendering is not Kubernetes API/schema or runtime validation.

## Optional Azure execution: not performed by creating this project

Do not run apply until you have checked ownership, permissions and pricing.
Even the AKS Free SKU bills nodes, disks and networking. AKS defaults OFF.

1. Use a disposable subscription, inspect current prices and set a budget
   alert. A budget alert is not a spending cap.
2. Authenticate yourself; do not put credentials in configuration or Git.
3. Copy `infra\example.tfvars` to an ignored local tfvars file. Supply the
   actual subscription ID. Never use the all-zero example as a real value.
4. Review `terraform plan` with the explicit tfvars file before any apply.
   The demo uses local state by default: state may contain sensitive values.
   For collaboration, configure a separately bootstrapped Azure Storage
   backend with private access, least-privilege RBAC and state locking.
   Do not share or commit state/plan files.
5. To opt into AKS, supply an existing approved Entra admin group and set
   `enable_aks=true`. Check regional VM availability/quota first. One node is
   a cost-conscious lab choice, not a highly available production design.
6. With authorized private-network access, use non-admin Entra credentials.
   Render/review the chart, create a dedicated namespace and install there.
   NetworkPolicy permits port 8080 only from same-namespace pods labelled
   `access=demo-client`; egress is denied. No public endpoint is exposed.
7. Test rollout/probes, authorized client traffic and denied unlabeled
   traffic. Test these on a policy-enforcing cluster; rendering proves none
   of these runtime properties. The PDB needs two healthy replicas; it does
   not itself protect against node failure. Review image digest and
   vulnerability results before any serious use.

## Entra membership exercise

Use only a disposable **static, non-role-assignable security group** and an
existing test user. Confirm the group grants no sensitive resource access:
non-role-assignable groups can still carry powerful application/Azure access.

Your Azure CLI identity needs tenant-approved Microsoft Graph access.
For delegated access, membership updates generally require consented
`GroupMember.ReadWrite.All` and an appropriate group-owner/directory role;
metadata/user reads also need suitable permissions. Have the tenant owner
confirm the exact least-privilege setup. This lab does not request consent,
store a token or grant permissions automatically.

```powershell
python identity\group_membership.py --tenant TENANT_UUID --group GROUP_UUID --user USER_UUID --action add
```

This is a live **read-only dry run**, not an offline simulation. Inspect its
planned change. An authorized operator can explicitly opt into a write using
`--apply --confirm-group GROUP_UUID`. Use `--action remove` for offboarding
from this one group only. Removal does not revoke all access, end sessions or
delete the user. Inspect other memberships and access paths separately.

The script verifies membership after writing and fails explicitly if Graph
has not converged. Do not retry blindly after an error: inspect current
membership and audit logs first. JSON output contains directory IDs and is
not automatically persisted; retain an appropriate access-controlled audit
record without publishing identity data.

## Recovery, cleanup and evidence

- Terraform rollback is not "undo": inspect current state and a new plan;
  state backup alone does not restore deleted resources or application data.
- For a failed application rollout, inspect events/probes/logs, then choose a
  verified chart revision or correction. Helm rollback is not data recovery.
- For wrong membership, record the before/after and obtain approval for the
  compensating change. A successful API response is not enough; read back.
- Before cleanup, inventory data and owners. Review a destroy plan for this
  lab only. AKS deletion destroys its managed workload infrastructure.
- Check managed resource groups, disks and load balancers after approved
  cleanup; do not claim costs stopped until the inventory/billing confirms.
- Capture your own sanitized plan review, test run, rendered manifest,
  rollout result and membership audit. Do not label mocked tests as a live
  Entra integration or local validation as a successful Azure deployment.

## Interview walkthrough

Be able to explain: why AKS is opt-in/private; why state needs protection;
what `validate` cannot prove; why `$ref` matters for removal; why dry-run
still reads Graph; what idempotency means; why probes and a PDB differ;
and what must change before this could support production.
