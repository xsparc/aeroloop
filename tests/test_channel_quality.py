import copy
import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aeroloop.axis_feedback import AxisCaptures
from aeroloop.channel_quality import QualityCaptures, QUALITIES, configuration, validate_capture
from aeroloop.contracts import ValidationError
from aeroloop.evidence import read_run, validate_config, replay_document
from aeroloop.live import FlightClock, validate_snapshot
from aeroloop.physics import State
from aeroloop.quality_study import PROFILES, SEEDS, study, export_demo, without_quality
from aeroloop.simulation import encoded, record, sha256
from test_observation import fixture


class ChannelQualityTests(unittest.TestCase):
    def test_acquisition_delay_bootstrap_and_clipped_independent_noise(self):
        before = random.getstate()
        sensors = {q:QualityCaptures(q,73) for q in QUALITIES}
        repeated = QualityCaptures('noise',73)
        other_seed = QualityCaptures('noise',74)
        history = {q:[] for q in QUALITIES}
        for i in range(500):
            truth = State(position=(i,i+1,i+2), velocity=(i*2,i*3,i*4))
            for q, sensor in sensors.items():
                c = sensor.capture(truth); history[q].append(c); validate_capture(c,i,quality=q)
                source = max(0,i-(8 if 'delay' in q else 0))//4*4
                self.assertEqual(c['source_sequence'],source)
                self.assertEqual(c['source_time_s'],round(source*.005,9))
                self.assertEqual(c['age_s'],round((i-source)*.005,9))
                self.assertIsNone(c['position_m'][2]);self.assertIsNone(c['velocity_m_s'][2])
                for k,values,sigma in [('position_m',(source,source+1),.01),('velocity_m_s',(source*2,source*3),.02)]:
                    for a,b in zip(c[k],values): self.assertLessEqual(abs(a-b),3*sigma+1e-10 if 'noise' in q else 0.)
                self.assertLessEqual(len(sensor.history),3)
            self.assertEqual(repeated.capture(truth),history['noise'][-1])
            changed = other_seed.capture(truth)
            self.assertNotEqual(changed['position_m'],history['noise'][-1]['position_m'])
            source = max(0,i-8)//4*4
            for k in ('position_m','velocity_m_s'):
                self.assertEqual(history['noise-delay'][-1][k],history['noise'][source][k])
                if i%4: self.assertEqual(history['noise'][-1][k],history['noise'][-2][k])
        self.assertEqual(before,random.getstate())
        self.assertEqual(max(c['age_s'] for c in history['delay']),.055)

    def test_ideal_capture_and_controller_compatibility(self):
        old, new = AxisCaptures('horizontal'), QualityCaptures('ideal',73)
        for i in range(100):
            state = State(position=(i*.01,0,1),velocity=(1,2,3))
            self.assertEqual(old.capture(state),{k:v for k,v in new.capture(state).items() if k!='quality'})
        for p in PROFILES:
            prior = fixture(p,predictive=True,fresh_axis='horizontal',count=4010)
            result = fixture(p,predictive=True,fresh_axis='horizontal',channel_quality='ideal',count=4010)
            self.assertEqual(prior['samples'],[without_quality(s) for s in result['samples']])
            self.assertEqual(prior['metrics'],result['metrics'])

    def test_reconstruction_rejects_rehashed_noise_delay_mask_and_control_tampering(self):
        with tempfile.TemporaryDirectory() as root:
            path=record(fixture(PROFILES[1],predictive=True,fresh_axis='horizontal',channel_quality='noise-delay',count=4010),root)
            original=read_run(path);self.assertEqual(original['manifest.json']['schema_version'],11)
            with self.assertRaises(ValidationError):replay_document(original)
            bad=copy.deepcopy(original['config.json']);bad['axis_feedback_model']['transport_delay_steps']=0
            with self.assertRaises(ValidationError):validate_config(bad,original['manifest.json'])
            for mutate in (lambda s:s['axis_observation']['position_m'].__setitem__(0,999.),
                           lambda s:s['axis_observation'].update(quality='noise'),
                           lambda s:s['axis_observation'].update(source_sequence=3600),
                           lambda s:s['axis_observation']['position_m'].__setitem__(2,0.),
                           lambda s:s['axis_feedback'].update(position_m=[99.]*3),
                           lambda s:s.update(thrust_setpoint_n=0.),
                           lambda s:s['axis_observation'].update(private_path='private')):
                samples=copy.deepcopy(original['samples.json']);mutate(samples[3603])
                data=encoded(samples);(path/'samples.json').write_bytes(data)
                hashes=json.loads((path/'checksums.json').read_text(encoding='utf-8'));hashes['samples.json']=sha256(data)
                (path/'checksums.json').write_bytes(encoded(hashes))
                with self.assertRaises(ValidationError):read_run(path)

    def test_live_quality_is_distinct_and_validates_delivery_and_composite(self):
        result=fixture(PROFILES[1],predictive=True,fresh_axis='horizontal',channel_quality='noise-delay')
        live=FlightClock().snapshot(73,.005,result['samples'][-1],observation_profile=PROFILES[1])
        self.assertEqual(live['schema_version'],7);validate_snapshot(live)
        for mutate in (lambda s:s.update(schema_version=6),lambda s:s['sample']['axis_observation'].update(age_s=0.),lambda s:s['sample']['axis_feedback'].update(mode='horizontal-fresh')):
            bad=copy.deepcopy(live);mutate(bad)
            with self.assertRaises(ValidationError):validate_snapshot(bad)

    def test_matrix_reproduction_provenance_and_export_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            inputs=[]
            for q in (None,*QUALITIES):
                runs={(p,s):read_run(record(fixture(p,s,predictive=True,fresh_axis='horizontal',channel_quality=q,count=4),root)) for p in PROFILES for s in SEEDS}
                # Synthetic fixtures never become measured evidence.
                for run in runs.values():run['manifest.json']['source_dirty']=False
                inputs.append((runs,{k:dict(monitor_enabled=True,paced=True) for k in runs}))
            directories={q:[] for q in QUALITIES}
            with patch('aeroloop.quality_study.read_study',side_effect=inputs):report,documents=study([],directories)
            self.assertFalse(report['accepted']);self.assertEqual(len(report['ideal_reproduction']),6)
            self.assertEqual(len(report['qualities']),4)
            for change in ('source','settings','ideal'):
                bad=copy.deepcopy(inputs)
                if change=='source':bad[-1][0][PROFILES[0],0]['manifest.json']['source_commit']='f'*40
                elif change=='settings':bad[-1][0][PROFILES[0],0]['config.json']['axis_feedback_model']=configuration('noise')
                else:bad[1][0][PROFILES[0],0]['samples.json'][0]['position_m'][0]=99.
                with patch('aeroloop.quality_study.read_study',side_effect=bad):
                    with self.assertRaises(ValidationError):study([],directories)
            output=Path(root)/'demo';digest=export_demo(report,documents,output)
            self.assertEqual(digest,sha256((output/'index.json').read_bytes()))
            index=json.loads((output/'index.json').read_text(encoding='utf-8'));self.assertEqual(len(index['cases']),9)
            for c in index['cases']:
                data=(output/c['file']).read_bytes();self.assertEqual(sha256(data),c['sha256'])
                pair=json.loads(data);self.assertEqual(pair['baseline']['samples'][0]['axis_observation']['quality'],'ideal')
                self.assertEqual(pair['candidate']['samples'][0]['axis_observation']['quality'],c['quality'])
                self.assertEqual(pair['candidate']['status'],'failed')


if __name__ == '__main__':unittest.main()
