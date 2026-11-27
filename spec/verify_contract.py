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
