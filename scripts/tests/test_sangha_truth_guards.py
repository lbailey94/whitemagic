"""Regression tests for honest Sangha execution and launcher boundaries."""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SANGHA_PATH = REPO_ROOT / "scripts" / "sangha.py"
WM_RS = REPO_ROOT / "crates" / "wm-gen3-harness" / "src" / "bin" / "wm.rs"
INSTALL_SH = REPO_ROOT / "scripts" / "install.sh"


def load_sangha():
    spec = importlib.util.spec_from_file_location("sangha_under_test", SANGHA_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class SanghaTruthGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sangha-truth-guard-")
        self.root = Path(self.temp.name)
        os.environ["SANGHA_ROOT"] = str(self.root)
        self.sangha = load_sangha()
        self.sangha.ROOT = self.root
        self.sangha.BOARD = self.root / "board"
        self.sangha.SANGHA_DIR = self.root / ".sangha"
        self.sangha.RECEIPTS_DIR = self.root / ".sangha" / "receipts"
        self.sangha.CREDIT_LEDGER_FILE = self.root / ".sangha" / "credit_ledger.jsonl"

    def tearDown(self):
        os.environ.pop("SANGHA_ROOT", None)
        self.temp.cleanup()

    def test_fabricated_receipt_cannot_mint_credits(self):
        self.sangha.RECEIPTS_DIR.mkdir(parents=True)
        (self.sangha.RECEIPTS_DIR / "0001.json").write_text(
            json.dumps({"receipt_id": "made-up", "seq": 1, "type": "delivery.attestation",
                        "issuer": {"id": "agent-a"}}),
            encoding="utf-8",
        )
        args = SimpleNamespace(credit_action="claim", agent="agent-a", json=True, seq=None, all=False)
        with mock.patch.object(self.sangha, "append_credit_tx") as append_tx:
            with mock.patch("sys.stdout") as stdout:
                result = self.sangha.cmd_credit(args)
        append_tx.assert_not_called()
        self.assertEqual(result, 2)
        self.assertFalse(self.sangha.CREDIT_LEDGER_FILE.exists())
        output = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertIn('"status": "unqualified"', output)
        self.assertIn('"claimed": 0', output)

    def test_worker_cannot_claim_report_or_complete_task(self):
        args = SimpleNamespace(room="research", agent="agent-a", daemon=False,
                               interval=1, max_tasks=1, dry_run=False, json=True)
        with mock.patch.object(self.sangha, "cmd_claim") as claim, \
             mock.patch.object(self.sangha, "issue_mandala_pass") as issue_pass, \
             mock.patch.object(self.sangha, "cmd_post") as post, \
             mock.patch.object(self.sangha, "cmd_release") as release, \
             mock.patch("sys.stdout") as stdout:
            result = self.sangha.cmd_worker(args)
        claim.assert_not_called()
        issue_pass.assert_not_called()
        post.assert_not_called()
        release.assert_not_called()
        self.assertEqual(result, 2)
        output = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertIn('"executed": false', output)
        self.assertIn('"status": "unavailable"', output)

    def test_dry_run_is_a_preview_and_never_posts_completion(self):
        args = SimpleNamespace(room="research", agent="agent-a", daemon=False,
                               interval=1, max_tasks=1, dry_run=True, json=False)
        with mock.patch.object(self.sangha, "find_open_tasks", return_value=[
            {"seq": 4, "title": "Review", "scope": "review"}
        ]), mock.patch.object(self.sangha, "cmd_post") as post, mock.patch("builtins.print") as output:
            result = self.sangha.cmd_worker(args)
        post.assert_not_called()
        self.assertEqual(result, 0)
        self.assertTrue(any("NON-EXECUTING" in str(call) for call in output.call_args_list))

    def test_daemon_mode_refuses_background_polling(self):
        args = SimpleNamespace(room="research", agent="agent-a", daemon=True,
                               interval=1, max_tasks=1, dry_run=True, json=True)
        with mock.patch.object(self.sangha, "find_open_tasks") as find_tasks, \
             mock.patch("sys.stdout") as stdout:
            result = self.sangha.cmd_worker(args)
        find_tasks.assert_not_called()
        self.assertEqual(result, 2)
        output = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertIn('"executed": false', output)
        self.assertIn("Background worker mode is unavailable", output)

    def test_launcher_does_not_redispatch_to_its_own_path_wrapper(self):
        source = WM_RS.read_text(encoding="utf-8")
        installer = INSTALL_SH.read_text(encoding="utf-8")
        self.assertNotIn('Command::new("sangha")', source)
        self.assertIn('WHITEMAGIC_SANGHA_SCRIPT', source)
        self.assertIn('exec "$(dirname "$0")/wm" sangha "$@"', installer)
        self.assertNotIn("/home/lucas/SharedWorkspace/sangha.py", source)
        self.assertNotIn("/home/lucas/Desktop/front burner/WHITEMAGIC/worktrees/continuity-receipt", source)
        self.assertIn("WHITEMAGIC_CPR_ROOT", source)


if __name__ == "__main__":
    unittest.main()
