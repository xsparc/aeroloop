import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop.contracts import ValidationError
from aeroloop.evidence import read_run
from aeroloop.landing_study import COHORTS,compare_cohort,export_demo,guard_display,study
from aeroloop.outage_study import summarize
from aeroloop.simulation import record,sha256
from test_observation import fixture


class LandingStudyTests(unittest.TestCase):
    def test_cohorts_bind_unseen_seeds_sources_configs_and_all_failed_traces(self):
        with tempfile.TemporaryDirectory() as root:
            documents={};read_results=[]
            clock=dict(monitor_enabled=True,paced=True)
            for name,seeds,profiles in COHORTS:
                sides=[]
                for guarded in (False,True):
                    runs={(p,s):read_run(record(fixture(p,s,predictive=True,guarded=guarded,count=4),root)) for p in profiles for s in seeds}
                    # Synthetic in-memory study inputs, never published as measured evidence.
                    for run in runs.values():run['manifest.json']['source_dirty']=False
                    sides.append(runs);read_results.append((runs,{key:clock for key in runs}))
                documents[name]=sides
            with patch('aeroloop.landing_study.read_study',side_effect=read_results):
                report,loaded=study([],[],[],[])
            self.assertFalse(report['accepted'])
            self.assertEqual([c['candidate']['trials'] for c in report['cohorts']],[12,6])
            self.assertTrue(all(r['trace_unchanged'] for c in report['cohorts'] for r in c['comparisons']))
            old,new=documents['unseen'];c=report['cohorts'][1]
            for bad in ({**c['candidate'],'lock_sha256':'f'*64},{**c['candidate'],'versions':{}}):
                with self.assertRaises(ValidationError):compare_cohort(old,new,c['baseline'],bad,COHORTS[1][1],COHORTS[1][2])
            missing=dict(new);missing.pop(('sample-hold',101))
            with self.assertRaises(ValidationError):compare_cohort(old,missing,c['baseline'],c['candidate'],COHORTS[1][1],COHORTS[1][2])
            changed=copy.deepcopy(new);changed['sample-hold',101]['samples.json'][0]['position_m'][0]=1.
            with self.assertRaises(ValidationError):compare_cohort(old,changed,c['baseline'],c['candidate'],COHORTS[1][1],COHORTS[1][2])
            changed=copy.deepcopy(new);changed['sample-hold',101]['config.json']['position_kp']=99
            with self.assertRaises(ValidationError):compare_cohort(old,changed,c['baseline'],c['candidate'],COHORTS[1][1],COHORTS[1][2])
            with self.assertRaises(ValidationError):summarize(new,{key:clock for key in new},9,COHORTS[1][2],(0,1,2))
            # A new-source baseline cannot be mixed with a different guarded revision.
            summaries=[report['cohorts'][0]['baseline'],report['cohorts'][0]['candidate'],c['baseline'],{**c['candidate'],'source_commit':'f'*40}]
            with patch('aeroloop.landing_study.read_study',side_effect=read_results),patch('aeroloop.landing_study.summarize',side_effect=summaries):
                with self.assertRaises(ValidationError):study([],[],[],[])
            output=Path(root)/'demo';digest=export_demo(report,loaded,output)
            self.assertEqual(digest,sha256((output/'index.json').read_bytes()))
            index=json.loads((output/'index.json').read_text(encoding='utf-8'))
            self.assertEqual(len(index['cases']),18)
            self.assertEqual(index['cohorts'][1]['seeds'],[101,202,303])
            for case in index['cases']:
                raw=(output/case['file']).read_bytes();self.assertEqual(sha256(raw),case['sha256'])
                pair=json.loads(raw);self.assertEqual(pair['candidate']['status'],'failed')
                self.assertEqual(pair['candidate']['samples'][-1]['time_s'],.015)
                self.assertIn('landing_guard',pair['candidate']['samples'][0])
                self.assertNotIn('landing_guard',pair['baseline']['samples'][0])
            with self.assertRaises(ValidationError):export_demo(report,loaded,output)

    def test_display_keeps_guard_transition_neighbors(self):
        # Synthetic display fixture only; the export path verifies evidence separately.
        run={'config.json':{'observation_model':{'profile':'sample-hold'}},'events.json':[], 'samples.json':[]}
        fields=('position_m','target_m','quaternion_wxyz','rotor_thrust_n','wind_velocity_m_s','external_force_n','external_moment_nm','mission_phase','contact_normal_force_n','support_clearance_m','observation','feedback')
        for i in range(30):
            run['samples.json'].append({**dict.fromkeys(fields,None),'time_s':i*.005,
                'observation':{'position_m':[],'velocity_m_s':[]},'landing_guard':{'mode':'holding' if i<13 else 'descending','resumed_at_s':None if i<13 else .065}})
        shown=guard_display(run)
        self.assertTrue({.06,.065,.07} <= {s['time_s'] for s in shown})

if __name__=='__main__':unittest.main()
