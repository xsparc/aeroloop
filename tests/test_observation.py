import copy
from dataclasses import asdict, replace
import random
import tempfile
import unittest
from unittest.mock import patch

from aeroloop import mission, wind_mission
from aeroloop.contracts import ValidationError
from aeroloop.evidence import read_run, validate_config, replay_document
from aeroloop.live import FlightClock, validate_snapshot
from aeroloop.observation import Observations, make_observations, PROFILES, configuration, validate_capture
from aeroloop.observation_study import read_study, summarize
from aeroloop.physics import Model, State
from aeroloop.rotors import RotorModel
from aeroloop.simulation import encoded, metrics, record, sha256


def fixture(profile="noise-delay", seed=73, predictive=False, count=410):
    # Synthetic failed protocol fixture; deliberately no physical integration.
    state, route, tracking = mission.initial_state(seed), mission.Mission(), wind_mission.TrackingController()
    wind, rotors, observations = wind_mission.wind_model(), RotorModel(), make_observations(profile,seed)
    from aeroloop.predictor import Predictor, configuration as predictor_configuration
    predictor = Predictor() if predictive else None
    samples, motors, scale = [], (0.,)*4, 1.
    for i, velocity in enumerate(wind.velocities(seed,.005,count)):
        t=round(i*.005,9)
        feedback, observed = observations.capture(state)
        if predictor:
            predicted = predictor.step(observed, (samples[-1]["thrust_n"],samples[-1]["quaternion_wxyz"]) if samples else None)
            feedback = replace(feedback,position=predicted["position_m"],velocity=predicted["velocity_m_s"])
        phase,target,armed,bottom = route.update(t,state,(0.,)*3)
        thrust,rate,control = tracking.step(t,feedback,target,armed,.005,scale < 1.-1e-12)
        command,_,scale = rotors.allocate(thrust,(0.,)*3)
        motors = rotors.advance(motors,command,.005)
        applied,moment = rotors.wrench(motors)
        force,external_moment = wind.wrench(state.velocity,state.quaternion,state.rates,velocity)
        samples.append(dict(time_s=t,sequence=i,position_m=state.position,velocity_m_s=state.velocity,
            quaternion_wxyz=state.quaternion,rates_rad_s=state.rates,target_m=target,rate_setpoint_rad_s=rate,
            effort_normalized=[0]*3,thrust_n=applied,external_force_n=force,external_moment_nm=external_moment,
            wind_velocity_m_s=velocity,thrust_setpoint_n=thrust,rotor_command_n=command,rotor_thrust_n=motors,
            moment_nm=moment,allocation_scale=scale,mission_phase=phase,contact_normal_force_n=[0]*3,
            support_clearance_m=bottom,observation=observed,**control))
        if predictor:samples[-1]["feedback"]=predicted
    config=dict(model=asdict(Model()),initial_state=asdict(state),dt_s=.005,duration_s=50.,scenario=wind_mission.SCENARIO,
        seed=seed,controller="rate-pid-v1",position_kp=2.5,position_kd=2.8,attitude_kp=5.,
        rate_gains={"p":[.6]*3,"i":[.1]*3,"d":[.005]*3,"ff":[0.]*3,"integral_limit":[.3]*3},
        actuator=asdict(rotors),simulator_versions={"isaacsim":"6.1","isaaclab":"17.0","torch":"2.11"},
        physics_options={"gyroscopic_forces":True},mission=wind_mission.contact_configuration(),wind=asdict(wind),
        trajectory_control=wind_mission.control_configuration(),observation_model=configuration(profile))
    if predictor:config["feedback_model"]=predictor_configuration()
    return dict(experiment="isaac-quadrotor",config=config,samples=samples,events=wind_mission.events(route.events,samples[-1]["time_s"]),
        metrics=metrics(samples,wind_mission.SCENARIO),status="failed",failure_reason="wind_mission_threshold",controller_binary_sha256="a"*64)


class ObservationTests(unittest.TestCase):
    def test_delay_holds_first_capture_and_preserves_current_ideal_channels(self):
        model=Observations("delay",73)
        for i in range(20):
            truth=State(position=(i,0,1),velocity=(i*2,0,0),rates=(i,1,2),acceleration=(i,3,4))
            feedback,s=model.capture(truth)
            source=max(0,i-8)
            self.assertEqual(feedback.position,(source,0,1))
            self.assertEqual(feedback.velocity,(source*2,0,0))
            self.assertEqual(feedback.rates,truth.rates)
            self.assertEqual(feedback.acceleration,truth.acceleration)
            self.assertEqual(s["source_sequence"],source)
            self.assertEqual(s["age_s"],round((i-source)*.005,9))
        self.assertEqual(len(model.history),9)

    def test_noise_is_captured_once_clipped_seeded_and_uses_an_independent_stream(self):
        before=random.getstate()
        noise,combined=Observations("noise",73),Observations("noise-delay",73)
        captures=[]
        for i in range(500):
            state=State(position=(i*.001,0,1),velocity=(1,0,0))
            _,n=noise.capture(state); feedback,c=combined.capture(state); captures.append(n)
            for key,truth,limit in (("position_m",state.position,.03),("velocity_m_s",state.velocity,.06)):
                self.assertTrue(all(abs(a-b)<=limit+1e-12 for a,b in zip(n[key],truth)))
                self.assertEqual(c[key],captures[max(0,i-8)][key])
        self.assertEqual(random.getstate(),before)
        self.assertEqual(Observations("noise",73).capture(State())[1],Observations("noise",73).capture(State())[1])
        self.assertNotEqual(Observations("noise",73).capture(State())[1],Observations("noise",74).capture(State())[1])
        state=State(); feedback,s=Observations("ideal",73).capture(state)
        self.assertEqual(feedback,state)
        self.assertEqual(s["position_m"],state.position)

    def test_observation_evidence_recomputes_feedback_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            path=record(fixture(),directory); original=read_run(path)
            self.assertEqual(original["manifest.json"]["schema_version"],6)
            replay = replay_document(original)
            self.assertEqual(replay["samples"][0]["observation"], original["samples.json"][0]["observation"])
            self.assertEqual(replay["samples"][-1]["velocity_m_s"], original["samples.json"][-1]["velocity_m_s"])
            changes=[
                ("samples.json",lambda s:s[409]["observation"]["position_m"].__setitem__(0,.8)),
                ("samples.json",lambda s:s[409]["observation"].update(source_sequence=409)),
                ("samples.json",lambda s:s[409]["observation"].update(age_s=.035)),
                ("samples.json",lambda s:s[409]["observation"].update(private_path="private")),
                ("samples.json",lambda s:s[409].update(rate_setpoint_rad_s=[0]*3)),
                ("samples.json",lambda s:s[409].update(external_force_n=[0]*3)),
                ("metrics.json",lambda m:m.update(position_rmse_m=0.)),
                ("manifest.json",lambda m:m.update(status="passed",failure_reason=None))]
            for filename,mutate in changes:
                data=copy.deepcopy(original); mutate(data[filename])
                for name,value in data.items(): (path/name).write_bytes(encoded(value))
                (path/"checksums.json").write_bytes(encoded({name:sha256(encoded(value)) for name,value in data.items()}))
                with self.subTest(filename=filename), self.assertRaises(ValidationError): read_run(path)

    def test_fixed_configuration_and_live_contract_reject_mislabeled_profiles(self):
        f=fixture(); c=f["config"]
        m=dict(schema_version=6,scenario=wind_mission.SCENARIO,seed=73,controller="rate-pid-v1")
        validate_config(c,m)
        for field,value in (("delay_steps",7),("position_sigma_m",.02),("startup","zero"),("private_path","private")):
            changed=copy.deepcopy(c);changed["observation_model"][field]=value
            with self.assertRaises(ValidationError):validate_config(changed,m)
        good=FlightClock().snapshot(73,.005,f["samples"][-1],observation_profile="noise-delay")
        validate_snapshot(good)
        for mutate in (lambda v:v.update(observation_profile="ideal"),lambda v:v["sample"]["observation"].update(age_s=.02),lambda v:v.update(schema_version=1)):
            bad=copy.deepcopy(good);mutate(bad)
            with self.assertRaises(ValidationError):validate_snapshot(bad)

    def test_study_requires_complete_matrix_and_preserves_failed_trials(self):
        base=fixture()
        runs={}; clocks={}
        for profile in PROFILES:
            for seed in range(3):
                run={key+".json":copy.deepcopy(base[key]) for key in ("config","samples","metrics","events")}
                run["config.json"].update(seed=seed,observation_model=configuration(profile))
                run["manifest.json"]=dict(schema_version=6,seed=seed,source_dirty=False,source_commit="a"*40,
                    source_tree_sha256="b"*64,controller_binary_sha256="c"*64,lock_sha256="d"*64,
                    config_sha256="e"*64,status="failed",failure_reason="wind_mission_threshold")
                runs[(profile,seed)]=run
                clocks[(profile,seed)]=dict(paced=True,elapsed_s=3.,simulation_s=2.045,max_lag_s=1.,late_steps=1,monitor_enabled=True)
        def worker(directory,result):return [runs[(str(directory),s)] for s in range(3)]
        def result(path):return {"results":[{"timing":clocks[(path.parent.name,s)]} for s in range(3)]}
        with patch("aeroloop.observation_study.validate_flight_result",side_effect=worker),patch("aeroloop.observation_study.load_json",side_effect=result):
            actual,times=read_study(list(PROFILES))
            summary=summarize(actual,times)
            self.assertFalse(summary["accepted"]);self.assertEqual(summary["passed"],0)
            self.assertEqual(len(summary["comparisons"]),9)
            self.assertTrue(all(c["reason"]=="incomplete_pair" for c in summary["comparisons"]))
            for directories in (list(PROFILES[:3]),["ideal","noise","delay","delay"]):
                with self.assertRaises(ValidationError):read_study(directories)
            runs[("noise",0)]["manifest.json"]["source_dirty"]=True
            with self.assertRaises(ValidationError):read_study(list(PROFILES))
        runs[("noise",0)]["manifest.json"]["source_dirty"]=False
        runs[("noise",0)]["manifest.json"]["source_commit"]="f"*40
        with self.assertRaises(ValidationError):summarize(runs,clocks)
