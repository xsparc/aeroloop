import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aeroloop.approach_control import parameters
from aeroloop.approach_study import trace, diagnostics, gate_changes
from aeroloop.contracts import ValidationError
from aeroloop.evidence import read_run, validate_config
from aeroloop.live import FlightClock, validate_snapshot
from aeroloop.physics import State
from aeroloop.simulation import record, encoded, sha256
from aeroloop.wind_mission import TrackingController
from test_observation import fixture


class ApproachTests(unittest.TestCase):
    def test_smooth_schedule_and_inactive_gains(self):
        self.assertEqual(parameters(34), (0.,2.5,2.8))
        self.assertEqual(parameters(34.5), (.5,3.25,3.1999999999999997))
        self.assertEqual(parameters(35), (1.,4.,3.5999999999999996))
        for t in (0,33.9,34,34.5,35,42,50):
            self.assertEqual(parameters(t,False),(0.,2.5,2.8))
        self.assertLess(parameters(34.0001)[0],1e-10)
        self.assertLess(1-parameters(34.9999)[0],1e-10)

    def test_horizontal_change_leaves_vertical_demand_and_disarm_fixed(self):
        state=State(position=(.2,-.1,1.),velocity=(.1,-.2,.3))
        accelerations=[]
        def capture(s,a,m):
            accelerations.append(a)
            return 9.,(0.,0.,0.)
        with patch('aeroloop.wind_mission.acceleration_wrench',capture):
            for mode in (False,True):
                c=TrackingController(approach=mode)
                c.step(35,state,(0.,0.,.5),True)
                self.assertEqual(c.step(35.005,state,(0.,0.,.5),False)[:2],(0.,(0.,0.,0.)))
                self.assertEqual(c.integral,(0.,0.,0.))
        self.assertEqual(accelerations[0][2],accelerations[1][2])
        self.assertAlmostEqual(accelerations[1][0]-accelerations[0][0],-1.5*.2-.8*.1)
        self.assertAlmostEqual(accelerations[1][1]-accelerations[0][1],1.5*.1+.8*.2)

    def test_pre_ramp_continuity_recording_and_live_tamper_rejection(self):
        kwargs=dict(profile='hold-dropout-2000ms',count=7010,predictive=True,fresh_axis='horizontal',channel_quality='noise-delay',decaying=True)
        a,b=fixture(**kwargs),fixture(**kwargs,approaching=True)
        self.assertEqual(a['samples'][:6800],[{k:v for k,v in s.items() if k!='approach_control'} for s in b['samples'][:6800]])
        self.assertEqual(b['samples'][-1]['approach_control'],parameters(35.045))
        with tempfile.TemporaryDirectory() as root:
            path=record(b,root);original=read_run(path)
            self.assertEqual(original['manifest.json']['schema_version'],13)
            bad=copy.deepcopy(original['config.json']);bad['trajectory_control']['horizontal_position_kp']=4.1
            with self.assertRaises(ValidationError):validate_config(bad,original['manifest.json'])
            checks=json.loads((path/'checksums.json').read_text(encoding='utf-8'))
            for key,value in [('approach_control',[1.,2.5,2.8]),('thrust_setpoint_n',9.),('private_path','private')]:
                rows=copy.deepcopy(original['samples.json']);rows[-1][key]=value
                data=encoded(rows);(path/'samples.json').write_bytes(data)
                (path/'checksums.json').write_bytes(encoded({**checks,'samples.json':sha256(data)}))
                with self.assertRaises(ValidationError):read_run(path)
        packet=FlightClock().snapshot(73,.005,b['samples'][-1],observation_profile=kwargs['profile'])
        self.assertEqual(packet['schema_version'],9);validate_snapshot(packet)
        for mutate in [lambda p:p.update(schema_version=8),lambda p:p['sample'].update(approach_control=[0.,2.5,2.8]),lambda p:p['sample'].update(private_path='private')]:
            bad=copy.deepcopy(packet);mutate(bad)
            with self.assertRaises(ValidationError):validate_snapshot(bad)

    def test_interval_integrals_and_clipping_do_not_count_terminal_state(self):
        base={'time_s':34.,'axis_feedback':{'position_m':(0.,0.,0.),'velocity_m_s':(0.,0.,0.)},
            'mission_phase':'landing','target_m':(2.,0.,0.),'target_velocity_m_s':(0.,)*3,
            'target_acceleration_m_s2':(0.,)*3,'integral_acceleration_m_s2':(0.,)*3,
            'position_m':(0.,)*3,'velocity_m_s':(0.,)*3,'quaternion_wxyz':(1.,0.,0.,0.),
            'allocation_scale':1.,'external_force_n':(0.,)*3,'thrust_n':9.,'thrust_setpoint_n':9.,
            'contact_normal_force_n':(0.,)*3,'support_clearance_m':1.}
        samples=[base,{**base,'time_s':34.005,'target_m':(1.,0.,0.)},{**base,'time_s':34.010,'target_m':(100.,0.,0.)}]
        rows=trace(samples);d=diagnostics(rows)
        self.assertAlmostEqual(d['squared_error_integral_m2_s'],(4+1)*.005)
        self.assertAlmostEqual(d['squared_demand_integral_m2_s3'],(16+6.25)*.005)
        self.assertEqual(d['axis_clipped_fraction'],.5)
        self.assertFalse(d['complete']);self.assertEqual(diagnostics([])['squared_error_integral_m2_s'],None)
        a=[dict(id='x',status='passed',headroom=1.),dict(id='y',status='failed',headroom=-1.)]
        b=[dict(id='x',status='not_measured',headroom=None),dict(id='y',status='passed',headroom=2.)]
        self.assertEqual([g['change'] for g in gate_changes(a,b)],['regressed','improved'])
        self.assertEqual(gate_changes(a,b)[1]['headroom_delta'],3.)
