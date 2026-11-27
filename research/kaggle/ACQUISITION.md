# Reproducible acquisition of Spider and BIRD (E01-03, #21)

`python -m sqltoviz_data.acquire spider bird_dev [bird_train] --root data [--no-extract]` downloads each archive, enforces the pinned size and SHA256 from `manifests/sources.json` (mismatch ⇒ file deleted and run rejected), extracts with zip-slip protection, and writes everything under `data/cc-by-sa-4.0/` (license namespace kept separate from other sources). Nothing under `data/` is committed.

## Pinned artifacts (verified 2026-11-27)
| Source | Size (bytes) | SHA256 |
|---|---|---|
| Spider (Google Drive id 1403EGqz…) | 205 800 266 | `00636695dabed6b5f4b8328a16b13e069a2f16591d5efcce57660669c85b121b` |
| BIRD dev.zip | 346 207 293 | `cdd6d19faeb45a23970b98d3ef6c40a87987c95459c2cf12076897a60cf5a630` (matches upstream Content-MD5 `04b4af22…ec`) |
| BIRD train.zip | 8 919 543 554 | `66e9e3115b59559554013aa3b124156249f30437a6b4e4f96de3d2dfb5ae8cbc` |

Caveats stated honestly: the BIRD train hash comes from one full download (size equals upstream Content-Length and `unzip -t` reports no errors); upstream publishes only a multipart ETag, so it is **trust-on-first-use**, not independently confirmed. Spider is served from a Google Drive link that can change or be rate-limited; if the hash ever differs, the run fails closed.

## Evidence
- `pytest tests/test_acquire.py` → 11 passed (happy path, `__MACOSX` skipped, checksum/size mismatch rejected and deleted, unpinned refused unless trust-on-first-use, zip-slip variants rejected, idempotent rerun, verify-only mode, manifest well-formed).
- Real runs: Spider extracted (922 files: 166 database folders in `database/`, 7000 train and 1034 dev examples); BIRD dev extracted (11 SQLite databases, 1534 examples; nested `dev_databases.zip` handled); BIRD train verified with `--no-extract`.
- Spider train ∩ BIRD dev databases share `formula_1` (see SPLITS.md).

## License notes
Both corpora are CC BY-SA 4.0 (see DATASET_LICENSE_AUDIT.md): keep attribution and ShareAlike for any derivative published from `cc-by-sa-4.0/`.
