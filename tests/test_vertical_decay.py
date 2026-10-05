import copy
import json
import tempfile
import unittest
from aeroloop.contracts import ValidationError
from aeroloop.evidence import read_run, validate_config
from aeroloop.live import FlightClock, validate_snapshot
from aeroloop.predictor import Predictor
from aeroloop.vertical_decay import VerticalDecay, scale_for_age
from aeroloop.simulation import record, encoded, sha256
from test_observation import fixture
from test_predictor import observation


class VerticalDecayTests(unittest.TestCase):
    def test_forgets_only_vertical_propagation_and_retains_anchor(self):
        a,b=Predictor(),VerticalDecay()
        for p in (a,b):
            p.step(observation(velocity=(0.,)*3));p.disturbance=(1.,2.,3.)
        for i in range(1,405):
            o=observation(age=round(i*.005,9),velocity=(0.,)*3)
            x,y=a.step(o,(9.81,(1.,0.,0.,0.))),b.step(o,(9.81,(1.,0.,0.,0.)))
            for k in ('position_m','velocity_m_s','disturbance_acceleration_m_s2'):
                self.assertEqual(x[k][:2],y[k][:2])
            self.assertEqual(b.disturbance,(1.,2.,3.))
            self.assertAlmostEqual(y['disturbance_acceleration_m_s2'][2],3*scale_for_age(o['age_s']))
            if i<4:self.assertEqual(x,y)
        self.assertLess(y['velocity_m_s'][2],x['velocity_m_s'][2])
        resumed=b.step(observation(404,velocity=(9.,)*3),(9.81,(1.,0.,0.,0.)))
        self.assertEqual(resumed['velocity_m_s'],(9.,)*3)
        self.assertEqual(b.telemetry['scale'],1)
        self.assertEqual(b.disturbance,(1.,2.,3.))  # no learning from outage jump
        b.step(observation(408,velocity=(9.,9.,9.02)),(9.81,(1.,0.,0.,0.)))
        self.assertNotEqual(b.disturbance,(1.,2.,3.))

    def test_no_outage_and_pre_outage_continuity(self):
        for profile,count in [('sample-hold',430),('hold-dropout-2000ms',3610)]:
            kwargs=dict(profile=profile,predictive=True,count=count,fresh_axis='horizontal',channel_quality='noise-delay')
            a,b=fixture(**kwargs),fixture(**kwargs,decaying=True)
            normalized=[{k:v for k,v in s.items() if k!='vertical_decay'} for s in b['samples']]
            boundary=3600 if 'dropout' in profile else count
            self.assertEqual(a['samples'][:boundary],normalized[:boundary])
            if boundary<count:self.assertNotEqual(a['samples'][boundary:],normalized[boundary:])

    def test_recording_and_live_reject_rehashed_corruption(self):
        f=fixture('hold-dropout-2000ms',predictive=True,count=3620,fresh_axis='horizontal',channel_quality='noise-delay',decaying=True)
        with tempfile.TemporaryDirectory() as root:
            path=record(f,root);original=read_run(path)
            self.assertEqual(original['manifest.json']['schema_version'],12)
            bad=copy.deepcopy(original['config.json']);bad['feedback_model']['decay_tau_s']=.3
            with self.assertRaises(ValidationError):validate_config(bad,original['manifest.json'])
            checks=json.loads((path/'checksums.json').read_text(encoding='utf-8'))
            for key,value in [('scale',1),('anchor_z_m_s2',0),('effective_z_m_s2',0),('private_path','private')]:
                rows=copy.deepcopy(original['samples.json']);rows[-1]['vertical_decay'][key]=value
                data=encoded(rows);(path/'samples.json').write_bytes(data)
                (path/'checksums.json').write_bytes(encoded({**checks,'samples.json':sha256(data)}))
                with self.assertRaises(ValidationError):read_run(path)
        packet=FlightClock().snapshot(73,.005,f['samples'][-1],observation_profile='hold-dropout-2000ms')
        self.assertEqual(packet['schema_version'],8);validate_snapshot(packet)
        for mutate in [lambda p:p.update(schema_version=7),lambda p:p['sample']['vertical_decay'].update(scale=1),lambda p:p['sample']['axis_observation'].update(quality='ideal')]:
            bad=copy.deepcopy(packet);mutate(bad)
            with self.assertRaises(ValidationError):validate_snapshot(bad)
