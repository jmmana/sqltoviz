# Dataset license and provenance audit (E01-01, #19)

Audit date: **2026-11-27**. Every row records *what was checked and how*; anything not verified is marked **UNRESOLVED**. This is an engineering audit, not legal advice. Machine-readable twin: [`provenance.json`](provenance.json).

## Summary

| Source | Role in SqlToViz | Declared license | Status | Redistribution of derived data |
|---|---|---|---|---|
| VizML / Plotly corpus | chart-type supervision on real data | **none declared** (repo `LICENSE` is 404; GitHub API `license: null`); corpus originates from the Plotly Community Feed | **BLOCKED** (see below) | **Not permitted until resolved** |
| Spider | NL/SQL + SQLite DBs | CC BY-SA 4.0 (data, per dataset page); code Apache-2.0 | OK with ShareAlike | Allowed under CC BY-SA 4.0 with attribution |
| BIRD | NL/SQL + DBs | CC BY-SA 4.0 (per dataset site) | OK with ShareAlike | Allowed under CC BY-SA 4.0 with attribution |
| TPC-H / TPC-DS (via TPC dbgen/dsdgen or DuckDB `tpch`/`tpcds`) | generated sample tables | TPC EULA v2.2.0 (software); DuckDB itself MIT | OK **with restrictions** | Software redistribution needs EULA terms; generated data: do not claim TPC-comparable results |

## Findings

### 1. VizML / Plotly — BLOCKED (impacts #20)
- Verified: `https://raw.githubusercontent.com/mitmedialab/vizml/master/LICENSE` returns 404; `gh api repos/mitmedialab/vizml` → `license: null`. Code and data therefore carry **no explicit grant**; default copyright applies.
- Verified: `retrieve_data.sh` downloads from `http://vizml-repository.s3.amazonaws.com/{features,plotly_subset_100k,plotly_subset_1k,plotly_full}.tar.gz`. On 2026-11-27 `GET` (range 0-1023) of `features.tar.gz`, `plotly_subset_100k.tar.gz` and `plotly_subset_1k.tar.gz` returned **HTTP 403 AccessDenied**. Upstream issues #4 ("100k dataset is unavailable") and #6 ("Unable to download the plotly dataset visualization pairs") report the same.
- Searched Kaggle (`kaggle datasets list -s vizml` → none) and Hugging Face (`vizml` → none). Only unrelated Plotly-image sets with no declared license were found; they are **not** equivalent and are not used.
- Corpus content is user-authored public Plotly charts; the paper's data redistribution terms are not stated in the repo.
- **Decision:** no VizML-derived file is committed, uploaded to a public Kaggle dataset, or used for a published number until (a) the data is obtainable from the authors or a mirror with a verifiable checksum, and (b) written permission or a clear license is obtained. Action items: ask the maintainers (mitmedialab/vizml) for license + a working link; fall back to other sources (below) if refused. The experiments must **not** claim to reproduce VizML results.
- Technical note: the corpus was extracted for Plotly chart types, not our 10-class taxonomy; a mapping to the 10 base classes needs independent annotation anyway (#24).

### 2. Spider
- Verified on `https://yale-lily.github.io/spider`: "distributed under the CC BY-SA 4.0 license"; `taoyds/spider` code is Apache-2.0 (GitHub API).
- Obligations: attribution, indicate changes, **ShareAlike** — derived datasets we publish must be CC BY-SA 4.0. Model weights are not clearly "adaptations" under CC BY-SA; this is an open legal question to be stated in `model/` metadata rather than assumed.
- The dataset page notes the corpus was corrected (dev/test annotations, 7 SQLite files). Record the exact downloaded archive SHA256 in #21.

### 3. BIRD
- Verified on `https://bird-bench.github.io/`: data license stated as **CC BY-SA 4.0**. `AlibabaResearch/DAMO-ConvAI` code is MIT (GitHub API); the repo's `bird/LICENSE` path returned 404, so the data license is taken from the website only.
- The test set ground truth is not public; only train/dev are usable. LiveSQLBench variants are out of scope.
- Underlying database contents were collected from third-party sources; per-database provenance is **UNRESOLVED** and must be listed from BIRD's own documentation before redistribution of any raw table values.

### 4. TPC-H / TPC-DS
- Verified: EULA v2.2.0 (`tpc.org/TPC_Documents_Current_Versions/txt/EULA_v2.2.0.txt`). Relevant clauses: §4.b modification of the Software allowed; §4.c performance results may be disclosed in academic/research efforts if they do not imply a marketing position, otherwise must be identified as **not comparable** to TPC Benchmark Results; §7 TPC trademarks; §9 redistribution of the Software only with the full EULA, the legend and no fee.
- **Decision:** generate samples locally with the TPC tools or DuckDB's `tpch`/`tpcds` extensions (DuckDB: MIT); distribute *scripts and seeds*, not the TPC software. Any latency number from these data is a SqlToViz measurement and must be labelled "not a TPC benchmark result". Scale factors, seeds and tool versions go in #22.

### 5. Own artifacts (synthetic SQL, annotations)
- Synthetic SQL (#25) and independent annotations (#24) are authored in this repository; license to be set with the project's code license (see repository root; **UNRESOLVED**: no root `LICENSE` file exists yet). Combined datasets containing Spider/BIRD rows must be CC BY-SA 4.0.

## Compatibility consequences
1. A public Kaggle dataset mixing Spider/BIRD material must be CC BY-SA 4.0 and carry attribution.
2. VizML-derived material is excluded from any public artifact until resolved; the pipeline must run (and report honestly) without it, or the training claim must be restricted to the sources actually available.
3. The ONNX model's license is not decided here; record the training-data licenses in `model/` metadata (#101).

## Reproduction of this audit
```
gh api repos/mitmedialab/vizml --jq .license
curl -s -o /dev/null -w "%{http_code}" -r 0-1023 http://vizml-repository.s3.amazonaws.com/features.tar.gz
curl -sL https://yale-lily.github.io/spider | grep -i "CC BY-SA"
curl -sL https://bird-bench.github.io/ | grep -i "CC BY-SA"
curl -sL https://www.tpc.org/TPC_Documents_Current_Versions/txt/EULA_v2.2.0.txt
```
