import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop.contracts import ValidationError
from aeroloop.evidence import read_run, validate_config
from aeroloop.live import FlightClock, validate_snapshot
from aeroloop.physics import Model
from aeroloop.predictor import Predictor
from aeroloop.simulation import record,encoded,sha256
from aeroloop.prediction_study import display,export_demo,study
from aeroloop.outage_study import PROFILES
from test_observation import fixture

def observation(sequence=0,age=0,position=(0.,0.,1.),velocity=(1.,0.,0.)):
    return dict(source_sequence=sequence,age_s=age,position_m=position,velocity_m_s=velocity)

class PredictorTests(unittest.TestCase):
    def test_constant_velocity_gravity_and_tilted_thrust_are_integrated(self):
        model=Model()
        p=Predictor();p.step(observation())
        for i in range(1,401):out=p.step(observation(age=i*.005),(model.mass*model.gravity,(1.,0.,0.,0.)))
        self.assertEqual(out['mode'],'predicting')
        self.assertAlmostEqual(out['position_m'][0],2.,places=10)
        self.assertAlmostEqual(out['position_m'][2],1.,places=10)
        p=Predictor();p.step(observation(velocity=(0.,)*3))
        for i in range(1,201):out=p.step(observation(age=i*.005),(0.,(1.,0.,0.,0.)))
        self.assertAlmostEqual(out['position_m'][2],1-model.gravity/2,places=10)
        self.assertAlmostEqual(out['velocity_m_s'][2],-model.gravity,places=10)
        p=Predictor();p.step(observation(velocity=(0.,)*3))
        q=(2**-.5,0.,2**-.5,0.)
        for i in range(1,201):out=p.step(observation(age=i*.005),(model.mass*2,q))
        self.assertAlmostEqual(out['position_m'][0],1.,places=10)

    def test_fresh_capture_is_exact_and_expiry_or_resumption_does_not_invent_feedback(self):
        p=Predictor();raw=observation();p.step(raw)
        for i in range(1,425):
            result=p.step({**raw,'age_s':round(i*.005,9)},(0.,(1.,0.,0.,0.)))
            if i<4 or i>420:self.assertEqual(result['position_m'],raw['position_m'])
            if i==420:self.assertEqual(result['mode'],'predicting')
        self.assertEqual(result['mode'],'expired')
        resumed=observation(424,position=(8.,1.,1.))
        result=p.step(resumed,(0.,(1.,0.,0.,0.)))
        self.assertEqual(result['position_m'],resumed['position_m'])
        self.assertEqual(result['mode'],'capture')
        self.assertEqual(result['disturbance_acceleration_m_s2'],(0.,)*3)

    def test_disturbance_learning_is_bounded_and_skips_first_post_outage_jump(self):
        p=Predictor();model=Model();last=observation(velocity=(0.,)*3);p.step(last)
        for i in range(1,401):
            if i%4==0:last=observation(i,velocity=(i*.005,100*i,0.))
            result=p.step({**last,'age_s':(i-last['source_sequence'])*.005},(model.mass*model.gravity,(1.,0.,0.,0.)))
        self.assertAlmostEqual(result['disturbance_acceleration_m_s2'][0],1.,places=4)
        self.assertTrue(3.99<result['disturbance_acceleration_m_s2'][1]<=4.)
        previous=result['disturbance_acceleration_m_s2']
        for i in range(401,501):p.step({**last,'age_s':(i-400)*.005},(0.,(1.,0.,0.,0.)))
        result=p.step(observation(504,velocity=(999.,999.,999.)),(0.,(1.,0.,0.,0.)))
        self.assertEqual(result['disturbance_acceleration_m_s2'],previous)

    def test_recording_reconstructs_predictor_and_rejects_rehashed_corruption(self):
        with tempfile.TemporaryDirectory() as root:
            path=record(fixture('hold-dropout-2000ms',predictive=True,count=3900),root)
            original=read_run(path)
            self.assertEqual(original['manifest.json']['schema_version'],8)
            bad=copy.deepcopy(original['config.json']);bad['feedback_model']['horizon_s']=3
            with self.assertRaises(ValidationError):validate_config(bad,original['manifest.json'])
            for key,value in [('mode','capture'),('position_m',[9.,0.,0.]),('disturbance_acceleration_m_s2',[0.,0.,0.]),('private_path','private')]:
                doc=copy.deepcopy(original);doc['samples.json'][-1]['feedback'][key]=value
                (path/'samples.json').write_bytes(encoded(doc['samples.json']))
                checks=json.loads((path/'checksums.json').read_text(encoding='utf-8'))
                checks['samples.json']=sha256(encoded(doc['samples.json']))
                (path/'checksums.json').write_bytes(encoded(checks))
                with self.assertRaises(ValidationError):read_run(path)

    def test_no_outage_recording_and_live_schema_preserve_raw_captures(self):
        a,b=fixture('sample-hold'),fixture('sample-hold',predictive=True)
        self.assertEqual(a['samples'],[{k:v for k,v in s.items() if k!='feedback'} for s in b['samples']])
        packet=FlightClock().snapshot(73,.005,b['samples'][-1],observation_profile='sample-hold')
        self.assertEqual(packet['schema_version'],4);validate_snapshot(packet)
        packet['sample']['feedback']['private_path']='private'
        with self.assertRaises(ValidationError):validate_snapshot(packet)

    def test_export_preserves_failed_short_traces_and_binds_every_file(self):
        with tempfile.TemporaryDirectory() as root:
            old={};new={}
            for profile in PROFILES:
                for seed in range(3):
                    old[profile,seed]=read_run(record(fixture(profile,seed),root))
                    new[profile,seed]=read_run(record(fixture(profile,seed,predictive=True),root))
            summary={'source_commit':'a'*40,'controller_binary_sha256':'b'*64,'lock_sha256':'c'*64,'versions':{},'accepted':False,'duration_results':[{} for _ in PROFILES]}
            with patch('aeroloop.prediction_study.read_study',return_value=(old,{})),patch('aeroloop.prediction_study.read_timing',return_value=(new,{})),patch('aeroloop.prediction_study.summarize',return_value=summary):
                report,_,_=study([],[])
                self.assertTrue(report['no_outage_unchanged']);self.assertFalse(report['accepted'])
                with patch('aeroloop.prediction_study.summarize',side_effect=[summary,{**summary,'lock_sha256':'d'*64}]):
                    with self.assertRaises(ValidationError):study([],[])
                new[PROFILES[0],0]['config.json']['position_kp']=9
                with self.assertRaises(ValidationError):study([],[])
                new[PROFILES[0],0]['config.json']['position_kp']=2.5
            output=Path(root)/'export';digest=export_demo(report,old,new,output)
            self.assertEqual(digest,sha256((output/'index.json').read_bytes()))
            index=json.loads((output/'index.json').read_text(encoding='utf-8'))
            self.assertEqual(len(index['cases']),15)
            for case in index['cases']:
                data=(output/case['file']).read_bytes();self.assertEqual(case['sha256'],sha256(data))
                pair=json.loads(data)
                self.assertEqual(pair['candidate']['status'],'failed')
                self.assertEqual(pair['candidate']['samples'][-1]['time_s'],2.045)
                self.assertTrue(any(g['status']!='passed' for g in pair['candidate']['gates']))
            with self.assertRaises(ValidationError):export_demo(report,old,new,output)

if __name__=='__main__':unittest.main()
