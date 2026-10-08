"""Hash-bound contact exports and interval momentum/work diagnostics."""
import math
from pathlib import Path

from .contact_forces import read_capture
from .contracts import load_json
from .diagnosis import gates
from .evidence import require
from .simulation import encoded, sha256

COLUMNS = ['time_s','x_m','y_m','z_m','qw','qx','qy','qz','vx_m_s','vy_m_s','vz_m_s',
           'nx_n','ny_n','nz_n','fx_n','fy_n','fz_n','ax_n','ay_n','az_n',
           'residual_x_ns','residual_y_ns','residual_z_ns','without_friction_ns','with_friction_ns',
           'wind_work_j','thrust_work_j','friction_work_j','kinetic_change_j','work_residual_j',
           'friction_ratio','com_alignment','anchors','contact','landed','target_x_m','target_y_m','target_z_m']


def trace(samples, contact, mass=1., gravity=9.81):
    rows = []
    for i,(s,r) in enumerate(zip(samples,contact)):
        n,f,a = r[1:4],r[4:7],r[8:11]
        residual = [0.]*3
        before = after = wind = thrust = work = kinetic = remaining = 0.
        ratio = math.hypot(*f[:2])/n[2] if n[2] > .1 else None
        alignment = None
        if i:
            p = samples[i-1];dt = s['time_s']-p['time_s']
            residual = [mass*(s['velocity_m_s'][k]-p['velocity_m_s'][k])-dt*(a[k]+n[k]+f[k]-(mass*gravity if k==2 else 0)) for k in range(3)]
            before = math.hypot(*(residual[k]+dt*f[k] for k in range(3)))
            after = math.hypot(*residual)
            displacement = [s['position_m'][k]-p['position_m'][k] for k in range(2)]
            wind = sum(p['external_force_n'][k]*displacement[k] for k in range(2))
            thrust = sum((a[k]-p['external_force_n'][k])*displacement[k] for k in range(2))
            work = sum(f[k]*displacement[k] for k in range(2))
            kinetic = .5*mass*sum(s['velocity_m_s'][k]**2-p['velocity_m_s'][k]**2 for k in range(2))
            remaining = kinetic-wind-thrust-work
            vx,vy = [(s['velocity_m_s'][k]+p['velocity_m_s'][k])*.5 for k in range(2)]
            speed,force = math.hypot(vx,vy),math.hypot(*f[:2])
            if speed > .01 and force > 1e-6:
                alignment = max(-1.,min(1.,(vx*f[0]+vy*f[1])/speed/force))
        rows.append([s['time_s'],*s['position_m'],*s['quaternion_wxyz'],*s['velocity_m_s'],
                     *n,*f,*a,*residual,before,after,wind,thrust,work,kinetic,remaining,
                     ratio,alignment,r[7],int(n[2]>.1),int(s['mission_phase']=='landed'),*s['target_m']])
    return rows


def summary(rows, start=0., end=50.):
    require(0 <= start < end <= 50 and all(abs(v/.005-round(v/.005))<1e-7 for v in (start,end)), 'invalid contact window')
    require(rows[0][0] <= start and rows[-1][0] >= end, 'incomplete contact window')
    intervals = [r for r in rows if start < r[0] <= end]
    count = round((end-start)/.005)
    require(len(intervals)==count, 'contact interval gap')
    rms=lambda col: math.sqrt(sum(r[col]**2 for r in intervals)/count)
    aligned=[r[31] for r in intervals if r[31] is not None]
    return {'start_s':start,'end_s':end,'intervals':count,'contact_intervals':sum(r[33] for r in intervals),
            'momentum_without_friction_rms_ns':rms(23),'momentum_with_friction_rms_ns':rms(24),
            'peak_friction_n':max(math.hypot(*r[14:17]) for r in intervals),
            'peak_friction_ratio':max((r[30] for r in intervals if r[30] is not None),default=None),
            'mean_com_alignment':sum(aligned)/len(aligned) if aligned else None,'alignment_intervals':len(aligned),
            'peak_anchors':max(r[32] for r in intervals),
            **{COLUMNS[c]:sum(r[c] for r in intervals) for c in range(25,30)}}


def rejected_capture(session):
    """Describe a hash-intact rejected normal-force trace, without promoting it."""
    from .evidence import read_run, FILES
    root = Path(session)
    require(not (root/'result.json').exists(), 'completed session is not a rejected capture')
    runs = list(root.glob('isaac-ground-mission-wind-*'))
    runs = [p for p in runs if p.is_dir()]
    require(len(runs)==1 and not root.is_symlink() and not runs[0].is_symlink(), 'invalid rejected session')
    run=runs[0];checksums=load_json(run/'checksums.json',4096)
    require(set(checksums)==FILES,'invalid rejected checksums')
    data={}
    for name in FILES:
        path=run/name
        require(not path.is_symlink() and path.stat().st_size<=32*1024*1024,'invalid rejected file')
        require(sha256(path.read_bytes())==checksums[name],'rejected trace hash mismatch')
        data[name]=load_json(path)
    m,c,s=data['manifest.json'],data['config.json'],data['samples.json']
    require(m['source_dirty'] is False and m['scenario']=='ground-mission-wind' and c['seed']==301 and
            c['physics_options']['physics_dt_s']==.00125 and len(s)==10001,'unexpected rejected protocol')
    try:
        read_run(run)
    except ValueError as exc:
        require(str(exc)=='invalid ground normal force','different rejection reason')
    else:
        require(False,'rejected capture unexpectedly verified')
    bad=[r for r in s if r['contact_normal_force_n'][2]<-1e-6]
    require(bool(bad),'no rejected negative normal')
    return {'id':'ideal-intact-s301-dt1250','seed':301,'physics_dt_s':.00125,
            'status':'unverified','reason':'invalid_ground_normal_force',
            'first_invalid_time_s':bad[0]['time_s'],
            'minimum_normal_z_n':min(r['contact_normal_force_n'][2] for r in bad),
            'invalid_intervals':len(bad),'checksums_sha256':sha256((run/'checksums.json').read_bytes()),
            'source_commit':m['source_commit']}


def export(sessions, destination, rejected_sessions=()):
    destination = Path(destination)
    require(not destination.exists(), 'contact export already exists')
    documents, entries = {}, []
    for session in sessions:
        result = load_json(Path(session)/'result.json')
        require(result.get('kind') == 'isaac_quadrotor_flight', 'not a flight session')
        for trial in result['results']:
            capture,run = read_capture(session,trial['run_id'])
            c,m = run['config.json'],run['manifest.json']
            mode = 'scheduled' if m['schema_version']==13 else 'fixed' if m['schema_version']==12 else 'ideal'
            profile = c.get('observation_model',{}).get('profile','ideal')
            seed = c['seed'];dt = capture['physics_dt_s']
            id = f'{mode}-'+('outage' if profile=='hold-dropout-2000ms' else 'intact')+f'-s{seed}-dt{round(dt*1000000)}'
            require(id not in documents, 'duplicate contact case')
            rows = trace(run['samples.json'],capture['rows'],c['model']['mass'],c['model']['gravity'])
            metrics = summary(rows)
            document = {'schema_version':1,'kind':'friction_case','id':id,'seed':seed,'mode':mode,'profile':profile,
                        'physics_dt_s':dt,'ground_kind':capture['ground_kind'],'source':capture['source'],'controller_binary_sha256':m['controller_binary_sha256'],
                        'versions':c['simulator_versions'],'capture_sha256':sha256((Path(session)/(trial['run_id']+'-contact.json')).read_bytes()),
                        'flight_checksums_sha256':capture['checksums_sha256'],'columns':COLUMNS,'rows':rows,
                        'status':m['status'],'failure_reason':m['failure_reason'],'gates':gates(run),'summary':metrics}
            content = encoded(document);documents[id]=content
            entries.append({k:document[k] for k in ('id','seed','mode','profile','physics_dt_s','status','summary')} |
                           {'file':id+'.json','sha256':sha256(content)})
    require(1 <= len(entries) <= 24,'invalid contact case count')
    # A bundle is one frozen experiment; no mixed source/runtime hidden in its matrix.
    import json
    identity=lambda d: [d[k] for k in ('source','controller_binary_sha256','versions')]
    require(all(identity(json.loads(v))==identity(json.loads(next(iter(documents.values())))) for v in documents.values()),'contact identities differ')
    rejected=[rejected_capture(p) for p in rejected_sessions]
    require(len(rejected)<=1 and all(r['id'] not in documents and r['source_commit']==json.loads(next(iter(documents.values())))['source']['source_commit'] for r in rejected),'invalid rejected identity')
    destination.mkdir(parents=True)
    for id,content in documents.items():
        (destination/(id+'.json')).write_bytes(content)
    index = {'schema_version':1,'kind':'friction_index','cases':entries,'rejected':rejected}
    raw=encoded(index);(destination/'index.json').write_bytes(raw)
    return {'index_sha256':sha256(raw),'cases':len(entries),'rejected':len(rejected),'intervals':sum(e['summary']['intervals'] for e in entries)}
