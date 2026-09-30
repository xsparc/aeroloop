import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop.axis_feedback import AxisCaptures, combine, validate_capture, AXES, PROFILES
from aeroloop.axis_study import COHORTS, study, compare_cohort, export_demo, feedback_errors
from aeroloop.contracts import ValidationError
from aeroloop.evidence import read_run, validate_config
from aeroloop.live import FlightClock, validate_snapshot
from aeroloop.physics import State
from aeroloop.simulation import record, encoded, sha256
from test_observation import fixture


class AxisFeedbackTests(unittest.TestCase):
    def test_capture_holds_between_ticks_and_masks_unavailable_axes(self):
        for axes in AXES:
            sensor = AxisCaptures(axes)
            for i in range(410):
                state = State(position=(i,i+1,i+2),velocity=(i*2,i*3,i*4))
                capture = sensor.capture(state);validate_capture(capture,i,axes)
                source = i//4*4
                expected = (None,None,source+2) if axes == 'vertical' else (source,source+1,None)
                self.assertEqual(capture['position_m'],expected)
                prediction = dict(position_m=(-1.,)*3,velocity_m_s=(-2.,)*3)
                feedback = combine(prediction,capture)
                self.assertEqual(feedback['position_m'],tuple(v if v is not None else -1. for v in expected))
                self.assertLessEqual(capture['age_s'],.015)
            bad=copy.deepcopy(capture);bad['source_sequence']+=1
            with self.assertRaises(ValidationError):validate_capture(bad,409,axes)
            bad=copy.deepcopy(capture);bad['position_m']=list(bad['position_m']);bad['position_m'][0 if axes=='vertical' else 2]=0.
            with self.assertRaises(ValidationError):validate_capture(bad,409,axes)

    def test_no_outage_exact_and_live_composite_is_validated(self):
        original=fixture('sample-hold',predictive=True)
        for axes in AXES:
            result=fixture('sample-hold',predictive=True,fresh_axis=axes)
            self.assertEqual(original['samples'],[{k:v for k,v in s.items() if k not in ('axis_observation','axis_feedback')} for s in result['samples']])
            live=FlightClock().snapshot(73,.005,result['samples'][-1],observation_profile='sample-hold')
            self.assertEqual(live['schema_version'],6);validate_snapshot(live)
            live['sample']['axis_feedback']['position_m']=(999.,)*3
            with self.assertRaises(ValidationError):validate_snapshot(live)

    def test_full_evidence_reconstructs_capture_and_control_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as root:
            for axes in AXES:
                path=record(fixture('hold-dropout-2000ms',predictive=True,fresh_axis=axes,count=4010),root)
                original=read_run(path);self.assertEqual(original['manifest.json']['schema_version'],10)
                bad=copy.deepcopy(original['config.json']);bad['axis_feedback_model']['capture_period_steps']=1
                with self.assertRaises(ValidationError):validate_config(bad,original['manifest.json'])
                for mutate in (lambda s:s['axis_observation'].update(position_m=[0.,0.,0.]),lambda s:s['axis_observation'].update(source_sequence=0),lambda s:s['axis_feedback'].update(position_m=[99.,99.,99.]),lambda s:s.update(thrust_setpoint_n=0.),lambda s:s['axis_observation'].update(private_path='private')):
                    samples=copy.deepcopy(original['samples.json']);mutate(samples[3603])
                    data=encoded(samples);(path/'samples.json').write_bytes(data)
                    hashes=json.loads((path/'checksums.json').read_text(encoding='utf-8'));hashes['samples.json']=sha256(data)
                    (path/'checksums.json').write_bytes(encoded(hashes))
                    with self.assertRaises(ValidationError):read_run(path)

    def test_frozen_matrix_failure_export_and_axis_error_decomposition(self):
        with tempfile.TemporaryDirectory() as root:
            inputs=[]
            for cohort,seeds in COHORTS:
                for axis in (None,*AXES):
                    runs={(p,s):read_run(record(fixture(p,s,predictive=True,fresh_axis=axis,count=4),root)) for p in PROFILES for s in seeds}
                    # Synthetic in-memory fixtures only, never public flight evidence.
                    for run in runs.values():run['manifest.json']['source_dirty']=False
                    inputs.append((runs,{k:dict(monitor_enabled=True,paced=True) for k in runs}))
            baselines={c:[] for c,_ in COHORTS};candidates={(c,a):[] for c,_ in COHORTS for a in AXES}
            with patch('aeroloop.axis_study.read_study',side_effect=inputs):report,docs=study(baselines,candidates)
            self.assertFalse(report['accepted']);self.assertEqual(len(report['cohorts']),4)
            old,new=docs['regression','vertical'];r=report['cohorts'][0]
            for change in ('missing','axis','config','prefix'):
                bad=copy.deepcopy(new)
                if change=='missing':bad.pop(('sample-hold',0))
                elif change=='axis':bad['sample-hold',0]['config.json']['axis_feedback_model']['available_axes']='horizontal'
                elif change=='config':bad['sample-hold',0]['config.json']['position_kp']=99.
                else:bad['sample-hold',0]['samples.json'][0]['position_m'][0]=99.
                with self.assertRaises(ValidationError):compare_cohort(old,bad,r['baseline'],r['candidate'],'vertical',(0,1,2))
            changed=copy.deepcopy(inputs);next(iter(changed[-1][0].values()))['manifest.json']['source_commit']='f'*40
            with patch('aeroloop.axis_study.read_study',side_effect=changed):
                with self.assertRaises(ValidationError):study(baselines,candidates)
            output=Path(root)/'demo';digest=export_demo(report,docs,output)
            self.assertEqual(digest,sha256((output/'index.json').read_bytes()))
            index=json.loads((output/'index.json').read_text(encoding='utf-8'));self.assertEqual(len(index['cases']),12)
            for entry in index['cases']:
                data=(output/entry['file']).read_bytes();self.assertEqual(sha256(data),entry['sha256'])
                pair=json.loads(data);self.assertEqual(pair['candidate']['status'],'failed')
                self.assertEqual(pair['candidate']['samples'][-1]['time_s'],.015)
            rows=[dict(time_s=18+i*.005,position_m=(0,0,0),feedback={'position_m':(3,4,12)},axis_feedback={'position_m':(3,4,0)}) for i in range(400)]
            result=feedback_errors(rows)
            self.assertEqual(result[0]['horizontal_position_rmse_m'],5.)
            self.assertEqual(result[0]['vertical_position_peak_m'],0.)
            self.assertTrue(result[0]['complete']);self.assertFalse(result[1]['complete'])
            self.assertIsNone(result[1]['horizontal_position_rmse_m'])

if __name__=='__main__':unittest.main()
