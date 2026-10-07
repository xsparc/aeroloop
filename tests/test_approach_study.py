import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aeroloop.contracts import ValidationError
from aeroloop.approach_study import study,export_demo
from aeroloop.simulation import encoded,sha256
from test_observation import fixture


class ApproachStudyTests(unittest.TestCase):
    def test_matrix_binds_identity_continuity_and_failed_short_exports(self):
        matrices={};directories={};clocks={}
        for cohort,seed in [('regression',0),('stress',401),('additional',709)]:
            directories[cohort]={}
            for mode in ('baseline','candidate'):
                name=cohort+'-'+mode;directories[cohort][mode]=name;runs={};times={}
                for profile in ('sample-hold','hold-dropout-2000ms'):
                    f=fixture(profile,seed,predictive=True,count=6801,fresh_axis='horizontal',channel_quality='noise-delay',decaying=True,approaching=mode=='candidate')
                    run={k+'.json':f[k] for k in ('config','samples','metrics','events')}
                    run['manifest.json']=dict(schema_version=13 if mode=='candidate' else 12,seed=seed,source_dirty=False,source_commit='a'*40,
                        source_tree_sha256='b'*64,controller_binary_sha256='c'*64,lock_sha256='d'*64,config_sha256='e'*64,status='failed',failure_reason='wind_mission_threshold')
                    runs[profile,seed]=run;times[profile,seed]=dict(paced=True,elapsed_s=34.,simulation_s=34.,max_lag_s=0.,late_steps=0,monitor_enabled=True)
                matrices[name]=runs;clocks[name]=times
        with patch('aeroloop.approach_study.COHORTS',{'regression':(0,),'stress':(401,),'additional':(709,)}),patch('aeroloop.approach_study.read_study',side_effect=lambda name,*_:(matrices[name],clocks[name])):
            report,documents=study(directories);self.assertFalse(report['accepted'])
            self.assertTrue(all(c['unchanged'] for r in report['cohorts'] for c in r['continuity']))
            with tempfile.TemporaryDirectory() as root:
                output=Path(root)/'demo';digest=export_demo(report,documents,output)
                self.assertEqual(digest,sha256((output/'index.json').read_bytes()))
                for c in json.loads((output/'index.json').read_text(encoding='utf-8'))['cases']:
                    data=(output/c['file']).read_bytes();self.assertEqual(c['sha256'],sha256(data));pair=json.loads(data)
                    self.assertEqual(pair['candidate']['status'],'failed');self.assertFalse(pair['candidate']['diagnostics']['complete']);self.assertIsNone(pair['candidate']['diagnostics']['axis_clipped_fraction'])
                with self.assertRaises(ValidationError):export_demo(report,documents,output)
            run=matrices['additional-baseline']['sample-hold',709]
            run['manifest.json']['source_commit']='f'*40
            with self.assertRaises(ValidationError):study(directories)
            run['manifest.json']['source_commit']='a'*40
            run['samples.json'][0]['thrust_n']=1
            with self.assertRaises(ValidationError):study(directories)
            with self.assertRaises(ValidationError):study({'regression':directories['regression']})
