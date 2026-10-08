"""Opt-in ground-contact instrumentation; never feeds the controller."""
import math
import os
import time
from pathlib import Path

from .contracts import load_json
from .evidence import read_run, require
from .simulation import encoded, sha256

COLUMNS = ['time_s', 'normal_x_n', 'normal_y_n', 'normal_z_n',
           'friction_x_n', 'friction_y_n', 'friction_z_n', 'peak_friction_anchors',
           'applied_x_n', 'applied_y_n', 'applied_z_n']
CAPACITY = 64


def validate_rows(rows, count=None):
    require(isinstance(rows, list) and 1 <= len(rows) <= 10001, 'invalid contact rows')
    if count is not None:
        require(len(rows) == count, 'contact coverage differs')
    for i, row in enumerate(rows):
        require(isinstance(row, list) and len(row) == 11 and
                all(type(v) in (int, float) and math.isfinite(v) for v in row), 'invalid contact row')
        require(abs(row[0]-i*.005) < 1e-8, 'contact time grid differs')
        require(type(row[7]) is int and 0 <= row[7] < CAPACITY, 'contact buffer saturated')
        require(row[3] >= -.001, 'invalid ground normal')
    require(all(v == 0 for v in rows[0]), 'initial contact interval must be empty')
    return rows


def write_capture(directory, run, rows, source, physics_dt):
    validate_rows(rows)
    value = {'schema_version': 1, 'kind': 'ground_contact_forces', 'columns': COLUMNS,
             'source': source, 'physics_dt_s': physics_dt, 'capacity': CAPACITY,
             'filter': 'ground', 'interval': 'preceding-control-interval-mean',
             'run_id': run.name,
             'checksums_sha256': sha256((run/'checksums.json').read_bytes()), 'rows': rows}
    (Path(directory)/(run.name+'-contact.json')).write_bytes(encoded(value))


def read_capture(directory, run_id):
    import re
    root = Path(directory)
    require(bool(re.fullmatch(r'isaac-ground-mission-wind-[0-9]+-[a-f0-9]{12}', run_id)), 'invalid contact run id')
    path = root/(run_id+'-contact.json')
    require(not path.is_symlink() and not root.is_symlink(), 'linked contact capture')
    value = load_json(path, 8*1024*1024)
    require(set(value) == {'schema_version','kind','columns','source','physics_dt_s','capacity','filter','interval','run_id','checksums_sha256','rows'}, 'invalid contact fields')
    require(value['schema_version'] == 1 and value['kind'] == 'ground_contact_forces' and value['columns'] == COLUMNS and
            value['capacity'] == CAPACITY and value['filter'] == 'ground' and value['interval'] == 'preceding-control-interval-mean' and
            value['run_id'] == run_id, 'invalid contact contract')
    run = read_run(root/run_id)
    require(value['checksums_sha256'] == sha256((root/run_id/'checksums.json').read_bytes()), 'contact flight digest differs')
    c, m, samples = run['config.json'], run['manifest.json'], run['samples.json']
    source = value['source']
    require(set(source) == {'source_commit','source_dirty','source_tree_sha256','lock_sha256'} and source['source_dirty'] is False and
            source['source_commit'] == m['source_commit'] and source['lock_sha256'] == m['lock_sha256'] and m['source_dirty'] is False, 'contact source differs or is dirty')
    require(all(isinstance(source[k], str) and re.fullmatch('[a-f0-9]{'+str(n)+'}', source[k]) for k,n in
                [('source_commit',40),('source_tree_sha256',64),('lock_sha256',64)]), 'invalid source hashes')
    require(value['physics_dt_s'] in (.005,.0025,.00125) and
            value['physics_dt_s'] == c['physics_options'].get('physics_dt_s',.005), 'contact timestep differs')
    validate_rows(value['rows'], len(samples))
    for row, sample in zip(value['rows'], samples):
        require(row[0] == sample['time_s'] and all(abs(a-b) < 1e-5 for a,b in
                zip(row[1:4],sample['contact_normal_force_n'])), 'filtered normal differs')
    return value, run


def validate_live(value):
    require(isinstance(value, dict) and set(value) == {'schema_version','seed','time_s','normal_n','friction_n','anchors','updated_monotonic_s'}, 'invalid contact live fields')
    require(value['schema_version'] == 1 and type(value['seed']) is int and 0 <= value['seed'] < 2**31 and
            type(value['anchors']) is int and 0 <= value['anchors'] < CAPACITY, 'invalid contact live identity')
    for k in ('time_s','updated_monotonic_s'):
        require(type(value[k]) in (int,float) and math.isfinite(value[k]) and value[k] >= 0, 'invalid contact live time')
    require(value['time_s'] <= 50, 'invalid contact duration')
    for k in ('normal_n','friction_n'):
        require(isinstance(value[k], list) and len(value[k]) == 3 and all(type(v) in (int,float) and math.isfinite(v) for v in value[k]), 'invalid contact force')
    return value


def write_live(directory, seed, row):
    value = validate_live({'schema_version':1,'seed':seed,'time_s':row[0],'normal_n':row[1:4],
                          'friction_n':row[4:7],'anchors':row[7],'updated_monotonic_s':time.perf_counter()})
    target = Path(directory)/'contact-live.json'
    temporary = target.with_suffix('.tmp')
    temporary.write_bytes(encoded(value))
    for attempt in range(3):
        try:
            os.replace(temporary,target)
            return
        except PermissionError:
            if attempt == 2:
                raise
            time.sleep(.001)
