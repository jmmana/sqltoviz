# Anomaly accuracy and numerical faithfulness (E08-08, #96) - Python SDK alpha

Script: `experiments/anomaly_faithfulness.py`; raw results: `results/anomaly_faithfulness.json` (seed 20261127). **Scope:** the Python detectors in `packages/python/sqltoviz/statistics.py` on synthetic Gaussian data with known injected outliers. TypeScript and .NET detectors and real data are **not** evaluated here.

## Numerical faithfulness (600 random cases, scales 1e-8..1e8, offsets, integer-valued variants)
| Detector | Independent reference | Max error |
|---|---|---|
| MAD median / MAD / modified z-scores | numpy median, `scipy.stats.median_abs_deviation(scale=1)` | 1.8e-16 relative; flagged set identical in every case |
| Pearson r | exact 80-digit `decimal` arithmetic on the same binary inputs | 4.6e-14 absolute (numpy's `corrcoef`: 3.3e-16) |
| temporal shifts (delta, relative change) | direct float recomputation | 0 |
| Pareto cumulative shares | numpy sort + cumsum | 1.7e-15 |
H8's threshold (1e-9) is met by every detector in this setting. The Pearson implementation is ~100x less accurate than numpy's (but still 1e-14): it is faithful, not optimal.
Degenerate inputs return explicit statuses instead of numbers: zero MAD -> `zero_mad`; fewer than 3 samples -> `insufficient_samples`; constant column -> `constant_column`; Pareto without additivity evidence -> `unknown_additivity`; negative weights -> `invalid_weights`; zero baseline -> `zero_baseline`.

## Injected-anomaly accuracy (200 trials per cell; n=100 shown, other sizes in the JSON)
Anomalies: +-magnitude sigma on a N(0,1) series. MAD = modified z-score threshold 3.5 (the SDK detector); z-score = classical |z|>3 with mean/SD.
| Contamination | magnitude | MAD recall / precision | z-score recall |
|---|---|---|---|
| 2 % | 4 sigma | 0.82 / 0.95 | 0.99 |
| 2 % | 6 sigma | 1.00 / 0.95 | 1.00 |
| 10 % | 4 sigma | 0.54 / 0.995 | 0.00 |
| 10 % | 6 sigma | 1.00 / 0.999 | 0.05 |
| 20 % | 6 sigma | 0.99 / 1.00 | 0.00 |
| 20 % | 4 sigma | 0.18 / 0.999 | 0.00 |
Reading: with sparse, strong outliers both work (z-score recalls slightly more at 4 sigma, 2 %); as contamination grows the classical z-score is masked by the outliers' own inflation of mean/SD while MAD stays robust. Weak outliers (4 sigma) at high contamination are mostly missed by either method. Detection accuracy depends entirely on the injected setting; no claim about real data.

## False alarms on clean Gaussian series (2000 series per size)
Share of series with at least one flagged point: 10.6 % (n=20), 9.9 % (n=100), 38.8 % (n=1000); point-level false-positive rate: 0.75 %, 0.12 %, 0.05 %. The fixed threshold gives a low per-point rate but a high per-series rate for long series: insights should be presented as candidates, not alarms.

## Still open for #96
Equivalent runs for the TypeScript and .NET detectors (parity fixtures exist in their own packages; faithfulness against the exact reference was not measured here), real-data anomaly labels, and accuracy of the narrative insight text.
