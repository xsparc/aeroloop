"""Horizontal landing diagnostics over verified, retained PhysX recordings."""
import json
import math
from pathlib import Path
import tempfile

from .decay_study import export_demo as export_descent
from .evidence import require
from .frames import rotate
from .simulation import encoded, sha256

DT = .005
START = 34.
COLUMNS = ('time_s', 'x_m', 'y_m', 'vx_m_s', 'vy_m_s',
           'feedback_x_m', 'feedback_y_m', 'feedback_vx_m_s', 'feedback_vy_m_s',
           'target_x_m', 'target_y_m', 'target_vx_m_s', 'target_vy_m_s',
           'integral_x_m_s2', 'integral_y_m_s2', 'feedforward_x_m_s2', 'feedforward_y_m_s2',
           'qw', 'qx', 'qy', 'qz', 'rotor_0_n', 'rotor_1_n', 'rotor_2_n', 'rotor_3_n',
           'wind_x_n', 'wind_y_n', 'previous_vx_m_s', 'previous_vy_m_s',
           'previous_thrust_x_n', 'previous_thrust_y_n', 'previous_wind_x_n', 'previous_wind_y_n',
           'p_x_m_s2', 'p_y_m_s2', 'd_x_m_s2', 'd_y_m_s2', 'clipped_x_m_s2', 'clipped_y_m_s2',
           'thrust_x_n', 'thrust_y_n', 'tilt_deg', 'yaw_deg', 'home_distance_m', 'horizontal_speed_m_s',
           'feedback_position_error_m', 'feedback_velocity_error_m_s', 'horizontal_energy_j',
           'residual_impulse_x_n_s', 'residual_impulse_y_n_s')


def trace(samples):
    """Mass is fixed at 1 kg in this study. Row t's impulse covers (t-dt,t]."""
    rows = []
    for i, s in enumerate(samples):
        if s['time_s'] < START:
            continue
        require(i > 0 and abs(s['time_s']-samples[i-1]['time_s']-DT) < 1e-9, 'missing preceding physics step')
        prev = samples[i-1]
        f = s['axis_feedback']; armed = s['mission_phase'] not in ('grounded', 'landed')
        p = [2.5*(s['target_m'][a]-f['position_m'][a]) if armed else 0. for a in (0, 1)]
        d = [2.8*(s['target_velocity_m_s'][a]-f['velocity_m_s'][a]) if armed else 0. for a in (0, 1)]
        integral = s['integral_acceleration_m_s2'][:2]; ff = s['target_acceleration_m_s2'][:2]
        clipped = [max(-4., min(4., p[a]+d[a]+integral[a]+ff[a])) for a in (0, 1)]
        q = s['quaternion_wxyz']; w, x, y, z = q
        thrust = rotate(q, (0., 0., s['thrust_n']))
        previous_thrust = rotate(prev['quaternion_wxyz'], (0., 0., prev['thrust_n']))
        residual = [s['velocity_m_s'][a]-prev['velocity_m_s'][a]-DT*(previous_thrust[a]+prev['external_force_n'][a]) for a in (0, 1)]
        rows.append([s['time_s'], *s['position_m'][:2], *s['velocity_m_s'][:2],
                     *f['position_m'][:2], *f['velocity_m_s'][:2], *s['target_m'][:2],
                     *s['target_velocity_m_s'][:2], *integral, *ff, *q, *s['rotor_thrust_n'],
                     *s['external_force_n'][:2], *prev['velocity_m_s'][:2], *previous_thrust[:2],
                     *prev['external_force_n'][:2], *p, *d, *clipped, *thrust[:2],
                     math.degrees(math.acos(max(-1., min(1., 1-2*(x*x+y*y))))),
                     math.degrees(math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))),
                     math.hypot(*s['position_m'][:2]), math.hypot(*s['velocity_m_s'][:2]),
                     math.hypot(*(f['position_m'][a]-s['position_m'][a] for a in (0, 1))),
                     math.hypot(*(f['velocity_m_s'][a]-s['velocity_m_s'][a] for a in (0, 1))),
                     .5*sum(v*v for v in s['velocity_m_s'][:2]), *residual])
    return rows


def phase_metrics(rows, start, end, complete):
    """State endpoints are inclusive; impulse integration uses (start,end]."""
    if start is None or end is None or end < start:
        return None
    selected = [r for r in rows if start-1e-9 <= r[0] <= end+1e-9]
    if not selected:
        return None
    a, b = selected[0], selected[-1]
    intervals = selected[1:]
    return {'start_s': start, 'end_s': end, 'state_samples': len(selected),
            'complete': complete and abs(a[0]-start) < 1e-9 and abs(b[0]-end) < 1e-9,
            'displacement_xy_m': [b[c]-a[c] for c in (1, 2)],
            'distance_change_m': b[43]-a[43], 'peak_speed_m_s': max(r[44] for r in selected),
            'energy_change_j': b[47]-a[47], 'momentum_change_n_s': [b[c]-a[c] for c in (3, 4)],
            'thrust_impulse_n_s': [sum(r[c]*DT for r in intervals) for c in (29, 30)],
            'wind_impulse_n_s': [sum(r[c]*DT for r in intervals) for c in (31, 32)],
            'residual_impulse_n_s': [sum(r[c] for r in intervals) for c in (48, 49)]}


def phases(rows, touchdown, landed):
    last = rows[-1][0] if rows else None
    return {'approach': phase_metrics(rows, START, touchdown if touchdown is not None else last, touchdown is not None),
            'contact_to_disarm': phase_metrics(rows, touchdown, landed if landed is not None else last, landed is not None),
            'disarmed': phase_metrics(rows, landed, last, last == 50.)}


def export_demo(report, documents, output):
    """Re-use the full descent contract; add allowlisted 200 Hz landing rows."""
    output = Path(output); require(not output.exists(), 'output already exists')
    payloads = {}; findings = []
    with tempfile.TemporaryDirectory() as root:
        base = Path(root)/'descent'
        export_descent(report, documents, base)
        index = json.loads((base/'index.json').read_text(encoding='utf-8'))
        index['kind'] = 'landing_contact_index'
        for entry in index['cases']:
            descent = json.loads((base/entry['file']).read_text(encoding='utf-8'))
            body = {'schema_version': 1, 'kind': 'landing_contact', 'columns': list(COLUMNS), 'descent': descent}
            finding = {'id': entry['id']}
            for mode in ('baseline', 'candidate'):
                run = documents[entry['cohort']][mode][entry['profile'], entry['seed']]
                require(run['config.json']['model']['mass'] == 1. and run['config.json']['dt_s'] == DT,
                        'contact diagnostics require the fixed mass and cadence')
                rows = trace(run['samples.json']); body[mode] = rows
                side = descent[mode]
                entry[mode+'_support_error_m'] = next(g['value'] for g in side['gates'] if g['id']=='final_support_peak_xy_error_m')
                at = lambda t: next((r for r in rows if t is not None and abs(r[0]-t)<1e-9), None)
                def checkpoint(t):
                    r = at(t)
                    return None if r is None else {'time_s': t, 'home_distance_m': r[43], 'speed_m_s': r[44],
                        'tilt_deg': r[41], 'horizontal_energy_j': r[47]}
                finding[mode] = {'status': side['status'], 'provenance': side['provenance'],
                    'touchdown': checkpoint(side['touchdown_s']), 'disarm': checkpoint(side['landed_s']),
                    'final_support_error_m': entry[mode+'_support_error_m'],
                    'phases': phases(rows, side['touchdown_s'], side['landed_s'])}
            data = encoded(body); require(len(data)<=24*1024*1024, 'contact case exceeds size budget')
            payloads[entry['file']] = data; entry['sha256'] = sha256(data); findings.append(finding)
    payloads['index.json'] = encoded(index)
    require(len(payloads['index.json'])<=16384 and sum(map(len,payloads.values()))<=192*1024*1024, 'contact bundle exceeds size budget')
    output.mkdir(parents=True)
    for name, data in payloads.items():
        (output/name).write_bytes(data)
    return {'schema_version': 1, 'kind': 'landing_contact_analysis', 'new_flights': 0, 'retained_flights': 24,
            'demo_index_sha256': sha256(payloads['index.json']), 'payload_bytes': sum(map(len,payloads.values())),
            'cases': findings, 'interpretation': 'Descriptive retained-flight analysis; no controller change or new acceptance result.'}
