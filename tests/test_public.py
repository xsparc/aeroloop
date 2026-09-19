import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("check_public", Path(__file__).resolve().parents[1] / "tools/check_public.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PublicSourceTests(unittest.TestCase):
    def test_detects_contact_without_echoing_value(self):
        value = "private" + "@" + "example.invalid"
        self.assertEqual(module.scan(value), ["contact email"])

    def test_allows_verified_noreply_format(self):
        self.assertEqual(module.scan("123+account" + "@users.noreply.github.com"), [])

    def test_detects_home_path(self):
        self.assertIn("private user path", module.scan("C:" + "/Users/" + "someone/file.txt"))

    def test_detects_key_material(self):
        self.assertIn("private key", module.scan("-----BEGIN " + "PRIVATE KEY-----"))
