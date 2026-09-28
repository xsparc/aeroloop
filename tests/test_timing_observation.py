import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from aeroloop.contracts import ValidationError
from aeroloop.evidence import read_run, replay_document, validate_config
from aeroloop.live import FlightClock, validate_snapshot
from aeroloop.observation import make_observations, validate_capture
from aeroloop.physics import State
from aeroloop.simulation import encoded, record, sha256
from aeroloop.timing_observation import PROFILES, TimingObservations, configuration, source_sequence
from aeroloop.timing_study import capture_metrics, read_study, recovery_windows, summarize
from test_observation import fixture


class TimingObservationTests(unittest.TestCase):
    def test_schedule_boundaries_age_and_held_identity(self):
        expected = {"timing-ideal": (10001, 0.), "sample-hold": (2501, .015),
                    "dropout": (9901, .25), "hold-dropout": (2475, .275)}
        for profile in PROFILES:
            model = TimingObservations(profile, 73)
            samples = []
            last = None
            for i in range(10001):
                truth = State(position=(i*.001,0,1), velocity=(i*.002,0,0), rates=(i,1,2), acceleration=(i,3,4))
                feedback, sample = model.capture(truth)
                t = round(i*.005,9)
                period = 4 if profile in ("sample-hold", "hold-dropout") else 1
                blocked = "dropout" in profile and (18 <= t < 18.25 or 40 <= t < 40.25)
                if i % period == 0 and not blocked:
                    last = i
                self.assertEqual(sample["source_sequence"],last)
                self.assertEqual(source_sequence(i,profile),last)
                self.assertEqual(feedback.position,(last*.001,0,1))
                self.assertEqual(feedback.velocity,(last*.002,0,0))
                self.assertEqual(feedback.rates,truth.rates)
                self.assertEqual(feedback.acceleration,truth.acceleration)
                samples.append({"time_s":t,"sequence":i,"position_m":truth.position,"velocity_m_s":truth.velocity,"observation":sample})
            m=capture_metrics(samples)
            self.assertEqual((m["captures"],m["max_age_s"]),expected[profile])
            self.assertEqual(m["held_control_samples"],10001-m["captures"])
            self.assertEqual(m["windows"][0]["first_capture_after_s"],18.26 if period==4 else 18.25)
            self.assertEqual(m["windows"][1]["first_capture_after_s"],40.26 if period==4 else 40.25)

    def test_restart_and_profile_isolation(self):
        a=make_observations("hold-dropout",0)
        for _ in range(8):a.capture(State(position=(1,0,1)))
        b=make_observations("hold-dropout",0)
        self.assertEqual(b.capture(State())[1]["source_sequence"],0)
        self.assertEqual(make_observations("timing-ideal",0).capture(State())[0],State())
        for p in ("unknown", "noise"):
            with self.assertRaises(ValueError):TimingObservations(p,0)

    def test_recording_config_and_capture_corruption_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path=record(fixture("hold-dropout"),directory)
            original=read_run(path)
            self.assertEqual(original["manifest.json"]["schema_version"],7)
            with self.assertRaisesRegex(ValidationError,"timing observation"):replay_document(original)
            for mutate in (lambda d:d["samples.json"][409]["observation"].update(source_sequence=409),
                           lambda d:d["samples.json"][409]["observation"]["position_m"].__setitem__(0,1),
                           lambda d:d["samples.json"][409]["observation"].update(age_s=0),
                           lambda d:d["manifest.json"].update(schema_version=6)):
                changed=copy.deepcopy(original);mutate(changed)
                for name,value in changed.items():(path/name).write_bytes(encoded(value))
                (path/"checksums.json").write_bytes(encoded({n:sha256(encoded(v)) for n,v in changed.items()}))
                with self.assertRaises(ValidationError):read_run(path)
            for field,value in (("capture_period_steps",3),("dropout_windows_s",[[18.,18.2]]),("private_path","private")):
                changed=copy.deepcopy(original["config.json"]);changed["observation_model"][field]=value
                with self.assertRaises(ValidationError):validate_config(changed,original["manifest.json"])

    def test_live_contract_distinguishes_monitor_and_capture_age(self):
        model=TimingObservations("hold-dropout",73)
        for i in range(8041):_,o=model.capture(State())
        sample=fixture("hold-dropout")["samples"][-1]
        sample.update(sequence=8040,time_s=40.2,observation=o)
        good=FlightClock().snapshot(73,.005,sample,observation_profile="hold-dropout")
        self.assertEqual(good["schema_version"],3)
        self.assertEqual(good["sample"]["observation"]["source_time_s"],39.98)
        validate_snapshot(good)
        for mutate in (lambda v:v.update(schema_version=2),lambda v:v.update(observation_profile="noise-delay"),
                       lambda v:v["sample"]["observation"].update(source_sequence=8040)):
            bad=copy.deepcopy(good);mutate(bad)
            with self.assertRaises(ValidationError):validate_snapshot(bad)

    def test_recovery_requires_full_dwell_and_preserves_failure(self):
        reference=[{"position_m":(0,0,0)} for _ in range(10001)]
        candidate=copy.deepcopy(reference)
        begin=3650  # End of first outage, at 18.25 s.
        for i in range(begin,begin+1000):candidate[i]["position_m"]=(.051,0,0)
        candidate[begin+1000]["position_m"]=(.05,0,0)
        result=recovery_windows(reference,candidate)
        self.assertEqual(result[0]["recovery_time_s"],5.)
        self.assertTrue(result[0]["passed"])
        candidate[begin+1000]["position_m"]=(.050001,0,0)
        result=recovery_windows(reference,candidate)
        self.assertEqual(result[0]["recovery_time_s"],5.005)
        self.assertFalse(result[0]["passed"])
        # A partial dwell never becomes a zero-second recovery.
        self.assertIsNone(recovery_windows(reference[:3850],reference[:3850])[0]["recovery_time_s"])
        self.assertFalse(recovery_windows(reference[:3850],reference[:3850])[1]["passed"])
        interrupted=copy.deepcopy(reference);interrupted[begin+100]["position_m"]=(.06,0,0)
        self.assertEqual(recovery_windows(reference,interrupted)[0]["recovery_time_s"],.505)

    def test_complete_matrix_mixed_source_and_incomplete_trials(self):
        base=fixture("timing-ideal");runs={};clocks={}
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
            summary=summarize(*read_study(list(PROFILES)))
            self.assertFalse(summary["accepted"]);self.assertEqual(summary["passed"],0)
            self.assertEqual(len(summary["comparisons"]),9)
            self.assertTrue(all(c["reason"]=="incomplete_pair" for c in summary["comparisons"]))
            for c in summary["comparisons"]:
                if "dropout" in c["profile"]:self.assertFalse(c["recovery_passed"])
            for directories in (PROFILES[:3], [*PROFILES[:3],PROFILES[0]]):
                with self.assertRaises(ValidationError):read_study(directories)
            runs[("dropout",0)]["manifest.json"]["source_dirty"]=True
            with self.assertRaises(ValidationError):read_study(PROFILES)
        runs[("dropout",0)]["manifest.json"]["source_dirty"]=False
        runs[("dropout",0)]["manifest.json"]["source_commit"]="f"*40
        with self.assertRaises(ValidationError):summarize(runs,clocks)
