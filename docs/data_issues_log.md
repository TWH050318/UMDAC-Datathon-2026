# Data issues log

Dataset: `swift_umdac_datathon_2026_fictitious_payment_data.csv` — 10,000,000 rows, 21 columns, 4.95 GB.
Period covered: 2023-04-30 11:22 UTC to 2023-07-31 09:56 UTC. Evidence: `notebooks/00_data_quality.ipynb`.

| # | Issue found | Decision | Why | Effect on findings |
|---|---|---|---|---|
| 1 | Column `DISCLAIMER` (not in the appendix) holds a legal notice on row 1 and is NULL on all other rows | Dropped | Carries no payment information | None |
| 2 | `ANOMALY_TYPE` is NULL for 9,992,994 rows (99.93%) | Kept; recoded as `NONE` and described as **unlabelled** | NULL means no anomaly was recorded; the case study calls labelling optional, so these rows are not verified legitimate | Comparisons of anomalies are against unlabelled payments; some unlabelled rows may be undetected anomalies |
| 3 | Label `CUSTOMER_RECALL` (317 rows) exists in the data but is not described in the case study | Kept and analysed as a sixth anomaly type | It is part of the generated data | Its meaning is our interpretation only |
| 4 | Path does not start at `ORDERING_BIC8` in 498,399 rows (4.98%); does not end at `BENEFICIARY_BIC8` in 499,265 rows (4.99%) | Kept, flagged with `PATH_FIRST_IS_ORD` / `PATH_LAST_IS_BEN` | Rates are almost exactly 5% and independent of each other, so this looks generated, not an error | Country-based analyses must say whether they use the BIC columns or the path |
| 5 | 23 amounts have more than 2 decimals | Kept unchanged | Negligible count; likely floating-point conversion | None |
| 6 | One pair of rows is identical on time, currency, amount, both accounts and path | Kept | May be a deliberate duplicate | None |
| 7 | Extreme amounts: 293 rows above USD 100M (161 labelled fat-finger, 132 unlabelled) | Kept; amounts analysed on a log scale and with medians | Removing them would delete the fat-finger signal | Means are unstable; we report medians and log-means |
| 8 | Rows are in random order (correlation of file position with time = −0.0003) | `ROW_ID` added for traceability; sequences use `EPOCH_SECONDS` | Row order has no meaning | None |
| 9 | `*_DETAILS` contain embedded line breaks | Parsed with a quote-aware CSV reader; row count verified = 10,000,000 | A naive line-based reader would split records | None |
| 10 | Weekday and hour are computed in UTC | Local time is estimated from the data per country (notebook 02), not from an external time-zone table | Only the provided dataset may be used as primary data | Weekend effect in UTC blends time zones; treat its size as approximate |

| 11 | **Process issue (16 Nov), found in peer review.** Notebooks re-run on the team laptop reported 10,400,000 rows, 400,001 duplicate pairs and inflated anomaly counts. Cause: a 400,000-row test file (`part_test.parquet`) had been left in `data/processed/payments_features/` while copying data to the drive, and that copy of `src/config.py` was an older version that read every `*.parquet` file in the folder | Test file is now ignored by the code and should be deleted; `config.py` reads only `data_*.parquet`; `utils.py` now stops every notebook unless the data has exactly 10,000,000 rows with `ROW_ID` 0–9,999,999; the build scripts empty their output folder before writing. All notebooks re-run | The figures in `RULES_AND_SOURCES.txt` and `hypothesis_log.md` were always computed on the correct 10,000,000 rows; only the re-run notebook outputs on the drive were affected and have been replaced |

No row was deleted and no value was modified.
