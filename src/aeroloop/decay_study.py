"""Predeclared vertical-prediction experiment and full-rate descent diagnostics."""
import math
from pathlib import Path
from .axis_feedback import PROFILES
from .channel_quality import configuration as quality_configuration
from .diagnosis import gates
from .evidence import require
from .flight_study import compare
from .frames import rotate
from .outage_study import summarize
from .prediction_study import display
from .simulation import encoded, sha256
from .timing_study import read_study

COHORTS = {'regression':(0,1,2), 'additional':(401,503,607)}
COLUMNS = ('time_s','truth_z_m','feedback_z_m','truth_vz_m_s','feedback_vz_m_s','target_z_m',
           'target_vz_m_s','position_term_m_s2','velocity_term_m_s2','feedforward_m_s2',
           'clipped_vertical_m_s2','requested_thrust_n','realized_thrust_n','world_vertical_thrust_n',
           'wind_vertical_force_n','contact_normal_n','clearance_m','contact_eligible','contact_dwell_s',
           'landed','decay_scale','anchor_z_m_s2','effective_z_m_s2','capture_age_s')


def without_decay(sample):
    return {k:v for k,v in sample.items() if k != 'vertical_decay'}


def trace(samples):
    rows, since = [], None
    for s in samples:
        t=s['time_s'];f=s['axis_feedback'];armed=s['mission_phase'] not in ('grounded','landed')
        p=2.5*(s['target_m'][2]-f['position_m'][2]) if armed else 0.
        d=2.8*(s['target_velocity_m_s'][2]-f['velocity_m_s'][2]) if armed else 0.
        ff=s['target_acceleration_m_s2'][2]
        eligible=t>=34 and s['contact_normal_force_n'][2]>.1 and s['support_clearance_m']<=.015 and abs(s['velocity_m_s'][2])<=.2
        since=(t if since is None else since) if eligible else None
        decay=s.get('vertical_decay',{})
        effective=s['feedback']['disturbance_acceleration_m_s2'][2]
        rows.append([t,s['position_m'][2],f['position_m'][2],s['velocity_m_s'][2],f['velocity_m_s'][2],
                     s['target_m'][2],s['target_velocity_m_s'][2],p,d,ff,max(-4.,min(4.,ff+p+d)),
                     s['thrust_setpoint_n'],s['thrust_n'],rotate(s['quaternion_wxyz'],(0.,0.,s['thrust_n']))[2],
                     s['external_force_n'][2],s['contact_normal_force_n'][2],s['support_clearance_m'],int(eligible),
                     t-since if since is not None else 0.,int(s['mission_phase']=='landed'),decay.get('scale',1.),
                     decay.get('anchor_z_m_s2',effective),effective,s['observation']['age_s']])
    return rows


def window_metrics(rows, start=40., end=42.):
    selected=[r for r in rows if start<=r[0]<end]
    return {'start_s':start,'end_s':end,'samples':len(selected),'complete':len(selected)==round((end-start)/.005),
            'vertical_velocity_error_rmse_m_s':math.sqrt(sum((r[4]-r[3])**2 for r in selected)/len(selected)) if selected else None,
            'peak_vertical_velocity_error_m_s':max((abs(r[4]-r[3]) for r in selected),default=None),
            'requested_thrust_impulse_n_s':sum(r[11]*.005 for r in selected),
            'realized_thrust_impulse_n_s':sum(r[12]*.005 for r in selected)}


def study(directories):
    require(set(directories)==set(COHORTS),'incomplete decay cohorts')
    reports, documents, identity = [], {}, None
    common=lambda c:{k:v for k,v in c.items() if k!='feedback_model'}
    for cohort,seeds in COHORTS.items():
        require(set(directories[cohort])=={'baseline','candidate'},'incomplete predictor modes')
        modes, summaries = {}, {}
        for mode,version in (('baseline',11),('candidate',12)):
            runs,clocks=read_study(directories[cohort][mode],PROFILES,PROFILES[1:],version,seeds)
            summaries[mode]=summarize(runs,clocks,version,PROFILES,seeds);modes[mode]=runs
            source={k:summaries[mode][k] for k in ('source_commit','source_tree_sha256','controller_binary_sha256','lock_sha256','versions')}
            if mode=='candidate' or cohort=='additional':
                if identity is None:identity=source
                require(identity==source,'final decay source or runtime differs')
        require(all(summaries['baseline'][k]==summaries['candidate'][k] for k in ('controller_binary_sha256','lock_sha256','versions')),'baseline runtime differs')
        continuity, comparisons, diagnostics = [], [], []
        for profile in PROFILES:
            for seed in seeds:
                a,b=modes['baseline'][profile,seed],modes['candidate'][profile,seed]
                require(common(a['config.json'])==common(b['config.json']) and b['config.json']['axis_feedback_model']==quality_configuration('noise-delay'),'paired settings differ')
                normalized=[without_decay(s) for s in b['samples.json']]
                cutoff=len(a['samples.json']) if profile==PROFILES[0] else 3600
                exact=a['samples.json'][:cutoff]==normalized[:cutoff]
                require(exact and len(normalized)>=cutoff,'normal-capture continuity failed')
                if profile==PROFILES[0]:require(a['metrics.json']==b['metrics.json'] and a['events.json']==b['events.json'] and len(normalized)==cutoff,'no-outage outcomes changed')
                continuity.append({'profile':profile,'seed':seed,'samples':cutoff,'unchanged':exact})
                comparisons.append({'profile':profile,'seed':seed,**compare(a,b)})
                diagnostics.append({'profile':profile,'seed':seed,**{mode:window_metrics(trace(modes[mode][profile,seed]['samples.json'])) for mode in modes}})
        reports.append({'cohort':cohort,'seeds':list(seeds),'baseline':summaries['baseline'],'candidate':summaries['candidate'],
                        'continuity':continuity,'cross_mode_descriptive':comparisons,'landing_windows':diagnostics})
        documents[cohort]=modes
    return {'schema_version':1,'kind':'isaac_vertical_decay_study','new_flights':18,'retained_flights':6,
            'cohorts':reports,'accepted':all(r['candidate']['accepted'] for r in reports),
            'limitations':['Small fixed seed cohorts; additional seeds were predeclared before this experiment',
                'Synthetic feedback and exponential forgetting are not calibrated wind or sensor models',
                'Ideal attitude, rates and contact supervisor; independent yaw refinement remains open',
                'Original mission, same-mode outage pair and sustained recovery limits retained',
                'Cross-mode comparisons and landing plots are descriptive, not replacement acceptance tests',
                'Soft real-time local simulation only; no hardware-flight validation']},documents


def export_demo(report, documents, output):
    """Export only reconstructed study documents, preserving failed and short runs."""
    output=Path(output);require(not output.exists(),'output already exists')
    require(set(documents)==set(COHORTS),'incomplete demo cohorts')
    payloads,cases={},[]
    for ci,(cohort,seeds) in enumerate(COHORTS.items()):
        summary=report['cohorts'][ci];require(summary['cohort']==cohort,'report cohort differs')
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
                        'window':window_metrics(rows),'outage':outage,'provenance':provenance}
                body={'schema_version':1,'kind':'descent_comparison','id':identifier,'cohort':cohort,'profile':profile,'seed':seed,'columns':list(COLUMNS),**sides}
                file=identifier+'.json';data=encoded(body);require(len(data)<=16*1024*1024,'descent pair exceeds size budget');payloads[file]=data
                cases.append({'id':identifier,'cohort':cohort,'profile':profile,'seed':seed,'file':file,'sha256':sha256(data),
                              **{mode+'_status':sides[mode]['status'] for mode in sides}})
    payloads['index.json']=encoded({'schema_version':1,'kind':'descent_comparison_index','cases':cases})
    require(len(payloads['index.json'])<=16384 and sum(map(len,payloads.values()))<=128*1024*1024,'descent bundle exceeds size budget')
    output.mkdir(parents=True)
    for name,data in payloads.items():(output/name).write_bytes(data)
    return sha256(payloads['index.json'])
