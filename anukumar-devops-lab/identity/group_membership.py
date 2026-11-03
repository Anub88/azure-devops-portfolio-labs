"""Dry-run-first direct membership lab for non-role-assignable Entra security groups."""

import argparse
import json
import shutil
import subprocess
import sys
from urllib.parse import urlparse
from uuid import UUID

GRAPH = "https://graph.microsoft.com/v1.0"


def object_id(value):
    try:
        return str(UUID(value))
    except (ValueError, AttributeError) as error:
        raise ValueError("Tenant, group and user IDs must be UUIDs.") from error


class AzureCLI:
    def __init__(self):
        self.executable = shutil.which("az")
        if not self.executable:
            raise RuntimeError("Azure CLI is missing. Install it and authenticate to the intended tenant.")

    def run(self, args):
        result = subprocess.run(
            [self.executable, *args], capture_output=True, text=True, check=False
        )
        if result.returncode:
            raise RuntimeError(f"Azure CLI failed ({result.returncode}): {result.stderr.strip()}")
        return result.stdout.strip()

    def tenant(self):
        return self.run(["account", "show", "--query", "tenantId", "--output", "tsv"])

    def request(self, method, url, body=None):
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "graph.microsoft.com":
            raise ValueError("Only the Microsoft Graph HTTPS endpoint is allowed.")
        args = ["rest", "--method", method, "--url", url, "--output", "json"]
        if body is not None:
            args += ["--headers", "Content-Type=application/json", "--body", json.dumps(body)]
        output = self.run(args)
        return json.loads(output) if output else None


def is_member(client, group, user):
    url = f"{GRAPH}/groups/{group}/members?$select=id&$top=999"
    visited = set()
    while url:
        if url in visited:
            raise RuntimeError("Microsoft Graph returned a repeated membership page.")
        visited.add(url)
        page = client.request("GET", url)
        if not isinstance(page, dict) or not isinstance(page.get("value"), list):
            raise RuntimeError("Microsoft Graph returned an invalid membership page.")
        for member in page["value"]:
            if not isinstance(member, dict) or not isinstance(member.get("id"), str):
                raise RuntimeError("Membership data is incomplete; refusing to infer absence.")
            if member["id"].lower() == user:
                return True
        url = page.get("@odata.nextLink")
        if url is not None and not isinstance(url, str):
            raise RuntimeError("Microsoft Graph returned an invalid next-page link.")
    return False


def reconcile(client, tenant, group, user, action, apply=False, confirm_group=None):
    tenant, group, user = map(object_id, (tenant, group, user))
    if action not in ("add", "remove"):
        raise ValueError("Action must be add or remove.")
    if object_id(client.tenant()) != tenant:
        raise RuntimeError("Authenticated tenant differs from the requested tenant. No change made.")
    if apply and (confirm_group is None or object_id(confirm_group) != group):
        raise ValueError("Apply requires --confirm-group with the exact target group ID.")
    details = client.request(
        "GET", f"{GRAPH}/groups/{group}?$select=id,securityEnabled,isAssignableToRole,groupTypes"
    )
    if not isinstance(details, dict):
        raise RuntimeError("Group metadata is missing.")
    if details.get("securityEnabled") is not True or details.get("isAssignableToRole") is not False:
        raise RuntimeError("Only confirmed non-role-assignable security groups are supported.")
    types = details.get("groupTypes")
    if not isinstance(types, list) or types:
        raise RuntimeError("Only static security groups are supported; dynamic and Microsoft 365 groups are excluded.")
    target = client.request("GET", f"{GRAPH}/users/{user}?$select=id")
    if not isinstance(target, dict) or target.get("id", "").lower() != user:
        raise RuntimeError("The target must resolve to the requested existing user.")
    before = is_member(client, group, user)
    desired = action == "add"
    result = {
        "action": action, "tenant": tenant, "group": group, "user": user,
        "member_before": before, "change_needed": before != desired,
        "dry_run": not apply, "changed": False,
    }
    if not apply or before == desired:
        result["status"] = "planned" if before != desired else "already_in_desired_state"
        return result
    if desired:
        client.request("POST", f"{GRAPH}/groups/{group}/members/$ref",
                       {"@odata.id": f"{GRAPH}/directoryObjects/{user}"})
    else:
        # $ref is essential: remove the relationship, never the directory object.
        client.request("DELETE", f"{GRAPH}/groups/{group}/members/{user}/$ref")
    after = is_member(client, group, user)
    if after != desired:
        raise RuntimeError("Graph accepted the change but read-back did not confirm it. Inspect membership before retrying; replication may be delayed.")
    result.update(changed=True, member_after=after, status="verified")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("tenant", "group", "user"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--action", required=True, choices=["add", "remove"])
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-group")
    args = parser.parse_args()
    try:
        result = reconcile(AzureCLI(), args.tenant, args.group, args.user,
                           args.action, args.apply, args.confirm_group)
    except (ValueError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
