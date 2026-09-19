from pathlib import Path
import json
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aeroloop.contracts import ValidationError
from aeroloop.evidence import export_bundle, read_run
from aeroloop.simulation import encoded, record, sha256, simulate


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cache = tempfile.TemporaryDirectory()
        cls.source = record(simulate(duration=6), Path(cls.cache.name))

    @classmethod
    def tearDownClass(cls):
        cls.cache.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.run = self.root / "run"
        shutil.copytree(self.source, self.run)

    def tearDown(self):
        self.temp.cleanup()

    def mutate(self, name, change):
        path = self.run / name
        value = json.loads(path.read_bytes())
        change(value)
        path.write_bytes(encoded(value))
        checksums = json.loads((self.run / "checksums.json").read_bytes())
        checksums[name] = sha256(path.read_bytes())
        (self.run / "checksums.json").write_bytes(encoded(checksums))

    def test_export_and_verify_genuine_computed_recording(self):
        read_run(self.run)
        result = export_bundle([self.run], self.root / "public")
        self.assertEqual(result["release_status"], "research_preview")
        self.assertFalse(result["isaac_validated"])
        for name, checksum in result["checksums"].items():
            self.assertEqual(sha256((self.root / "public" / name).read_bytes()), checksum)

    def test_export_keeps_full_resolution_and_downsamples_replay(self):
        result = export_bundle([self.run], self.root / "public")
        directory = self.root / "public" / result["runs"][0]["run_id"]
        full = json.loads((directory / "samples.json").read_bytes())
        replay = json.loads((directory / "replay.json").read_bytes())["samples"]
        self.assertEqual(len(full), 1201)
        self.assertEqual(len(replay), 121)
        self.assertEqual(replay[-1]["time_s"], full[-1]["time_s"])

    def test_checksum_tamper_rejected(self):
        with (self.run / "samples.json").open("ab") as stream:
            stream.write(b" ")
        with self.assertRaises(ValidationError):
            read_run(self.run)

    def test_forged_metric_rejected_even_with_updated_checksum(self):
        self.mutate("metrics.json", lambda m: m.update(position_rmse_m=0))
        with self.assertRaises(ValidationError):
            read_run(self.run)

    def test_fixture_rejected_before_any_output(self):
        self.mutate("manifest.json", lambda m: m.update(fixture=True))
        with self.assertRaises(ValidationError):
            export_bundle([self.run], self.root / "public")
        self.assertFalse((self.root / "public").exists())

    def test_unknown_private_metadata_rejected(self):
        self.mutate("manifest.json", lambda m: m.update(private_note="not-for-publication"))
        with self.assertRaises(ValidationError):
            read_run(self.run)

    def test_traversal_identifier_rejected(self):
        self.mutate("manifest.json", lambda m: m.update(run_id="../private"))
        with self.assertRaises(ValidationError):
            read_run(self.run)

    def test_missing_frame_rejected(self):
        self.mutate("manifest.json", lambda m: m.pop("world_frame"))
        with self.assertRaises(ValidationError):
            read_run(self.run)

    def test_truncated_recording_rejected(self):
        self.mutate("samples.json", lambda s: s.pop())
        with self.assertRaises(ValidationError):
            read_run(self.run)

    def test_backwards_time_and_nonunit_quaternion_rejected(self):
        self.mutate("samples.json", lambda s: s[1].update(time_s=0))
        with self.assertRaises(ValidationError):
            read_run(self.run)
        shutil.copyfile(self.source / "samples.json", self.run / "samples.json")
        self.mutate("samples.json", lambda s: s[0].update(quaternion_wxyz=[0,0,0,0]))
        with self.assertRaises(ValidationError):
            read_run(self.run)

    def test_existing_output_is_not_overwritten(self):
        output = self.root / "existing"
        output.mkdir()
        (output / "keep").write_text("retain")
        with self.assertRaises(ValidationError):
            export_bundle([self.run], output)
        self.assertEqual((output / "keep").read_text(), "retain")

    def test_failed_trials_remain_publishable(self):
        failed = record(simulate("lateral-force-pulse", duration=6), self.root)
        result = export_bundle([failed], self.root / "public")
        self.assertEqual(result["runs"][0]["status"], "failed")

    def test_config_content_and_manifest_hash_must_agree(self):
        self.mutate("config.json", lambda c: c.update(position_kp=123))
        with self.assertRaises(ValidationError):
            read_run(self.run)
