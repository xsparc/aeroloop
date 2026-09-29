import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop.contracts import ValidationError
from aeroloop.evidence import read_run,validate_config
from aeroloop.landing_guard import LandingGuard,configuration
from aeroloop.live import FlightClock,validate_snapshot
from aeroloop.mission import scheduled_target
from aeroloop.simulation import record,encoded,sha256
from test_observation import fixture

def capture(age=0,position=(0.,0.,.3),velocity=(0.,)*3):
    return dict(age_s=age,position_m=position,velocity_m_s=velocity)

class LandingGuardTests(unittest.TestCase):
    def test_activation_is_landing_only_and_short_outages_do_not_change_reference(self):
        guard=LandingGuard()
        for t,age in ((18.,2.),(40.,.515),(40.1,.595)):
            phase,target=scheduled_target(t);s=guard.step(t,phase,target,capture(age))
            self.assertEqual(s['mode'],'inactive');self.assertEqual(s['target_m'],target)
        s=guard.step(40.58,'landing',(0.,0.,.1),capture(.6))
        self.assertEqual(s['mode'],'holding');self.assertEqual(s['target_m'],(0.,0.,.3))
        self.assertEqual(s['activated_at_s'],40.58)
        self.assertEqual(s['target_velocity_m_s'],(0.,)*3)

    def test_fresh_stable_dwell_resets_on_age_speed_or_position_and_quintic_is_smooth(self):
        g=LandingGuard();g.step(40.58,'landing',(0.,0.,.1),capture(.6))
        g.step(42.,'landing',(0.,0.,.1),capture())
        for t,c in ((42.1,capture(.02)),(42.3,capture(position=(.201,0.,.3))),(42.5,capture(velocity=(.201,0.,0.)))):
            g.step(t-.05,'landing',(0.,0.,.1),capture())
            s=g.step(t,'landing',(0.,0.,.1),c);self.assertIsNone(s['resumed_at_s'])
            self.assertEqual(s['stable_for_s'],0.)
        g.step(42.6,'landing',(0.,0.,.1),capture())
        s=g.step(42.9,'landing',(0.,0.,.1),capture(.015,position=(.2,0.,.3),velocity=(.2,0.,0.)))
        self.assertEqual(s['mode'],'descending');self.assertEqual(s['resumed_at_s'],42.9)
        self.assertEqual(s['target_m'][2],.3);self.assertEqual(s['target_velocity_m_s'],(0.,)*3)
        mid=g.step(44.9,'landing',(0.,0.,.1),capture())
        self.assertAlmostEqual(mid['target_m'][2],.135)
        self.assertAlmostEqual(mid['target_velocity_m_s'][2],-.33*1.875/4)
        self.assertAlmostEqual(mid['target_acceleration_m_s2'][2],0.)
        end=g.step(46.9,'landing',(0.,0.,-.03),capture())
        self.assertAlmostEqual(end['target_m'][2],-.03)
        self.assertEqual(end['target_velocity_m_s'],(0.,)*3)
        self.assertEqual(end['target_acceleration_m_s2'],(0.,)*3)

    def test_renewed_outage_restarts_hold_and_landed_phase_has_precedence(self):
        g=LandingGuard();g.step(40.,'landing',(0.,0.,.4),capture(.6))
        g.step(42.,'landing',(0.,0.,.1),capture());g.step(42.3,'landing',(0.,0.,.1),capture())
        s=g.step(43.,'landing',(0.,0.,.1),capture(.6));self.assertEqual(s['mode'],'holding');self.assertIsNone(s['resumed_at_s'])
        s=g.step(43.1,'landed',(0.,0.,.05),capture(2.));self.assertEqual(s['mode'],'complete')
        self.assertEqual(s['target_m'],(0.,0.,.05));self.assertEqual(s['target_velocity_m_s'],(0.,)*3)

    def test_evidence_reconstructs_commands_and_keeps_original_scoring_targets(self):
        with tempfile.TemporaryDirectory() as root:
            path=record(fixture('hold-dropout-2000ms',predictive=True,guarded=True,count=8800),root)
            original=read_run(path);self.assertEqual(original['manifest.json']['schema_version'],9)
            s=original['samples.json'][8200]
            self.assertEqual(s['target_m'],list(scheduled_target(41.)[1]))
            self.assertEqual(s['landing_guard']['target_m'][2],.3)
            self.assertNotEqual(s['target_m'],s['landing_guard']['target_m'])
            bad=copy.deepcopy(original['config.json']);bad['landing_guard_model']['trigger_age_s']=.5
            with self.assertRaises(ValidationError):validate_config(bad,original['manifest.json'])
            for change in (lambda s:s['landing_guard'].update(mode='inactive'),lambda s:s['landing_guard'].update(target_m=[0,0,.8]),lambda s:s.update(target_m=s['landing_guard']['target_m']),lambda s:s['landing_guard'].update(private_path='private')):
                samples=copy.deepcopy(original['samples.json']);change(samples[8200]);data=encoded(samples)
                (path/'samples.json').write_bytes(data)
                checks=json.loads((path/'checksums.json').read_text(encoding='utf-8'));checks['samples.json']=sha256(data)
                (path/'checksums.json').write_bytes(encoded(checks))
                with self.assertRaises(ValidationError):read_run(path)

    def test_inactive_guard_is_exact_and_live_metadata_is_bounded(self):
        a=fixture('sample-hold',predictive=True);b=fixture('sample-hold',predictive=True,guarded=True)
        self.assertEqual(a['samples'],[{k:v for k,v in s.items() if k!='landing_guard'} for s in b['samples']])
        packet=FlightClock().snapshot(73,.005,b['samples'][-1],observation_profile='sample-hold')
        self.assertEqual(packet['schema_version'],5);validate_snapshot(packet)
        packet['sample']['landing_guard']['stable_for_s']=float('nan')
        with self.assertRaises(ValidationError):validate_snapshot(packet)

if __name__=='__main__':unittest.main()
