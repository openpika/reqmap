"""Functional CLI tests: no external dependencies."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reqmap.py"


class ReqmapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def cli(self, *parts, ok=True):
        p = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), *parts], text=True, capture_output=True)
        if ok:
            self.assertEqual(p.returncode, 0, p.stderr)
            return json.loads(p.stdout)
        self.assertNotEqual(p.returncode, 0)
        return p.stderr + p.stdout

    def init(self):
        self.cli("init", "--name", "测试商城", "--description", "数字商品交易")

    def add(self, title="微信登录", summary="允许微信账号登录商城", why="降低用户购买门槛"):
        return self.cli("add", "--title", title, "--summary", summary, "--why", why)

    def test_init_is_idempotent_for_agents_and_refuses_catalog_overwrite(self):
        self.root.joinpath("AGENTS.md").write_text("# Existing rules\n\nDo not delete this.\n")
        self.init()
        ag = self.root.joinpath("AGENTS.md").read_text()
        self.assertIn("Do not delete this", ag)
        self.assertEqual(ag.count("<!-- reqmap:start -->"), 1)
        self.assertIn(".reqmap/INDEX.md", ag)
        self.assertIn("Already initialized", self.cli("init", "--name", "Oops", ok=False))
        self.assertEqual(self.root.joinpath("AGENTS.md").read_text(), ag)

    def test_features_status_and_history(self):
        self.init()
        one = self.add()
        self.assertEqual(one["id"], "REQ-0001")
        self.assertEqual(one["status"], "defined")
        self.assertEqual(len(self.cli("list")), 1)
        self.assertIn("微信登录", self.root.joinpath(".reqmap/INDEX.md").read_text())
        self.assertIn("降低用户购买门槛", self.root.joinpath(".reqmap/features/REQ-0001.md").read_text())
        err = self.cli("status", "REQ-0001", "--to", "done", ok=False)
        self.assertIn("required", err)
        updated = self.cli("status", "REQ-0001", "--to", "done", "--user-confirmation", "我验收通过")
        self.assertEqual(updated["status"], "done")
        self.assertIn("我验收通过", self.root.joinpath(".reqmap/features/REQ-0001.md").read_text())
        self.assertTrue(any(e["action"] == "status_confirmed" for e in self.cli("history", "REQ-0001")))
        self.assertTrue(self.cli("check")["valid"])

    def test_relations_have_proposal_and_confirmation_gate(self):
        self.init()
        a = self.add()["id"]
        b = self.add("商品购买", "先登录后购买数字商品", "保障交易身份")["id"]
        self.cli("link", "--from", b, "--to", a, "--type", "depends_on", "--reason", "购买必须登录")
        impact = self.cli("impact", a)
        self.assertFalse(impact["hard_dependents"])
        self.assertEqual(impact["possible_impacts"][0]["other"], b)
        error = self.cli("review-link", "--from", b, "--to", a, "--type", "depends_on", "--to-state", "confirmed", ok=False)
        self.assertIn("required", error)
        self.cli("review-link", "--from", b, "--to", a, "--type", "depends_on", "--to-state", "confirmed", "--user-confirmation", "认可依赖关系")
        impact = self.cli("impact", a)
        self.assertEqual([i["id"] for i in impact["hard_dependents"]], [b])
        self.assertEqual(impact["possible_impacts"], [])
        self.assertTrue(self.cli("check")["valid"])

    def test_change_history_and_suggestion(self):
        self.init()
        self.add()
        suggestion = self.cli("suggest", "--title", "微信登录", "--summary", "允许微信账号登录")
        self.assertEqual(suggestion[0]["id"], "REQ-0001")
        f = self.cli("revise", "REQ-0001", "--summary", "微信登录必须验证用户身份", "--reason", "防止冒用身份")
        self.assertEqual(f["revision"], 2)
        entries = self.cli("history", "REQ-0001")
        revision = [e for e in entries if e["action"] == "feature_revised"][0]
        self.assertEqual(revision["reason"], "防止冒用身份")
        self.assertEqual(revision["before"]["revision"], 1)
        self.assertEqual(revision["after"]["revision"], 2)

    def test_duplicate_and_cycle_detection(self):
        self.init()
        self.add()
        self.assertIn("same title", self.cli("add", "--title", "微信登录", "--summary", "重复", "--why", "重复", ok=False))
        self.add("商品购买", "用户购买数字商品", "完成交易")
        for src, dst in [("REQ-0001", "REQ-0002"), ("REQ-0002", "REQ-0001")]:
            self.cli("link", "--from", src, "--to", dst, "--type", "depends_on", "--reason", "测试依赖", "--review", "confirmed", "--user-confirmation", "确认")
        result = self.cli("check", ok=False)
        self.assertIn("cycle", result)
        self.cli("review-link", "--from", "REQ-0002", "--to", "REQ-0001", "--type", "depends_on", "--to-state", "rejected", "--user-confirmation", "这条关系不成立")
        self.assertTrue(self.cli("check")["valid"])

    def test_missing_project_and_unknown_feature(self):
        self.assertIn("No project memory", self.cli("list", ok=False))
        self.init()
        self.assertIn("Unknown requirement", self.cli("show", "REQ-8888", ok=False))

    def test_product_files_are_portable(self):
        self.init()
        self.add()
        self.assertTrue(self.root.joinpath(".reqmap/catalog.json").exists())
        catalog = json.loads(self.root.joinpath(".reqmap/catalog.json").read_text())
        self.assertEqual(catalog["schema_version"], 1)
        self.assertEqual(catalog["next_id"], 2)
        self.cli("sync")
        self.assertTrue(self.cli("check")["valid"])


if __name__ == "__main__":
    unittest.main()
