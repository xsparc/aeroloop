"""Frozen landing-gain comparison with original gates and interval diagnostics."""
import math
from pathlib import Path
from .axis_feedback import PROFILES
from .approach_control import configuration
from .channel_quality import configuration as quality_configuration
from .diagnosis import gates
from .evidence import require
from .frames import rotate
from .outage_study import summarize
from .prediction_study import display
from .simulation import encoded, sha256
from .timing_study import read_study

COHORTS = {'regression': (0, 1, 2), 'stress': (401, 503, 607), 'additional': (709, 811, 907)}
COLUMNS = ('time_s','truth_x_m','truth_y_m','truth_vx_m_s','truth_vy_m_s',
    'feedback_x_m','feedback_y_m','feedback_vx_m_s','feedback_vy_m_s',
    'target_x_m','target_y_m','target_vx_m_s','target_vy_m_s',
    'integral_x_m_s2','integral_y_m_s2','feedforward_x_m_s2','feedforward_y_m_s2',
    'gain_blend','horizontal_kp_s2','horizontal_kd_s','clipped_ax_m_s2','clipped_ay_m_s2',
    'allocation_scale','wind_fx_n','wind_fy_n','thrust_fx_n','thrust_fy_n',
    'normal_n','clearance_m','truth_vz_m_s','landed','horizontal_error_m','horizontal_speed_m_s',
    'squared_error_integral_m2_s','squared_demand_integral_m2_s3','axis_clipped',
    'horizontal_energy_j','tilt_deg','truth_z_m','requested_thrust_n','realized_thrust_n','target_z_m')


def trace(samples):
    rows = []
    for s in samples:
        if s['time_s'] < 34:
            continue
        f = s['axis_feedback']; armed = s['mission_phase'] not in ('grounded','landed')
        blend, kp, kd = s.get('approach_control', (0., 2.5, 2.8))
        demand = [s['target_acceleration_m_s2'][a]+kp*(s['target_m'][a]-f['position_m'][a])
                  +kd*(s['target_velocity_m_s'][a]-f['velocity_m_s'][a])+s['integral_acceleration_m_s2'][a]
                  if armed else 0. for a in (0,1)]
        clipped = [max(-4., min(4., v)) for v in demand]
        error = math.dist(s['position_m'][:2], s['target_m'][:2])
        speed = math.hypot(*s['velocity_m_s'][:2])
        cumulative_error = cumulative_demand = 0.
        if rows:
            prev = rows[-1]; dt = s['time_s']-prev[0]
            cumulative_error = prev[33]+prev[31]**2*dt
            cumulative_demand = prev[34]+(prev[20]**2+prev[21]**2)*dt
        thrust = rotate(s['quaternion_wxyz'], (0.,0.,s['thrust_n']))
        x,y = s['quaternion_wxyz'][1:3]
        rows.append([s['time_s'],*s['position_m'][:2],*s['velocity_m_s'][:2],
            *f['position_m'][:2],*f['velocity_m_s'][:2],*s['target_m'][:2],
            *s['target_velocity_m_s'][:2],*s['integral_acceleration_m_s2'][:2],
            *s['target_acceleration_m_s2'][:2],blend,kp,kd,*clipped,s['allocation_scale'],
            *s['external_force_n'][:2],*thrust[:2],s['contact_normal_force_n'][2],
            s['support_clearance_m'],s['velocity_m_s'][2],int(s['mission_phase']=='landed'),
            error,speed,cumulative_error,cumulative_demand,int(any(abs(v)>4 for v in demand)),
            .5*speed**2,math.degrees(math.acos(max(-1., min(1.,1-2*(x*x+y*y))))),
            s['position_m'][2],s['thrust_setpoint_n'],s['thrust_n'],s['target_m'][2]])
    return rows


def diagnostics(rows):
    return {'samples':len(rows), 'complete':len(rows)==3201,
        'squared_error_integral_m2_s':rows[-1][33] if rows else None,
        'squared_demand_integral_m2_s3':rows[-1][34] if rows else None,
        'axis_clipped_fraction':sum(r[35] for r in rows[:-1])/(len(rows)-1) if len(rows)>1 else None,
        'minimum_allocation_scale':min((r[22] for r in rows),default=None),
        'peak_horizontal_error_m':max((r[31] for r in rows),default=None)}


def gate_changes(a, b):
    require([g['id'] for g in a]==[g['id'] for g in b], 'gate definitions differ')
    return [{'id':x['id'], 'change':'unchanged' if x['status']==y['status'] else
             'improved' if y['status']=='passed' else 'regressed' if x['status']=='passed' else 'changed',
             'headroom_delta':y['headroom']-x['headroom'] if x['headroom'] is not None and y['headroom'] is not None else None}
            for x,y in zip(a,b)]


def study(directories):
    require(set(directories)==set(COHORTS),'incomplete approach cohorts')
    reports, documents, identity = [], {}, None
    common=lambda c:{k:v for k,v in c.items() if k!='trajectory_control'}
    for cohort,seeds in COHORTS.items():
        require(set(directories[cohort])=={'baseline','candidate'},'incomplete gain modes')
        modes, summaries = {}, {}
        for mode,version in (('baseline',12),('candidate',13)):
            runs,clocks=read_study(directories[cohort][mode],PROFILES,PROFILES[1:],version,seeds)
            summaries[mode]=summarize(runs,clocks,version,PROFILES,seeds);modes[mode]=runs
            source={k:summaries[mode][k] for k in ('source_commit','source_tree_sha256','controller_binary_sha256','lock_sha256','versions')}
            if mode=='candidate' or cohort=='additional':
                if identity is None:identity=source
                require(identity==source,'final approach source or runtime differs')
        require(all(summaries['baseline'][k]==summaries['candidate'][k] for k in ('controller_binary_sha256','lock_sha256','versions')),'baseline runtime differs')
        continuity, findings = [], []
        for profile in PROFILES:
            for seed in seeds:
                a,b=modes['baseline'][profile,seed],modes['candidate'][profile,seed]
                require(common(a['config.json'])==common(b['config.json']) and b['config.json']['axis_feedback_model']==quality_configuration('noise-delay'),'paired settings differ')
                normalized=[{k:v for k,v in s.items() if k!='approach_control'} for s in b['samples.json'][:6800]]
                require(len(normalized)==6800 and a['samples.json'][:6800]==normalized,'pre-ramp continuity failed')
                continuity.append({'profile':profile,'seed':seed,'samples':6800,'unchanged':True})
                findings.append({'profile':profile,'seed':seed,'gates':gate_changes(gates(a),gates(b)),
                    **{m:diagnostics(trace(r['samples.json'])) for m,r in (('baseline',a),('candidate',b))}})
        reports.append({'cohort':cohort,'seeds':list(seeds),'baseline':summaries['baseline'],'candidate':summaries['candidate'],
                        'continuity':continuity,'descriptive':findings})
        documents[cohort]=modes
    return {'schema_version':1,'kind':'isaac_approach_gain_study','new_flights':24,'retained_flights':12,
        'configuration':configuration(),'cohorts':reports,'accepted':all(r['candidate']['accepted'] for r in reports),
        'limitations':['Fixed small cohorts; stress seeds were previously observed; additional seeds predeclared',
            'Higher gains are an engineering hypothesis; synthetic wind and sensors are not calibrated',
            'Original mission, same-mode outage pair and recovery limits retained; default unchanged',
            'Ideal attitude, rates and contact supervisor; AL-010 yaw refinement remains open',
            'Command-demand integral is not physical energy; soft real-time simulation only']},documents


def export_demo(report, documents, output):
    output=Path(output);require(not output.exists(),'output already exists')
    payloads,cases={},[]
    for ci,(cohort,seeds) in enumerate(COHORTS.items()):
        summary=report['cohorts'][ci];require(summary['cohort']==cohort,'cohort order differs')
        for pi,profile in enumerate(PROFILES):
            for seed in seeds:
                identifier=f'{cohort}-p{pi}-s{seed}';sides={}
                for mode in ('baseline','candidate'):
                    run=documents[cohort][mode][profile,seed];m=run['manifest.json'];rows=trace(run['samples.json'])
                    original=next((c for c in summary[mode]['comparisons'] if c['profile']==profile and c['seed']==seed),None)
                    outage=None if original is None else {'passed':original['passed'],'recovery_passed':original['recovery_passed'],
                        'peak_distance_m':original.get('peak_position_difference_m'),'rmse_change_m':original.get('position_rmse_change_m'),
                        'landed_change_s':original.get('landed_time_change_s'),'recovery':[
                            {'time_s':w['recovery_time_s'],'passed':w['passed'],'complete':w['complete_horizon']} for w in original['recovery_windows']]}
                    provenance={k:m[k] for k in ('source_commit','source_tree_sha256','controller_binary_sha256','lock_sha256','config_sha256')}
                    provenance.update(samples_sha256=sha256(encoded(run['samples.json'])),versions=summary[mode]['versions'],source_dirty=False)
                    sides[mode]={'status':m['status'],'failure_reason':m['failure_reason'],'gates':gates(run),'rows':rows,
                        'poses':[{k:s[k] for k in ('time_s','position_m','target_m','quaternion_wxyz','mission_phase')} for s in display(run)],
                        'touchdown_s':run['metrics.json']['mission']['touchdown_time_s'],'landed_s':run['metrics.json']['mission']['landed_time_s'],
                        'diagnostics':diagnostics(rows),'outage':outage,'provenance':provenance}
                changes=gate_changes(sides['baseline']['gates'],sides['candidate']['gates'])
                body={'schema_version':1,'kind':'approach_comparison','id':identifier,'cohort':cohort,'profile':profile,'seed':seed,
                      'columns':list(COLUMNS),'configuration':configuration(),'gate_changes':changes,**sides}
                file=identifier+'.json';data=encoded(body);require(len(data)<=12*1024*1024,'approach pair exceeds size budget');payloads[file]=data
                cases.append({'id':identifier,'cohort':cohort,'profile':profile,'seed':seed,'file':file,'sha256':sha256(data),
                    **{mode+'_status':sides[mode]['status'] for mode in sides},'regressed_gates':sum(g['change']=='regressed' for g in changes),
                    'improved_gates':sum(g['change']=='improved' for g in changes)})
    payloads['index.json']=encoded({'schema_version':1,'kind':'approach_comparison_index','cases':cases})
    require(len(payloads['index.json'])<=16384 and sum(map(len,payloads.values()))<=192*1024*1024,'approach bundle exceeds size budget')
    output.mkdir(parents=True)
    for name,data in payloads.items():(output/name).write_bytes(data)
    return sha256(payloads['index.json'])
