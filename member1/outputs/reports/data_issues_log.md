# Data Issues Log - Gate 1 Audit

- **Generated (UTC):** 2026-11-16T17:37:27+00:00
- **Source:** `swift_umdac_datathon_2026_fictitious_payment_data.csv` (4.61 GB)
- **Raw rows:** 10,000,000 | **Clean/parquet rows:** 10,000,000 | **Rows dropped:** 0
- **Method:** DuckDB `read_csv(all_varchar=true)` -> explicit `CAST` after a `TRY_CAST` failure audit (0 failures required, run aborts otherwise). All numbers below are printed by `src/01_data_prep_and_audit.py`.

## Summary of issues

| # | Issue | Rows affected | Decision |
| :-- | :-- | --: | :-- |
| 1 | Undocumented `DISCLAIMER` column (multi-line text) | 1 non-null | Isolated and excluded from parquet; no column shift |
| 2 | `ANOMALY_TYPE` is NULL for normal traffic | 9,992,994 | Filled with `'NORMAL'` |
| 3 | Label `CUSTOMER_RECALL` not listed in the schema reference | 317 | Kept; `is_anomaly=True`; flagged for team |
| 4 | Exact duplicate rows (all 20 data cols) | 1 surplus (2 in groups) | Flagged `is_exact_dup`; none dropped |
| 5 | `DUPLICATE_PAYMENT` labels vs exact duplicates | 679 labelled / 1 byte-identical | See section below |
| 6 | USD_AMOUNT <= 0 | 0 | None found; no action |
| 7 | Invalid CURRENCY_CODE (not 3 uppercase letters / NULL) | 0 | None |
| 8 | BIC8 length != 8 / NULL | 0 | None |
| 9 | Numeric cast failures | 0 | None - zero silent coercion |
| 10 | Leading-zero BIC8 (e.g. `0621US30`) | 9,832,750 (ordering side) | Kept as VARCHAR; hash-verified vs raw |
| 11 | Incomplete paths (`...` in BIC8_PATH) | 767,204 | Kept; `CONTINUITY_QFLAG='N'` rows = 767,204; disagreements = 0 |

## 1. `DISCLAIMER` column

Only 1 of 10,000,000 rows carry a value (row_id 1). Full text:

```text
WARNING: This dataset contains purely fictitious data that has been generated exclusively through hard-coded rules, NumPy 'random number' calls and the Python Faker library.
This dataset does not represent any real payment transactions, and therefore any resemblance to real data is purely coincidental.

Swift disclaims all liability for any decisions based on this dataset, and for their consequences.

This is a fictitious dataset created for the UMDAC Datathon 2026.

SWIFT © 2026. All rights reserved.
```

Column-shift check: 0 rows where `EPOCH_SECONDS` contains disclaimer text. Column excluded from `clean_payments.parquet`.

## 2. Null counts per raw column

| Column | NULL | Empty string |
| :-- | --: | --: |
| DISCLAIMER | 9,999,999 | 0 |
| EPOCH_SECONDS | 0 | 0 |
| CURRENCY_CODE | 0 | 0 |
| USD_AMOUNT | 0 | 0 |
| ORDERING_BIC8 | 0 | 0 |
| BENEFICIARY_BIC8 | 0 | 0 |
| BIC8_PATH | 0 | 0 |
| TOTAL_DURATION | 0 | 0 |
| CONTINUITY_QFLAG | 0 | 0 |
| CURRENCY_CONVERSION_COUNT | 0 | 0 |
| PARTICIPANT_COUNT | 0 | 0 |
| TRANSACTION_TYPE_CODE | 0 | 0 |
| ORDERING_ACCOUNT | 0 | 0 |
| BENEFICIARY_ACCOUNT | 0 | 0 |
| ORDERING_DETAILS | 0 | 0 |
| ORDERING_TOKENS | 0 | 0 |
| BENEFICIARY_DETAILS | 0 | 0 |
| BENEFICIARY_TOKENS | 0 | 0 |
| ORDERING_TYPE | 0 | 0 |
| BENEFICIARY_TYPE | 0 | 0 |
| ANOMALY_TYPE | 9,992,994 | 0 |

## 3. `ANOMALY_TYPE` distribution (after cleaning)

| ANOMALY_TYPE | Rows | % |
| :-- | --: | --: |
| NORMAL | 9,992,994 | 99.9299% |
| ROMANCE_SCAM | 2,476 | 0.0248% |
| FAT_FINGER_MISTAKE | 1,940 | 0.0194% |
| CEO_SCAM | 945 | 0.0095% |
| DUPLICATE_PAYMENT | 679 | 0.0068% |
| ACCOUNT_REPLACEMENT_SCAM | 649 | 0.0065% |
| CUSTOMER_RECALL | 317 | 0.0032% |

`CUSTOMER_RECALL` is present in the data but absent from the challenge schema notes; it is preserved as an anomaly label.

## 4. Exact duplicates vs `DUPLICATE_PAYMENT`

Duplicates are defined on all 20 data columns (including `ANOMALY_TYPE`) using an md5 key, verified collision-free by a full-tuple GROUP BY (1 groups). First occurrence is kept as `is_exact_dup=False`; later copies are `True`.

| ANOMALY_TYPE | Rows in dup group | Surplus (is_exact_dup) | Total |
| :-- | --: | --: | --: |
| NORMAL | 0 | 0 | 9,992,994 |
| ROMANCE_SCAM | 0 | 0 | 2,476 |
| FAT_FINGER_MISTAKE | 0 | 0 | 1,940 |
| CEO_SCAM | 0 | 0 | 945 |
| DUPLICATE_PAYMENT | 2 | 1 | 679 |
| ACCOUNT_REPLACEMENT_SCAM | 0 | 0 | 649 |
| CUSTOMER_RECALL | 0 | 0 | 317 |

**Finding:** 1 of 679 `DUPLICATE_PAYMENT` rows are byte-identical to an earlier row. 0 unlabelled rows are exact duplicates of an earlier row. Because duplicate detection includes `ANOMALY_TYPE`, a labelled row can only match another row carrying the same label; near-duplicates (e.g. same payment with a different timestamp) are for later analysis.

## 5. Extreme amounts vs `FAT_FINGER_MISTAKE`

NORMAL-row quantiles: p50=3,662.58, p99=1,211,077.85, p99.9=7,820,646.75, p99.99=33,415,933.67.

| Label | Rows | Min | Median | Max |
| :-- | --: | --: | --: | --: |
| NORMAL | 9,992,994 | 0.01 | 3,662.58 | 1,395,062,089.32 |
| ROMANCE_SCAM | 2,476 | 0.01 | 109.45 | 123,370.39 |
| FAT_FINGER_MISTAKE | 1,940 | 0.03 | 260,241.23 | 15,664,132,213.09 |
| CEO_SCAM | 945 | 0.12 | 20,602.13 | 88,481,911.15 |
| DUPLICATE_PAYMENT | 679 | 0.58 | 2,888.63 | 10,000,000.00 |
| ACCOUNT_REPLACEMENT_SCAM | 649 | 2.15 | 3,977.30 | 5,836,230.06 |
| CUSTOMER_RECALL | 317 | 1.87 | 3,163.97 | 12,855,757.01 |

Rows above the NORMAL p99.99 (33,415,933.67) by label: NORMAL=1,000; FAT_FINGER_MISTAKE=279; CEO_SCAM=2. No row removed.

## 6. Other structural checks

- USD_AMOUNT <= 0: 0 (negative 0, zero 0); NULL: 0
- TOTAL_DURATION < 0: 0
- Distinct CURRENCY_CODE: 155; format-invalid: 0 (format only; no external ISO table used)
- ORDERING_BIC8 == BENEFICIARY_BIC8: 2,387
- Complete paths whose segment count != PARTICIPANT_COUNT: 0
- EPOCH_SECONDS: 1682853746 -> 2023-04-30T11:22:26+00:00 ; 1690797361 -> 2023-07-31T09:56:01+00:00
- `ORDERING_TYPE` values: B=7,874,637, C=2,125,363
- `BENEFICIARY_TYPE` values: C=7,118,450, B=2,881,550
- `CONTINUITY_QFLAG` values: Y=9,232,796, N=767,204
- `TRANSACTION_TYPE_CODE` values: Direct=6,323,280, Indirect=3,260,758, Covered=415,962

## 7. Verification

- Raw 10,000,000 = clean 10,000,000 = parquet 10,000,000 rows.
- Hash-sum checks of 5 ID/BIC columns, 4 free-text columns and CURRENCY_CODE are identical between raw CSV text and parquet; sums of the 5 numeric columns match to double-precision rounding (relative error <= 1e-9; the EPOCH_SECONDS sum differs by 2 in 1.7e16, a float-summation artefact, while the epoch -> utc_dt round-trip has 0 mismatches).
- Anomaly label counts identical between raw CSV and parquet.

## 8. Engineered columns

| Column | Definition |
| :-- | :-- |
| `row_id` | 1-based file order of raw row |
| `utc_dt` | UTC timestamp (timezone-naive) from EPOCH_SECONDS |
| `utc_hour` | 0-23 |
| `utc_dow` | 0=Mon..6=Sun |
| `is_weekend` | Sat/Sun (UTC) |
| `party_pair` | ORDERING_TYPE + '2' + BENEFICIARY_TYPE |
| `ordering_country / beneficiary_country` | chars 5-6 of the BIC8 |
| `is_anomaly` | raw ANOMALY_TYPE was non-null |
| `is_exact_dup` | row is a 2nd+ copy of an identical earlier row |
| `dup_group_size` | number of identical rows sharing this row's content (1 = unique) |
