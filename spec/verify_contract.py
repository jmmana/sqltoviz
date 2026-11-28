import hashlib,json,pathlib
p=pathlib.Path(__file__).with_name('sqlvizspec-v1-features.json')
b=p.read_bytes(); d=json.loads(b)
assert d['status']=='frozen'
for key,n in [('sql_features',16),('global_features',16),('column_features',28)]:
    f=d[key]; assert len(f)==n and [x['index'] for x in f]==list(range(n))
    assert len({x['name'] for x in f})==n
    for x in f:
        assert x['dtype']=='float32' and x['range'][0]<=x['default']<=x['range'][1] and x['formula'] and x['null_policy']
assert len(d['model_io']['base_classes'])==10 and len(d['model_io']['roles'])==5
print(hashlib.sha256(b).hexdigest())

# additive outputs extension (SqlVizSpec-Outputs-v1.0.0): pinned separately, bound to the base hash above
OUT_PINNED = "45581c7b4414fc6250fb57988e04811bc4492fb1bbc21841058589481cce01db"
ob = pathlib.Path(__file__).with_name('sqlvizspec-v1-outputs.json').read_bytes()
od = json.loads(ob)
assert hashlib.sha256(ob).hexdigest() == OUT_PINNED, 'outputs spec bytes changed'
assert od['base_contract_sha256'] == hashlib.sha256(b).hexdigest()
assert od['contract_version'] == 'SqlVizSpec-Outputs-v1.0.0' and len(od['outputs']) == 21 and od['status'] == 'frozen'
assert set(od['specialization']) == set(d['model_io']['base_classes'])
assert {o for v in od['specialization'].values() for o in v} == set(od['outputs']) == set(od['outputs_definition'])
for o, df in od['outputs_definition'].items():
    assert all(p['reason'] in od['reason_codes'] for p in df['preconditions']) and df['channels'], o
print(OUT_PINNED)
