import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "identity"))
from group_membership import GRAPH, is_member, reconcile

TENANT = "11111111-1111-1111-1111-111111111111"
GROUP = "22222222-2222-2222-2222-222222222222"
USER = "33333333-3333-3333-3333-333333333333"


class FakeGraph:
    def __init__(self, member=False):
        self.member = member
        self.calls = []
        self.group = {"securityEnabled": True, "isAssignableToRole": False, "groupTypes": []}
        self.fail_write = False
        self.ignore_write = False

    def tenant(self):
        return TENANT

    def request(self, method, url, body=None):
        self.calls.append((method, url, body))
        if method != "GET":
            if self.fail_write:
                raise RuntimeError("Graph rejected operation")
            if not self.ignore_write:
                self.member = method == "POST"
            return None
        if "/members?" in url:
            return {"value": [{"id": USER}] if self.member else []}
        if "/users/" in url:
            return {"id": USER}
        return self.group


class MembershipTests(unittest.TestCase):
    def test_default_dry_run_never_writes(self):
        for action, before in [("add", False), ("remove", True)]:
            client = FakeGraph(before)
            result = reconcile(client, TENANT, GROUP, USER, action)
            self.assertTrue(result["dry_run"])
            self.assertTrue(result["change_needed"])
            self.assertFalse(result["changed"])
            self.assertTrue(all(call[0] == "GET" for call in client.calls))

    def test_add_and_remove_verify_and_are_idempotent(self):
        client = FakeGraph()
        for action, expected in [("add", True), ("remove", False)]:
            result = reconcile(client, TENANT, GROUP, USER, action, True, GROUP)
            self.assertEqual(result["member_after"], expected)
            self.assertEqual(result["status"], "verified")
            client.calls.clear()
            result = reconcile(client, TENANT, GROUP, USER, action, True, GROUP)
            self.assertFalse(result["changed"])
            self.assertTrue(all(call[0] == "GET" for call in client.calls))

    def test_remove_targets_reference_not_user(self):
        client = FakeGraph(True)
        reconcile(client, TENANT, GROUP, USER, "remove", True, GROUP)
        writes = [call for call in client.calls if call[0] != "GET"]
        self.assertEqual(writes, [("DELETE", f"{GRAPH}/groups/{GROUP}/members/{USER}/$ref", None)])

    def test_privileged_dynamic_and_unknown_groups_are_rejected(self):
        for metadata in [
            {"securityEnabled": True, "isAssignableToRole": True, "groupTypes": []},
            {"securityEnabled": True, "isAssignableToRole": False, "groupTypes": ["DynamicMembership"]},
            {"securityEnabled": True, "groupTypes": []},
        ]:
            client = FakeGraph()
            client.group = metadata
            with self.assertRaises(RuntimeError):
                reconcile(client, TENANT, GROUP, USER, "add", True, GROUP)
            self.assertTrue(all(call[0] == "GET" for call in client.calls))

    def test_wrong_tenant_and_confirmation_fail_before_write(self):
        client = FakeGraph()
        with self.assertRaises(RuntimeError):
            reconcile(client, GROUP, GROUP, USER, "add", True, GROUP)
        with self.assertRaises(ValueError):
            reconcile(client, TENANT, GROUP, USER, "add", True)
        self.assertEqual(client.calls, [])

    def test_invalid_ids_and_actions_are_rejected(self):
        for args in [
            (TENANT, "not-a-uuid", USER, "add"),
            (TENANT, GROUP, USER, "delete-user"),
        ]:
            with self.assertRaises(ValueError):
                reconcile(FakeGraph(), *args)

    def test_write_failures_and_unconfirmed_readback_are_errors(self):
        for failure in ("fail_write", "ignore_write"):
            client = FakeGraph()
            setattr(client, failure, True)
            with self.assertRaises(RuntimeError):
                reconcile(client, TENANT, GROUP, USER, "add", True, GROUP)

    def test_membership_pagination(self):
        class PagedGraph:
            def request(self, method, url):
                if "$skiptoken" in url:
                    return {"value": [{"id": USER}]}
                return {"value": [], "@odata.nextLink": f"{GRAPH}/groups/{GROUP}/members?$skiptoken=next"}
        self.assertTrue(is_member(PagedGraph(), GROUP, USER))

    def test_missing_membership_data_does_not_mean_absent(self):
        class InvalidGraph:
            def request(self, method, url):
                return {"error": "insufficient permissions"}
        with self.assertRaises(RuntimeError):
            is_member(InvalidGraph(), GROUP, USER)


if __name__ == "__main__":
    unittest.main()
