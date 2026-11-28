"""LLM-as-recommender baseline (#93) on the reserved 100, scored against the LLM-reference truth (declared design, no human labels).
Usage: run_llm_recommender.py RESERVE_ITEMS_JSONL --provider anthropic|openai --model MODEL [--out PATH]
       run_llm_recommender.py RESERVE_ITEMS_JSONL --replay RESPONSES_JSONL --model NAME      re-score logged responses offline
Needs an API key in the environment: ANTHROPIC_API_KEY (provider anthropic) or OPENAI_API_KEY (provider openai). Without a key the
tool writes NO numbers: it writes reports/llm_recommender_status.json with status "not_run" and the exact requirement, and exits 2.
Prompt: llm_baseline.TEMPLATE (version llm-baseline-v1, SHA256 recorded). The blind annotation runs used a different prompt
(GUIDELINES_BLIND_PILOT.md) and are references, not this baseline. CIRCULARITY: if the model evaluated is also one of the annotators
(a Claude or GPT model), its score against the LLM reference is inflated by construction; the report says so."""
import argparse, json, os, sys, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqltoviz_data import confirmatory as C, llm_baseline as B, llm_reference as L
here = os.path.join(os.path.dirname(__file__), "..")
ap = argparse.ArgumentParser(); ap.add_argument("items"); ap.add_argument("--provider", choices=["anthropic", "openai"]); ap.add_argument("--model", required=True)
ap.add_argument("--replay"); ap.add_argument("--out", default=f"{here}/reports/llm_recommender_reserved100.json"); a = ap.parse_args()
reserve = set(json.load(open(f"{here}/annotations/human_validation_reserve_ids.json")))
items = [i for i in map(json.loads, open(a.items)) if i["item_id"] in reserve]
items = [{k: i[k] for k in ("item_id", "db_id", "sql", "columns", "rows")} for i in items]


def post(url, headers, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"content-type": "application/json", **headers})
    return json.load(urllib.request.urlopen(req, timeout=120))


if a.replay:
    logged = {d["item_id"]: d["response"] for d in map(json.loads, open(a.replay))}
    call_for = lambda it: logged[it["item_id"]]
else:
    envk = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}.get(a.provider or "")
    key = os.environ.get(envk or "")
    if not key:
        st = {"status": "not_run", "reason": f"no API key in the environment ({envk or 'ANTHROPIC_API_KEY or OPENAI_API_KEY'}); no numbers were produced",
              "needs": ["a provider API key exported as ANTHROPIC_API_KEY or OPENAI_API_KEY", "network access to the provider", "a model id passed with --model (recorded in the report)"],
              "prompt_version": B.PROMPT_VERSION, "prompt_sha256": B.PROMPT_SHA256, "n_items": len(items),
              "note": "run once per model; temperature 0; responses are logged beside the report so the run can be re-scored with --replay"}
        json.dump(st, open(f"{here}/reports/llm_recommender_status.json", "w"), indent=1); print(json.dumps(st, indent=1)); sys.exit(2)
    def call_for(it):
        p = B.build_prompt(it)
        if a.provider == "anthropic":
            r = post("https://api.anthropic.com/v1/messages", {"x-api-key": key, "anthropic-version": "2023-06-01"},
                     {"model": a.model, "max_tokens": 300, "temperature": 0, "messages": [{"role": "user", "content": p}]})
            return r["content"][0]["text"]
        r = post("https://api.openai.com/v1/chat/completions", {"authorization": f"Bearer {key}"},
                 {"model": a.model, "temperature": 0, "messages": [{"role": "user", "content": p}]})
        return r["choices"][0]["message"]["content"]
recs = B.run(items, call_for, a.model)
log = os.path.splitext(a.out)[0] + "_responses.jsonl"
with open(log, "w") as f:
    for r in recs: f.write(json.dumps({"item_id": r.item_id, "model": r.model, "prompt_sha256": r.prompt_sha256, "response": r.response}) + "\n")
ref = L.reference(L.load_annotators(here))
rep = {"provenance": C.LLM_REF, "confirmatory": False, "banner": C.BANNER[C.LLM_REF], "model": a.model, "provider": a.provider or "replay",
       "circularity_warning": "if this model is also an annotator of the reference, the score is inflated by construction",
       "score": B.score(recs, ref["truth"], {i["item_id"]: i["db_id"] for i in items}), "ties_excluded": ref["unresolved"], "responses_log": os.path.basename(log)}
print("wrote", C.write_report(rep, a.out))
