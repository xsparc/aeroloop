import copy
import math
import unittest
from aeroloop.diagnosis import phase,phase_errors,headroom,trace
from aeroloop.contracts import ValidationError


class DiagnosisTests(unittest.TestCase):
    def test_phase_precedence_and_intermittent_contact(self):
        sample=dict(mission_phase='landing',thrust_setpoint_n=9.,contact_normal_force_n=[0.,0.,0.])
        self.assertEqual(phase(sample),1)
        sample['contact_normal_force_n'][2]=.11;self.assertEqual(phase(sample),2)
        sample.update(mission_phase='landed',thrust_setpoint_n=0.);self.assertEqual(phase(sample),3)
        sample['thrust_setpoint_n']=.001;self.assertEqual(phase(sample),2)
        sample['contact_normal_force_n'][2]=.1;self.assertEqual(phase(sample),0)

    def test_partition_boundaries_peak_times_empty_and_incomplete(self):
        rows=[]
        for i in range(399,802):
            r=[0.]*13;r[0]=38+i*.005;r[5]=3.;r[6]=4.;r[12]=1 if i<600 else 3;rows.append(r)
        result=phase_errors(rows)
        self.assertTrue(result['complete']);self.assertEqual(result['sample_count'],400)
        self.assertEqual([g['samples'] for g in result['groups']],[0,200,0,200])
        self.assertEqual(result['groups'][1]['vertical_peak_time_s'],40.)
        self.assertEqual(result['groups'][3]['vertical_peak_time_s'],41.)
        self.assertEqual(result['groups'][1]['vertical_rmse_m'],4.)
        self.assertIsNone(result['groups'][2]['horizontal_rmse_m'])
        truncated=phase_errors(rows[:4]);self.assertFalse(truncated['complete']);self.assertEqual(truncated['sample_count'],3)
        self.assertEqual(sum(g['samples'] for g in result['groups']),400)

    def test_signed_headroom_does_not_reinterpret_strict_or_missing_gates(self):
        for op,v,limit,expected in [('eq',3,4,-1),('eq',4,4,0),('lt',4,4,0),('ge',3,4,-1),('le',3,4,1),('abs_le',-5,4,-1)]:
            self.assertEqual(headroom(dict(operator=op,value=v,limit=limit)),expected)
        self.assertIsNone(headroom(dict(operator='le',value=None,limit=4)))

    def test_numeric_trace_preserves_truth_input_and_reference_separation(self):
        sample=dict(time_s=40.,position_m=[1.,2.,3.],observation={'position_m':[2.,3.,4.],'age_s':.02},
                    feedback={'position_m':[1.,2.,5.]},axis_feedback={'position_m':[4.,6.,5.]},
                    axis_observation={'age_s':.04},thrust_setpoint_n=9.,contact_normal_force_n=[0.,0.,0.],mission_phase='landing')
        before=copy.deepcopy(sample);ref={**sample,'position_m':[0.,0.,0.]}
        rows=trace([sample],[ref]);self.assertEqual(rows[0][:11],[40.,3.,4.,5.,5.,5.,2.,9.,0.,.02,.04])
        self.assertEqual(rows[0][11],math.sqrt(14));self.assertEqual(sample,before)
        with self.assertRaises(ValidationError):trace([sample],[])
        with self.assertRaises(ValidationError):trace([sample],[{**ref,'time_s':39.}])
