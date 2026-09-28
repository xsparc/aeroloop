import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop.contracts import ValidationError
from aeroloop.evidence import read_run, validate_config
from aeroloop.live import FlightClock, validate_snapshot
from aeroloop.observation import make_observations, validate_capture
from aeroloop.outage_study import PROFILES, read_study, recovery_windows, summarize
from aeroloop.physics import State
from aeroloop.simulation import record
from aeroloop.timing_observation import OUTAGE_DURATIONS, configuration, source_sequence
from aeroloop.timing_study import capture_metrics
from test_observation import fixture


class OutageStudyTests(unittest.TestCase):
    def test_long_outages_hold_truth_and_resume_at_exact_capture_boundary(self):
        for profile, duration in OUTAGE_DURATIONS.items():
            model, samples, last = make_observations(profile, 73), [], 0
            for i in range(10001):
                t = round(i*.005,9)
                truth = State(position=(i,0,1), velocity=(0,i,0))
                feedback, observed = model.capture(truth)
                if i%4 == 0 and not (18 <= t < 18+duration or 40 <= t < 40+duration):
                    last = i
                self.assertEqual(source_sequence(i,profile), last)
                self.assertEqual(observed["source_sequence"], last)
                self.assertEqual(feedback.position, (last,0,1))
                validate_capture(observed, {**observed,"position_m":(last,0,1),"velocity_m_s":(0,last,0)}, i)
                samples.append(dict(sequence=i,time_s=t,position_m=truth.position,velocity_m_s=truth.velocity,observation=observed))
            metrics = capture_metrics(samples, configuration(profile)["dropout_windows_s"])
            self.assertEqual(metrics["captures"],2501-round(duration/.02)*2)
            self.assertEqual(metrics["max_age_s"],duration+.015)
            self.assertEqual(metrics["windows"][0]["first_capture_after_s"],18+duration)
            self.assertEqual(metrics["windows"][1]["first_capture_after_s"],40+duration)
            self.assertEqual(make_observations(profile,73).capture(State())[1]["source_sequence"],0)

    def test_versioned_evidence_and_live_reject_wrong_duration(self):
        profile = "hold-dropout-2000ms"
        with tempfile.TemporaryDirectory() as directory:
            run = read_run(record(fixture(profile),directory))
            self.assertEqual(run["manifest.json"]["schema_version"],7)
            changed = copy.deepcopy(run["config.json"])
            changed["observation_model"]["dropout_windows_s"][0][1] = 18.25
            with self.assertRaises(ValidationError): validate_config(changed,run["manifest.json"])
        model = make_observations(profile,73)
        for _ in range(8201): _,o = model.capture(State())
        sample = fixture(profile)["samples"][-1]
        sample.update(sequence=8200,time_s=41.,observation=o)
        packet = FlightClock().snapshot(73,.005,sample,observation_profile=profile)
        validate_snapshot(packet)
        self.assertEqual(packet["sample"]["observation"]["age_s"],1.02)
        for mutate in (lambda p:p.update(schema_version=2),
                       lambda p:p.update(observation_profile="hold-dropout-500ms"),
                       lambda p:p["sample"]["observation"].update(source_sequence=8200)):
            bad=copy.deepcopy(packet);mutate(bad)
            with self.assertRaises(ValidationError):validate_snapshot(bad)

    def test_settled_recovery_rejects_transient_dwell_and_preserves_late_or_missing_return(self):
        profile = "hold-dropout-2000ms"
        windows = configuration(profile)["dropout_windows_s"]
        model = make_observations(profile,0)
        reference = [dict(time_s=round(i*.005,9),sequence=i,position_m=(0,0,0),observation=model.capture(State())[1]) for i in range(10001)]
        candidate = copy.deepcopy(reference)
        # A >1 s in-band period followed by another excursion is not settled.
        candidate[4200]["position_m"]=(.06,0,0)  # 21 s, window ends at 20.
        candidate[5000]["position_m"]=(.06,0,0)  # 25 s, beyond deadline after this sample.
        rows = recovery_windows(reference,candidate,windows)
        self.assertEqual(rows[0]["recovery_time_s"],5.005)
        self.assertFalse(rows[0]["passed"])
        self.assertTrue(rows[0]["excursion_observed"])
        self.assertEqual(rows[0]["post_outage_samples_above_band"],2)
        self.assertEqual(rows[0]["first_resumed_capture_s"],20.)
        candidate[5000]["position_m"]=(.05,0,0)
        candidate[4999]["position_m"]=(.06,0,0)
        self.assertEqual(recovery_windows(reference,candidate,windows)[0]["recovery_time_s"],5.)
        self.assertTrue(recovery_windows(reference,candidate,windows)[0]["passed"])
        for end in (3900,7999,9900):
            rows = recovery_windows(reference[:end],candidate[:end],windows)
            self.assertIsNone(rows[-1]["recovery_time_s"])
            self.assertFalse(rows[-1]["passed"])
        # Last 1 s is required in full, including both endpoint samples.
        candidate[9800]["position_m"]=(.06,0,0)
        self.assertIsNone(recovery_windows(reference,candidate,windows)[1]["recovery_time_s"])
        candidate[9800]["position_m"]=(0,0,0)
        candidate[9799]["position_m"]=(.06,0,0)
        self.assertEqual(recovery_windows(reference,candidate,windows)[1]["recovery_time_s"],7.)
        # An excursion inside the outage followed by no post-outage error returns at zero.
        clean=copy.deepcopy(reference);clean[3800]["position_m"]=(.06,0,0)
        row=recovery_windows(reference,clean,windows)[0]
        self.assertTrue(row["excursion_observed"]);self.assertEqual(row["recovery_time_s"],0.)
        self.assertFalse(recovery_windows(reference,reference,windows)[0]["excursion_observed"])

    def test_matrix_requires_all_seeds_pacing_and_shared_source_while_retaining_failures(self):
        base=fixture("sample-hold");runs={};clocks={}
        for profile in PROFILES:
            for seed in range(3):
                run={k+".json":copy.deepcopy(base[k]) for k in ("config","samples","metrics","events")}
                run["config.json"].update(seed=seed,observation_model=configuration(profile))
                run["manifest.json"]=dict(schema_version=7,seed=seed,source_dirty=False,source_commit="a"*40,
                    source_tree_sha256="b"*64,controller_binary_sha256="c"*64,lock_sha256="d"*64,
                    config_sha256="e"*64,status="failed",failure_reason="wind_mission_threshold")
                runs[(profile,seed)]=run
                clocks[(profile,seed)]=dict(paced=True,elapsed_s=3.,simulation_s=2.045,max_lag_s=1.,late_steps=1,monitor_enabled=True)
        def worker(directory,result):return [runs[(str(directory),s)] for s in range(3)]
        def result(path):return {"results":[{"timing":clocks[(path.parent.name,s)]} for s in range(3)]}
        with patch("aeroloop.timing_study.validate_flight_result",side_effect=worker),patch("aeroloop.timing_study.load_json",side_effect=result):
            summary=summarize(*read_study(PROFILES))
            self.assertFalse(summary["accepted"]);self.assertFalse(summary["complete"])
            self.assertEqual(summary["trials"],15);self.assertEqual(summary["passed"],0)
            self.assertEqual(len(summary["comparisons"]),12)
            self.assertTrue(all(r["reason"]=="incomplete_pair" and not r["recovery_passed"] for r in summary["comparisons"]))
            self.assertTrue(all(r["recovery_passes"]==0 for r in summary["duration_results"]))
            for paths in (PROFILES[:4], [*PROFILES[:4],PROFILES[0]]):
                with self.assertRaises(ValidationError):read_study(paths)
            clocks[(PROFILES[0],0)]["paced"]=False
            with self.assertRaises(ValidationError):read_study(PROFILES)
            clocks[(PROFILES[0],0)]["paced"]=True
        runs[(PROFILES[-1],2)]["manifest.json"]["source_commit"]="f"*40
        with self.assertRaises(ValidationError):summarize(runs,clocks)
