import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "whitemagic-sentinel-reflex.sh"

STORE_START = 1792670400  # 2026-10-22T12:00:00Z, fixed for deterministic cooldowns


class SentinelReflexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.store = self.root / "store"
        self.bin.mkdir()
        self.store.mkdir()
        self.capture = self.root / "posted.json"
        self.lane = self.root / "lane-health"
        self.shim = self.root / "gateway-readiness"
        self.restart_capture = self.root / "restarts.txt"
        self.lane.write_text("fail")
        self.shim.write_text("success")
        self._tool("wm", '''#!/bin/sh
if [ "${3-}" = sentinel ] && [ "${5-}" = --json ]; then
  printf '{"status":"%s"}\\n' "${WM_TEST_STATUS:-warning}"
elif [ "${3-}" = sentinel ] && [ "${5-}" = --prompt ]; then
  printf '%s\\n' "- **Status**: **${WM_TEST_STATUS:-warning}**" 'No active anomalies detected. System invariants verified.'
else
  exit 2
fi
''')
        # Backend health and gateway discovery are independent signals.
        self._tool("curl", '''#!/bin/sh
case "$*" in
  *8787/api/post*)
    if [ "${WM_TEST_POST_FAIL:-0}" = 1 ]; then exit 22; fi
    while [ "$#" -gt 0 ]; do
      if [ "$1" = -d ]; then shift; printf '%s' "$1" > "$WM_TEST_CAPTURE"; break; fi
      shift
    done
    printf '{"ok":true}'
    exit 0
    ;;
  *8787/api/status*) exit 0 ;;
  *18789/health*)
    if [ "$(cat "$WM_TEST_LANE")" = success ]; then exit 0; else exit 22; fi
    ;;
  *18797/ready*)
    if [ "$(cat "$WM_TEST_SHIM")" = success ]; then exit 0; else exit 22; fi
    ;;
esac
exit 1
''')
        self._tool("sudo", '''#!/bin/sh
printf '%s\\n' "$*" >> "$WM_TEST_RESTART_CAPTURE"
exit 0
''')
        self._tool("date", '''#!/bin/sh
case "$*" in
  +%s) printf '%s\\n' "$WM_TEST_NOW" ;;
  "-u +%H") printf '12\\n' ;;
  "-u +%F") printf '2026-10-22\\n' ;;
  "-u +%FT%TZ") printf '2026-10-22T12:00:00Z\\n' ;;
  *) /bin/date "$@" ;;
esac
''')
        self.env = os.environ.copy()
        self.env.update({
            "PATH": f"{self.bin}:{self.env['PATH']}",
            "WM_BIN": str(self.bin / "wm"),
            "WM_STORE": str(self.store),
            "WM_NODE_ID": "test-vps",
            "WM_WATCHDOG_ENABLED": "1",
            "WM_TEST_LANE": str(self.lane),
            "WM_TEST_SHIM": str(self.shim),
            "WM_TEST_RESTART_CAPTURE": str(self.restart_capture),
            "WM_TEST_CAPTURE": str(self.capture),
            "WM_TEST_NOW": str(STORE_START),
            "WM_TEST_STATUS": "warning",
        })

    def tearDown(self):
        self.temp.cleanup()

    def _tool(self, name, source):
        path = self.bin / name
        path.write_text(source)
        path.chmod(0o755)

    def run_reflex(self, now=None):
        if now is not None:
            self.env["WM_TEST_NOW"] = str(now)
        return subprocess.run([str(SCRIPT)], env=self.env, text=True,
                              capture_output=True, check=False)

    def state(self):
        return json.loads((self.store / "watchdog-circuit.json").read_text())

    # ── recovery ──────────────────────────────────────────────────────────
    def test_healthy_probe_clears_only_recovered_service(self):
        (self.store / "watchdog-circuit.json").write_text(json.dumps({
            "whitemagic-hosted.service": {"failures": 8, "last_trip": STORE_START - 100},
            "other.service": {"failures": 2, "last_trip": STORE_START - 100},
        }))
        self.lane.write_text("success")

        result = self.run_reflex()

        self.assertEqual(result.returncode, 0, result.stderr)
        actual = self.state()
        self.assertNotIn("whitemagic-hosted.service", actual)
        self.assertEqual(actual["other.service"]["failures"], 2)
        self.assertFalse(self.capture.exists())

    # ── defect 1: title/body must never disagree ──────────────────────────
    def test_title_and_body_share_one_severity_when_only_watchdog_trips(self):
        for offset in range(4):
            self.run_reflex(now=STORE_START + offset)

        payload = json.loads(self.capture.read_text())
        self.assertIn("is critical", payload["title"])
        # The body must explain *why* it is critical, not contradict itself.
        self.assertIn("**Alert severity**: **critical**", payload["body"])
        self.assertIn("**System report status**: **warning**", payload["body"])
        self.assertIn("circuit open for whitemagic-hosted.service", payload["body"])
        self.assertIn("http://127.0.0.1:18789/health", payload["body"])
        # ...and it must be provenance-marked so lint stays clean.
        self.assertEqual(payload["provenance"], "computed")

    # ── defect 2: cooldown must actually hold ─────────────────────────────
    def test_unchanged_condition_alerts_once_then_cooldown(self):
        # Seed the streak one failure short of tripping so the alert lands exactly
        # at STORE_START; the cooldown clock is then unambiguous.
        (self.store / "watchdog-circuit.json").write_text(json.dumps({
            "whitemagic-hosted.service": {
                "failures": 3, "first_seen": STORE_START - 300, "last_trip": STORE_START - 1,
            }
        }))
        self.run_reflex(now=STORE_START)
        self.assertTrue(self.capture.exists())
        first = json.loads(self.capture.read_text())
        self.capture.unlink()

        suppressed = self.run_reflex(now=STORE_START + 60)
        self.assertFalse(self.capture.exists())
        self.assertIn("15-minute cooldown", suppressed.stdout)

        self.run_reflex(now=STORE_START + 899)
        self.assertFalse(self.capture.exists())

        self.run_reflex(now=STORE_START + 900)
        self.assertTrue(self.capture.exists())
        self.assertEqual(json.loads(self.capture.read_text())["title"], first["title"])

    def test_storm_of_runs_yields_exactly_one_alert(self):
        # The 2026-10-22 incident posted 15 alerts in 15 minutes. Simulate 15
        # consecutive failing runs and require exactly one delivery.
        posted = 0
        for offset in range(15):
            if self.capture.exists():
                self.capture.unlink()
            self.run_reflex(now=STORE_START + offset * 60)
            if self.capture.exists():
                posted += 1
        self.assertEqual(posted, 1)

    def test_report_critical_does_not_bypass_cooldown(self):
        # Regression: suppression used to require the *report* to be nominal or
        # warning, so a critical report re-alerted every minute forever.
        (self.store / "watchdog-circuit.json").write_text(json.dumps({
            "whitemagic-hosted.service": {
                "failures": 3, "first_seen": STORE_START - 300, "last_trip": STORE_START - 1,
            }
        }))
        self.env["WM_TEST_STATUS"] = "critical"
        posted = 0
        for offset in range(6):
            if self.capture.exists():
                self.capture.unlink()
            self.run_reflex(now=STORE_START + offset * 60)
            if self.capture.exists():
                posted += 1
        self.assertEqual(posted, 1)

    def test_changed_condition_alerts_immediately(self):
        for offset in range(4):
            self.run_reflex(now=STORE_START + offset)
        self.assertTrue(self.capture.exists())
        self.capture.unlink()

        self.env["WM_TEST_STATUS"] = "critical"
        self.run_reflex(now=STORE_START + 30)
        self.assertTrue(self.capture.exists(), "severity escalation must not wait out the cooldown")

    def test_new_gateway_failure_escalates_existing_backend_condition(self):
        self.lane.write_text("fail")
        self.shim.write_text("success")
        for offset in range(4):
            self.run_reflex(now=STORE_START + offset)
        self.assertTrue(self.capture.exists())
        self.capture.unlink()

        self.shim.write_text("fail")
        for offset in range(4, 8):
            result = self.run_reflex(now=STORE_START + offset)
        self.assertTrue(self.capture.exists(), "a newly open gateway condition must bypass prior backend cooldown")
        payload = json.loads(self.capture.read_text())
        self.assertIn("whitemagic-hosted.service", payload["body"])
        self.assertIn("whitemagic-gateway.service", payload["body"])
        self.assertIn("authd tools/list discovery failed", payload["body"])
        restarts = self.restart_capture.read_text() if self.restart_capture.exists() else ""
        self.assertNotIn("whitemagic-gateway.service", restarts, "gateway-only failure must not restart the gateway")

    # ── defect 3: probe what customers use ────────────────────────────────
    def test_served_lane_is_what_pages(self):
        self.lane.write_text("fail")
        self.shim.write_text("success")
        for offset in range(4):
            self.run_reflex(now=STORE_START + offset)
        self.assertTrue(self.capture.exists())
        payload = json.loads(self.capture.read_text())
        self.assertIn("18789/health", payload["body"])

    def test_gateway_discovery_failure_pages_without_restarting_backend(self):
        self.lane.write_text("success")
        self.shim.write_text("fail")
        posted = 0
        first_payload = None
        for offset in range(12):
            if self.capture.exists():
                self.capture.unlink()
            result = self.run_reflex(now=STORE_START + offset * 60)
            if self.capture.exists():
                posted += 1
                if first_payload is None:
                    first_payload = json.loads(self.capture.read_text())
        self.assertEqual(posted, 1, "persistent gateway discovery failure should page once in the cooldown")
        payload = first_payload
        self.assertIn("whitemagic-gateway.service", payload["body"])
        self.assertIn("18797/ready?fresh=1", payload["body"])
        self.assertIn("authd tools/list discovery failed", payload["body"])
        self.assertIn("no automatic restart was attempted", payload["body"])
        self.assertFalse(self.restart_capture.exists(), "gateway-only failure must not restart backend")

    def test_gateway_recovery_rearms_new_failure_generation(self):
        self.lane.write_text("success")
        self.shim.write_text("fail")
        for offset in range(4):
            self.run_reflex(now=STORE_START + offset * 60)
        self.assertTrue(self.capture.exists())
        self.capture.unlink()

        self.shim.write_text("success")
        self.run_reflex(now=STORE_START + 300)
        self.assertNotIn("whitemagic-gateway.service", self.state())
        self.assertFalse(self.capture.exists())

        self.shim.write_text("fail")
        for offset in range(5, 9):
            self.run_reflex(now=STORE_START + offset * 60)
        self.assertTrue(self.capture.exists(), "recovery followed by a new outage must rearm notification")
        self.assertFalse(self.restart_capture.exists(), "gateway-only failure must not restart backend")

    def test_gateway_delivery_failure_retries_without_cooldown(self):
        self.lane.write_text("success")
        self.shim.write_text("fail")
        self.env["WM_TEST_POST_FAIL"] = "1"
        for offset in range(4):
            self.run_reflex(now=STORE_START + offset * 60)
        self.assertFalse(self.capture.exists())
        self.assertNotIn("_cooldown", self.state())

        self.env.pop("WM_TEST_POST_FAIL")
        retried = self.run_reflex(now=STORE_START + 240)
        self.assertEqual(retried.returncode, 0, retried.stderr)
        self.assertTrue(self.capture.exists())
        self.assertFalse(self.restart_capture.exists())

    def test_fresh_critical_report_creates_delivered_cooldown_atomically(self):
        self.lane.write_text("success")
        self.shim.write_text("success")
        self.env["WM_TEST_STATUS"] = "critical"
        first = self.run_reflex(now=STORE_START)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertTrue(self.capture.exists())
        self.assertEqual(self.state()["_cooldown"]["report=critical;watchdog=none"], STORE_START)

        self.capture.unlink()
        repeated = self.run_reflex(now=STORE_START + 60)
        self.assertFalse(self.capture.exists())
        self.assertIn("15-minute cooldown", repeated.stdout)
        self.assertEqual(self.state()["_cooldown"]["report=critical;watchdog=none"], STORE_START)

        expired = self.run_reflex(now=STORE_START + 900)
        self.assertEqual(expired.returncode, 0, expired.stderr)
        self.assertTrue(self.capture.exists())

    # ── delivery + streak bookkeeping ─────────────────────────────────────
    def test_delivery_failure_does_not_start_cooldown(self):
        self.env["WM_TEST_POST_FAIL"] = "1"
        for offset in range(4):
            self.run_reflex(now=STORE_START + offset)
        self.assertFalse(self.capture.exists())
        self.assertNotIn("_cooldown", self.state())

        self.env.pop("WM_TEST_POST_FAIL")
        self.capture.unlink(missing_ok=True)
        retried = self.run_reflex(now=STORE_START + 30)
        self.assertEqual(retried.returncode, 0, retried.stderr)
        self.assertTrue(self.capture.exists())

    def test_recovered_probe_resets_streak_before_next_outage(self):
        for offset in range(4):
            self.run_reflex(now=STORE_START + offset)
        self.assertTrue(self.capture.exists())

        self.lane.write_text("success")
        self.run_reflex(now=STORE_START + 100)
        self.assertNotIn("whitemagic-hosted.service", self.state())

        self.capture.unlink()
        self.lane.write_text("fail")
        first_failure = self.run_reflex(now=STORE_START + 200)
        self.assertEqual(self.state()["whitemagic-hosted.service"]["failures"], 1)
        self.assertNotIn("is critical", first_failure.stdout)


if __name__ == "__main__":
    unittest.main()
