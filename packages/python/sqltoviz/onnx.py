"""Optional inference loader; no model is bundled in alpha."""
from pathlib import Path
import hashlib

def load_session(path, expected_sha256, *, kind):
    if kind not in ("chart","role"): raise ValueError("kind must be chart or role")
    path=Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected_sha256.lower():
        raise ValueError("model checksum mismatch")
    import onnxruntime as ort
    session=ort.InferenceSession(str(path),providers=["CPUExecutionProvider"])
    names=("table_features","chart_scores",32,10) if kind=="chart" else ("column_features","role_scores",28,5)
    inputs,outputs=session.get_inputs(),session.get_outputs()
    for nodes,name,width in [(inputs,names[0],names[2]),(outputs,names[1],names[3])]:
        if len(nodes)!=1 or nodes[0].name!=name or nodes[0].type!="tensor(float)" or len(nodes[0].shape)!=2 or nodes[0].shape[1]!=width:
            raise ValueError("incompatible model schema")
    return session
