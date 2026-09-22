import copy
from http.client import HTTPConnection
from pathlib import Path
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch

from aeroloop.contracts import ValidationError
from aeroloop.live import FlightClock, finish_monitor, monitor_server, validate_snapshot, write_snapshot
from aeroloop.flight_study import compare, timing, report
from aeroloop.simulation import encoded


def sample(i=0):
    return {"time_s": i*.005, "sequence": i, "position_m": [0,0,1.5], "velocity_m_s": [0,0,0],
        "quaternion_wxyz": [1,0,0,0], "target_m": [0,0,1.5], "rates_rad_s": [0,0,0],
        "rate_setpoint_rad_s": [0,0,0], "effort_normalized": [0,0,0], "rotor_thrust_n": [2.45]*4,
        "allocation_scale": 1., "wind_velocity_m_s": [1,0,0], "external_force_n": [.1,0,0],
        "mission_phase": "hover", "contact_normal_force_n": [0,0,0], "support_clearance_m": 1.45}


class LiveTests(unittest.TestCase):
    def test_clock_paces_without_changing_simulation_or_skipping_late_updates(self):
        now = [0.]
        sleeps = []
        def sleep(duration):
            sleeps.append(duration); now[0] += duration
        clock = FlightClock(True, lambda: now[0], sleep)
        clock.tick(.005)
        self.assertEqual(sleeps, [.005])
        now[0] = .020
        clock.tick(.010)
        clock.tick(.015)
        self.assertEqual(sleeps, [.005])
        self.assertEqual(clock.max_lag, .010)
        self.assertEqual(clock.late_steps, 2)

    def test_snapshot_rejects_private_fields_nonfinite_and_inconsistent_timing(self):
        good = FlightClock().snapshot(0,.005,sample())
        for mutate in (lambda v: v.update(private_path="private"), lambda v: v.update(elapsed_s=float('nan')),
                       lambda v: v['sample'].update(sequence=1), lambda v: v['sample'].update(quaternion_wxyz=[0]*4)):
            value = copy.deepcopy(good); mutate(value)
            with self.assertRaises(ValidationError): validate_snapshot(value)
        with tempfile.TemporaryDirectory() as directory:
            write_snapshot(directory, good)
            finish_monitor(directory, False)
            self.assertIn(b'"state":"failed"', (Path(directory)/'live.json').read_bytes())
            self.assertFalse((Path(directory)/'live.tmp').exists())

    def test_loopback_server_blocks_paths_origins_writes_and_marks_stale(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); assets = root/'assets-root'; assets.mkdir(); (assets/'assets').mkdir()
            (assets/'monitor.html').write_text('<h1>monitor</h1>')
            session = root/'session'; session.mkdir()
            value = FlightClock().snapshot(0,.005,sample()); value['updated_monotonic_s'] = 0
            write_snapshot(session, value)
            server = monitor_server(session, assets, 0)
            thread = Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                def request(path, method='GET', headers=None):
                    c = HTTPConnection('127.0.0.1', server.server_port, timeout=3)
                    c.request(method,path,headers=headers or {}); response = c.getresponse()
                    result = (response.status, response.read(), dict(response.getheaders())); c.close(); return result
                code, body, headers = request('/api/live')
                self.assertEqual(code,200); self.assertIn(b'"stale":true',body)
                self.assertNotIn(b'updated_monotonic_s',body)
                self.assertEqual(headers['Cache-Control'],'no-store')
                self.assertNotIn('Access-Control-Allow-Origin',headers)
                for path in ('/live.json','/../live.json','/%2e%2e/live.json','/api/live?file=secret'):
                    self.assertEqual(request(path)[0],404)
                self.assertEqual(request('/api/live',headers={'Host':'attacker.invalid'})[0],403)
                self.assertEqual(request('/api/live',headers={'Origin':'https://attacker.invalid'})[0],403)
                self.assertEqual(request('/api/live','POST')[0],405)
                (session/'live.json').write_bytes(encoded({'private':'value'}))
                self.assertEqual(request('/api/live')[0],503)
                (session/'live.json').unlink()
                self.assertIn(b'waiting',request('/api/live')[1])
            finally:
                server.shutdown(); server.server_close(); thread.join()

    def test_sensitivity_preserves_failure_and_requires_identical_wind(self):
        # Protocol-only trajectories, never claimed as measured physics.
        a = {'samples.json':[sample(i) for i in range(10001)],
             'metrics.json':{'position_rmse_m':.1,'mission':{'landed_time_s':44.}}}
        b = copy.deepcopy(a)
        self.assertTrue(compare(a,b)['passed'])
        b['samples.json'][500]['position_m'][0] = .16
        self.assertFalse(compare(a,b)['passed'])
        b['samples.json'][0]['wind_velocity_m_s'][0] = 2
        with self.assertRaises(ValidationError): compare(a,b)

    def test_timing_rejects_invented_fields_and_impossible_counts(self):
        good = {'paced':True,'elapsed_s':51.,'simulation_s':50.,'max_lag_s':1.,'late_steps':5,'monitor_enabled':True}
        self.assertAlmostEqual(timing(good,50.)['real_time_factor'],50/51)
        with self.assertRaises(ValidationError): timing({**good,'late_steps':10002},50.)
        with self.assertRaises(ValidationError): timing({**good,'host':'private'},50.)

    def test_report_requires_complete_matrix_clean_provenance_and_shared_inputs(self):
        samples = [sample(i) for i in range(10001)]
        measured = {'position_rmse_m':.1,'mission':{'landed_time_s':44.}}
        cases, results = {}, {}
        for dt in (.005,.0025,.00125):
            cases[dt] = [{'manifest.json':{'scenario':'ground-mission-wind','seed':seed,'source_dirty':False,
                'source_commit':'a'*40,'source_tree_sha256':'b'*64,'controller_binary_sha256':'c'*64,
                'lock_sha256':'d'*64,'config_sha256':'e'*64,'status':'passed','failure_reason':None},
                'config.json':{'seed':seed,'simulator_versions':{},'physics_options':{'physics_dt_s':dt}},
                'samples.json':samples,'metrics.json':measured} for seed in range(3)]
            results[dt] = {'results':[{'timing':{'paced':True,'elapsed_s':51.,'simulation_s':50.,
                'max_lag_s':1.,'late_steps':100,'monitor_enabled':True}} for _ in range(3)]}
        with patch('aeroloop.flight_study.load_json',side_effect=lambda p:results[float(p.parent.name)]), \
             patch('aeroloop.flight_study.validate_flight_result',side_effect=lambda d,r:cases[float(d)]):
            directories=['.005','.0025','.00125']
            self.assertTrue(report(directories)['accepted'])
            cases[.00125][0]['manifest.json']['source_dirty']=True
            with self.assertRaises(ValidationError): report(directories)
            cases[.00125][0]['manifest.json']['source_dirty']=False
            cases[.00125][0]['config.json']['extra']='private'
            with self.assertRaises(ValidationError): report(directories)
            del cases[.00125][0]['config.json']['extra']
            cases[.00125][0]['manifest.json'].update(status='failed',failure_reason='wind_mission_threshold')
            self.assertFalse(report(directories)['accepted'])
            with self.assertRaises(ValidationError): report(['.005','.005','.00125'])
