# Detector numerical faithfulness in all three runtimes (E08-08, #96)

Extends ANOMALY_FAITHFULNESS.md (Python, numpy/scipy/decimal references) to TypeScript and .NET with the **same 1,500 random cases** and **exact rational/decimal references** (`parity/tools/gen_faithfulness.py`: medians/MAD/shifts/Pareto via `fractions.Fraction`, Pearson via 120-digit `decimal`; boundary cases within 1e-9 of the MAD threshold or the Pareto coverage are excluded because they are decided by the last input bit). Each runtime replays the file (`SQLTOVIZ_FAITH=...`; CI job `golden-parity.yml`), compares statuses, outlier indices and included sets exactly, and reports its worst numerical error.

| Detector (error measure) | Python | TypeScript | .NET |
|---|---|---|---|
| MAD median/MAD/modified z-scores (relative) | 5.3e-14 | 5.3e-14 | 5.3e-14 |
| Pearson r (absolute) | 2.2e-16 | 6.7e-16 | 6.7e-16 |
| Temporal shifts delta / relative change (relative) | 2.2e-16 | 2.2e-16 | 2.2e-16 |
| Pareto share / cumulative (absolute) | 4.4e-16 | 5.6e-16 | 5.6e-16 |
Thresholds enforced in tests: 1e-12 relative (MAD, shifts), 1e-10 absolute (Pearson), 1e-12 (Pareto). Statuses, outlier index sets and Pareto inclusion sets were identical in every case and runtime. The shared 5.3e-14 MAD error comes from the even-count median `(a+b)/2` rounding, identical across runtimes.

Scope: synthetic inputs (scales 1e-8..1e8, offsets, integers, missing values), not real data labels; accuracy on injected anomalies is unchanged from ANOMALY_FAITHFULNESS.md (Python; the detector formulas are identical, so recall/precision follow from the same inputs). The accuracy of generated insight *text* remains unevaluated.
