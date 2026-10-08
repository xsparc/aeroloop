import copy
from http.client import HTTPConnection
import json
from pathlib import Path
import tempfile
from threading import Thread
import unittest

from aeroloop.contact_forces import validate_rows,validate_live,write_live
from aeroloop.contracts import ValidationError
from aeroloop.friction_study import trace,summary
from aeroloop.live import monitor_server


def samples():
    # 1 kg sliding at 1 m/s, decelerating by 2 m/s2 under measured friction.
    return [{'time_s':i*.005,'position_m':[i*.005-(i*.005)**2,0,.05],
             'velocity_m_s':[1-2*i*.005,0,0],'quaternion_wxyz':[1,0,0,0],
             'external_force_n':[0,0,0],'target_m':[0,0,.05],'mission_phase':'landed'} for i in range(3)]


class ContactTests(unittest.TestCase):
    def test_momentum_closes_with_preceding_interval_contact(self):
        raw=[[0.]*7+[0]+[0.]*3]+[[i*.005,0,0,9.81,-2,0,0,2,0,0,0] for i in (1,2)]
        rows=trace(samples(),validate_rows(raw))
        result=summary(rows,0,.01)
        self.assertAlmostEqual(result['momentum_without_friction_rms_ns'],.01)
        self.assertLess(result['momentum_with_friction_rms_ns'],1e-15)
        self.assertAlmostEqual(result['friction_work_j'],-.0198)
        self.assertAlmostEqual(result['kinetic_change_j'],-.0198)
        self.assertAlmostEqual(result['work_residual_j'],0)
        self.assertEqual(result['mean_com_alignment'],-1)
        self.assertEqual(summary(rows,.005,.01)['intervals'],1)

    def test_missing_alignment_and_ratio_remain_missing(self):
        s=samples();s[0]['velocity_m_s']=[0,0,0];s[1]['velocity_m_s']=[0,0,0]
        rows=trace(s[:2],[[0.]*11,[.005]+[0.]*10])
        self.assertIsNone(rows[1][30]);self.assertIsNone(rows[1][31])
        self.assertIsNone(summary(rows,0,.005)['mean_com_alignment'])

    def test_incomplete_windows_and_saturated_or_nonfinite_capture_rejected(self):
        raw=[[0.]*7+[0]+[0.]*3,[.005,0,0,9.81,-2,0,0,2,0,0,0]]
        for index,value in ((0,.006),(7,64),(7,True),(4,float('nan'))):
            bad=copy.deepcopy(raw);bad[1][index]=value
            with self.assertRaises(ValidationError):validate_rows(bad)
        with self.assertRaises(ValidationError):summary(trace(samples()[:2],raw),0,.01)
        with self.assertRaises(ValidationError):summary(trace(samples()[:2],raw),0,.004)

    def test_live_endpoint_is_bounded_read_only_and_rejects_private_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);assets=root/'assets';assets.mkdir();(assets/'monitor.html').write_text('monitor')
            (assets/'friction-live.html').write_text('contact');(assets/'assets').mkdir()
            write_live(root,401,[42,0,0,9.81,-2,0,0,2,0,0,0])
            server=monitor_server(root,assets,0);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                connection=HTTPConnection('127.0.0.1',server.server_port)
                connection.request('GET','/api/contact');response=connection.getresponse();value=json.loads(response.read())
                self.assertEqual(response.status,200);self.assertEqual(value['seed'],401);self.assertNotIn('updated_monotonic_s',value)
                connection.request('GET','/api/contact',headers={'Origin':'https://example.invalid'});response=connection.getresponse();response.read();self.assertEqual(response.status,403)
                connection.request('GET','/contact-live.json');response=connection.getresponse();response.read();self.assertEqual(response.status,404)
                connection.request('POST','/api/contact');response=connection.getresponse();response.read();self.assertEqual(response.status,405)
                value=json.loads((root/'contact-live.json').read_text());value['private_path']='private'
                with self.assertRaises(ValidationError):validate_live(value)
            finally:server.shutdown();server.server_close();thread.join()

    def test_sidecar_binds_exact_flight_and_rejects_mismatched_normal_source_and_time(self):
        from unittest.mock import patch
        from aeroloop.contact_forces import COLUMNS,read_capture
        from aeroloop.simulation import encoded,sha256
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);run_id='isaac-ground-mission-wind-1-'+('a'*12)
            run=root/run_id;run.mkdir();(run/'checksums.json').write_bytes(b'{}')
            rows=[[0.]*7+[0]+[0.]*3,[.005,0,0,9.81,-2,0,0,2,0,0,0]]
            source={'source_commit':'a'*40,'source_dirty':False,'source_tree_sha256':'b'*64,'lock_sha256':'c'*64}
            capture={'schema_version':1,'kind':'ground_contact_forces','columns':COLUMNS,'source':source,
                     'physics_dt_s':.005,'capacity':64,'filter':'ground','ground_kind':'stationary-kinematic',
                     'interval':'preceding-control-interval-mean','run_id':run_id,
                     'checksums_sha256':sha256(b'{}'),'rows':rows}
            data={'config.json':{'physics_options':{}},'manifest.json':dict(source),
                  'samples.json':[{'time_s':i*.005,'contact_normal_force_n':r[1:4]} for i,r in enumerate(rows)]}
            path=root/(run_id+'-contact.json')
            with patch('aeroloop.contact_forces.read_run',return_value=data):
                path.write_bytes(encoded(capture));read_capture(root,run_id)
                for mutate in (lambda v:v.update(checksums_sha256='f'*64),lambda v:v['source'].update(source_dirty=True),
                               lambda v:v.update(physics_dt_s=.0025),lambda v:v['rows'][1].__setitem__(3,8),
                               lambda v:v.update(ground_kind='static'),lambda v:v.update(private_path='private')):
                    bad=copy.deepcopy(capture);mutate(bad);path.write_bytes(encoded(bad))
                    with self.assertRaises(ValidationError):read_capture(root,run_id)
