import importlib.machinery
import importlib.util
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader("ohc", str(ROOT / "orgo-hermes-connect"))
spec = importlib.util.spec_from_loader("ohc", loader)
ohc = importlib.util.module_from_spec(spec)
loader.exec_module(ohc)


class LabelTests(unittest.TestCase):
    def test_sanitize_produces_valid_labels(self):
        cases = ["Hermes Agent", "orgo-desktop", "ab--cd", "12345678", "deadbeef", "x", "",
                 "Ünïcödé Bot!!", "a" * 80, "My   Agent__42", "--lead-trail--"]
        for raw in cases:
            for _ in range(5):
                lab = ohc.sanitize_label(raw)
                self.assertTrue(ohc.valid_label(lab), f"{raw!r} -> {lab!r}")

    def test_sanitize_keeps_name(self):
        self.assertTrue(ohc.sanitize_label("Hermes Agent", "ab12").startswith("hermes-agent-ab12"))

    def test_valid_label_rejects(self):
        for bad in ["ab", "AB-cd", "-abc", "abc-", "ab--cd", "12345", "deadbeef", "orgo-thing", "a_b_c"]:
            self.assertFalse(ohc.valid_label(bad), bad)


class EnvTests(unittest.TestCase):
    def test_upsert_preserves_and_replaces(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".env"
            p.write_text("# comment\nA=1\nexport B=2\nC=\"three\"\nA=dup\n")
            ohc.upsert_env({"A": "x", "B": None, "D": "4"}, p)
            text = p.read_text()
            self.assertIn("# comment", text)
            self.assertEqual(text.count("A="), 1)
            self.assertNotIn("B=", text)
            self.assertIn("D=4", text)
            self.assertEqual(oct(p.stat().st_mode & 0o777), "0o600")
            self.assertEqual(ohc.read_env(p), {"A": "x", "C": "three", "D": "4"})


class HashTests(unittest.TestCase):
    def test_hash_matches_hermes_basic_format_and_verifies(self):
        h = ohc.hash_password("pw")
        scheme, n, r, p, salt, dk = h.split("$")
        self.assertEqual((scheme, n, r, p), ("scrypt", "16384", "8", "1"))
        import base64, hashlib
        again = hashlib.scrypt(b"pw", salt=base64.b64decode(salt), n=16384, r=8, p=1, dklen=32, maxmem=0)
        self.assertEqual(base64.b64encode(again).decode(), dk)

    def test_hermes_verifier_accepts_hash_if_available(self):
        plugin = Path("/usr/local/lib/hermes-agent/plugins/dashboard_auth/basic/__init__.py")
        if not plugin.exists():
            self.skipTest("Hermes not installed here")
        src = plugin.read_text()
        m = re.search(r"def _verify_password\(.*?return hmac\.compare_digest\(actual, expected\)\n", src, re.S)
        if not m:
            self.skipTest("Hermes verifier shape changed")
        ns = {}
        exec("import base64, hashlib, hmac, secrets\n_SCRYPT_DKLEN=32\n" + m.group(0), ns)
        self.assertTrue(ns["_verify_password"]("pw", ohc.hash_password("pw")))
        self.assertFalse(ns["_verify_password"]("nope", ohc.hash_password("pw")))


class ParserTests(unittest.TestCase):
    def test_defaults(self):
        a = ohc.build_parser().parse_args(["up"])
        self.assertEqual((a.auth, a.port), ("nous", 9119))

    def test_reserved_port_rejected(self):
        self.assertEqual(ohc.main(["up", "--port", "8080"]), 1)


class DetectTests(unittest.TestCase):
    def test_detect_from_config_yaml(self):
        with tempfile.TemporaryDirectory() as d:
            old = ohc.HERMES_HOME
            try:
                ohc.HERMES_HOME = Path(d)
                (Path(d) / "config.yaml").write_text(
                    "mcp_servers:\n  orgo:\n    url: https://www.orgo.ai/mcp/computers/7f388be6-3ef7-4b95-9d3b-483ca746b4a0\n")
                env_backup = {k: os.environ.pop(k, None) for k in ("ORGO_COMPUTER_ID", "COMPUTER_ID")}
                old_env_file = ohc.ENV_FILE
                ohc.ENV_FILE = Path(d) / ".env"
                self.assertEqual(ohc.detect_computer_id("k", None), "7f388be6-3ef7-4b95-9d3b-483ca746b4a0")
            finally:
                ohc.HERMES_HOME = old
                ohc.ENV_FILE = old_env_file
                for k, v in env_backup.items():
                    if v is not None:
                        os.environ[k] = v

    def test_explicit_wins(self):
        self.assertEqual(ohc.detect_computer_id("k", "abc"), "abc")


class FakeRun:
    """Records supervisorctl calls; reports a configurable status."""
    def __init__(self, running=True):
        self.calls, self.running = [], running

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        out = ""
        if cmd[:2] == ["supervisorctl", "status"]:
            out = "hermes-serve  RUNNING  pid 1" if self.running else "hermes-serve  STOPPED"
        if cmd[:2] == ["supervisorctl", "start"]:
            self.running = True
        import subprocess
        return subprocess.CompletedProcess(cmd, 0, out, "")

    def did(self, verb):
        return any(c[:2] == ["supervisorctl", verb] for c in self.calls)


class BackendSafetyTests(unittest.TestCase):
    """The tool must never disrupt a live gateway it doesn't need to touch."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conf = Path(self.tmp.name) / "hermes-serve.conf"
        self.saved = (ohc.SUPERVISOR_CONF, ohc.run, ohc.service_kind)
        ohc.SUPERVISOR_CONF = self.conf
        ohc.service_kind = lambda: "supervisor"

    def tearDown(self):
        ohc.SUPERVISOR_CONF, ohc.run, ohc.service_kind = self.saved
        self.tmp.cleanup()

    def go(self, running=True, **kw):
        fake = FakeRun(running)
        ohc.run = fake
        kind, action = ohc.start_backend("/usr/local/bin/hermes", 9119, **{"restart": False, **kw})
        return fake, action

    def test_foreign_running_service_is_adopted_untouched(self):
        original = "[program:hermes-serve]\ncommand=hermes serve --host 0.0.0.0 --port 9119\n"
        self.conf.write_text(original)
        fake, action = self.go()
        self.assertEqual(action, "adopted")
        self.assertEqual(self.conf.read_text(), original)
        for verb in ("restart", "stop", "update", "reread", "start"):
            self.assertFalse(fake.did(verb), verb)

    def test_foreign_service_on_other_port_refuses(self):
        self.conf.write_text("[program:hermes-serve]\ncommand=hermes serve --port 9200\n")
        with self.assertRaises(ohc.Fail):
            self.go()

    def test_managed_unchanged_running_is_left_alone(self):
        self.conf.write_text(ohc.supervisor_conf("/usr/local/bin/hermes", 9119))
        fake, action = self.go()
        self.assertEqual(action, "unchanged")
        self.assertFalse(fake.did("restart") or fake.did("update"))

    def test_restart_only_when_settings_changed(self):
        self.conf.write_text(ohc.supervisor_conf("/usr/local/bin/hermes", 9119))
        fake, action = self.go(restart=True)
        self.assertEqual(action, "restarted")
        self.assertTrue(fake.did("restart"))

    def test_fresh_install_writes_and_starts(self):
        fake, action = self.go(running=False)
        self.assertIn(ohc.MANAGED_MARK, self.conf.read_text())
        self.assertEqual(action, "started")

    def test_force_takes_over_foreign(self):
        self.conf.write_text("[program:hermes-serve]\ncommand=old\n")
        fake, action = self.go(force=True)
        self.assertIn(ohc.MANAGED_MARK, self.conf.read_text())

    def test_down_refuses_foreign_without_force(self):
        self.conf.write_text("[program:hermes-serve]\ncommand=old\n")
        ohc.run = FakeRun()
        with self.assertRaises(ohc.Fail):
            ohc.stop_backend()
        self.assertTrue(self.conf.exists())


if __name__ == "__main__":
    unittest.main()
