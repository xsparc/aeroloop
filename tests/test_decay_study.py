import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from aeroloop.contracts import ValidationError
from aeroloop.decay_study import study,trace,window_metrics,export_demo
from aeroloop.simulation import encoded,sha256
from test_observation import fixture


class DecayStudyTests(unittest.TestCase):
    def test_matrix_binds_identity_continuity_and_failed_short_exports(self):
        matrices={};directories={};clocks={}
        for cohort,seed in [('regression',0),('additional',401)]:
            directories[cohort]={}
            for mode in ('baseline','candidate'):
                name=cohort+'-'+mode;directories[cohort][mode]=name;runs={};times={}
                for profile in ('sample-hold','hold-dropout-2000ms'):
                    f=fixture(profile,seed,predictive=True,count=3601,fresh_axis='horizontal',channel_quality='noise-delay',decaying=mode=='candidate')
                    run={k+'.json':f[k] for k in ('config','samples','metrics','events')}
                    run['manifest.json']=dict(schema_version=12 if mode=='candidate' else 11,seed=seed,source_dirty=False,source_commit='a'*40,
                        source_tree_sha256='b'*64,controller_binary_sha256='c'*64,lock_sha256='d'*64,config_sha256='e'*64,status='failed',failure_reason='wind_mission_threshold')
                    runs[profile,seed]=run;times[profile,seed]=dict(paced=True,elapsed_s=18.,simulation_s=18.,max_lag_s=0.,late_steps=0,monitor_enabled=True)
                matrices[name]=runs;clocks[name]=times
        with patch('aeroloop.decay_study.COHORTS',{'regression':(0,),'additional':(401,)}),patch('aeroloop.decay_study.read_study',side_effect=lambda name,*_:(matrices[name],clocks[name])):
            report,documents=study(directories);self.assertFalse(report['accepted'])
            self.assertTrue(all(c['unchanged'] for r in report['cohorts'] for c in r['continuity']))
            with tempfile.TemporaryDirectory() as root:
                output=Path(root)/'demo';digest=export_demo(report,documents,output)
                self.assertEqual(digest,sha256((output/'index.json').read_bytes()))
                for c in json.loads((output/'index.json').read_text(encoding='utf-8'))['cases']:
                    data=(output/c['file']).read_bytes();self.assertEqual(c['sha256'],sha256(data));pair=json.loads(data)
                    self.assertEqual(pair['candidate']['status'],'failed');self.assertFalse(pair['candidate']['window']['complete']);self.assertIsNone(pair['candidate']['window']['vertical_velocity_error_rmse_m_s'])
                with self.assertRaises(ValidationError):export_demo(report,documents,output)
            run=matrices['additional-baseline']['sample-hold',401]
            run['manifest.json']['source_commit']='f'*40
            with self.assertRaises(ValidationError):study(directories)
            run['manifest.json']['source_commit']='a'*40
            run['samples.json'][0]['thrust_n']=1
            with self.assertRaises(ValidationError):study(directories)
            with self.assertRaises(ValidationError):study({'regression':directories['regression']})

    def test_diagnostic_terms_contact_dwell_and_impulses_are_sample_based(self):
        samples=fixture('sample-hold',predictive=True,count=3,fresh_axis='horizontal',channel_quality='noise-delay')['samples']
        for i,s in enumerate(samples):
            s.update(time_s=40+i*.005,mission_phase='landing',contact_normal_force_n=[0,0,.2],support_clearance_m=.01,
                     velocity_m_s=[0,0,-.1],target_m=[0,0,1],target_velocity_m_s=[0,0,-.2],target_acceleration_m_s2=[0,0,.3],thrust_setpoint_n=10,thrust_n=9)
            s['axis_feedback'].update(position_m=[0,0,.8],velocity_m_s=[0,0,-.3])
        rows=trace(samples)
        self.assertAlmostEqual(rows[0][7],.5);self.assertAlmostEqual(rows[0][8],.28);self.assertAlmostEqual(rows[0][10],1.08)
        self.assertAlmostEqual(rows[-1][18],.01);self.assertTrue(all(r[17]==1 for r in rows))
        measured=window_metrics(rows,40,40.015);self.assertTrue(measured['complete']);self.assertAlmostEqual(measured['requested_thrust_impulse_n_s'],.15)
        self.assertAlmostEqual(measured['vertical_velocity_error_rmse_m_s'],.2)
        samples[-1]['contact_normal_force_n'][2]=0;self.assertEqual(trace(samples)[-1][18],0)
