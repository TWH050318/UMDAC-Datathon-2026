# UMDAC Datathon 2026 - Swift Payments Reverse-Engineering (Member 1)

**Deadline:** Thursday 19 Nov 2026, 12:00 PM Malaysia time.
**Task type:** forensic reverse-engineering of how Swift's *fictitious* 10M-row payment dataset was generated. Not a prediction task: no black-box ML; every finding must state a rule (Condition, Effect, Scope) backed by a statistical test.
**Judging weights known from the brief:** Insight Quality 45%, Evidence / Method / Data Integrity 23%. (The remaining criteria are not stated in the files we have.)

## What is in this folder
| Path | Content |
| :-- | :-- |
| `src/01_data_prep_and_audit.py` | Gate 1: ingest, audit, build shared parquet |
| `src/02_currency_analysis.py` | Gate 2: currency patterns |
| `src/03_amount_analysis.py` | Gate 3: amount patterns |
| `src/04_temporal_analysis.py` | Gate 4: temporal patterns |
| `data/processed/clean_payments.parquet` | Shared clean dataset (10,000,000 rows, 0 dropped) |
| `outputs/reports/data_issues_log.md` | Every data-quality decision and row count |
| `outputs/reports/extracted_rules.md` | 19 rules in the Hypothesis / Rule / Negative check / Interpretation template |
| `outputs/csv/` | Summary tables for Power BI (`d1_*`, `d2_*`, `d3_*`) |
| `outputs/charts/` | Six 300-DPI charts with quantified titles |
| `outputs/d*_run.log` | Full console output behind every number |

Run order: `python src/01_...py` then `02`, `03`, `04` (Gate 1 takes ~15 min; others a few minutes).

## Data integrity (Gate 1)
- 10,000,000 rows, 20 data columns plus an undocumented `DISCLAIMER` column (filled on row 1 only; excluded).
- Zero rows dropped, zero numeric cast failures, parquet hash-checked against the raw CSV; BIC8 and account IDs kept as text (leading zeros preserved).
- Anomalies are flagged, never removed: 7,006 rows (0.07%): ROMANCE_SCAM 2,476, FAT_FINGER_MISTAKE 1,940, CEO_SCAM 945, DUPLICATE_PAYMENT 679, ACCOUNT_REPLACEMENT_SCAM 649, **CUSTOMER_RECALL 317 (not in the brief's schema notes)**.
- Only 1 byte-identical duplicate row; labelled duplicates are near-duplicates (see rule D2-R7).
- Period: 30 Apr 2023 11:22 UTC to 31 Jul 2023 09:56 UTC.

## Key findings (full numbers in `extracted_rules.md`)
**Currency**
- EUR 32.0% and USD 17.0% of payments; top 5 = 69.5% of 155 currencies.
- Currency = ordering bank's home currency in 89.5% of rows; the beneficiary side does not determine it (32%).
- Median amount differs strongly by currency (KW epsilon^2 0.077; e.g. UAH $222 vs USD $6,371).

**Amounts**
- log10(amount) is normal within each party pair with the same spread (sd ~0.99); medians B2B $22,883, B2C $3,118, C2B $3,236, C2C $464.
- Each Business party multiplies the amount ~7x (sender x7.04, receiver x7.27), almost purely additive on the log scale.
- USD amounts are whole-dollar 38.6% of the time vs ~1% for other currencies; non-USD amounts are round numbers in local currency converted at a **UTC-day-specific rate** (13% match at the reconstructed daily rate vs 0.01% with another day's rate).
- No $10,000 threshold effect. No hard cap.
- ROMANCE_SCAM = small consumer payments (~$105-121 median); CEO_SCAM B2C = 8.2x normal; FAT_FINGER = median 86x the sender's own typical amount (no single 10x/100x factor); DUPLICATE_PAYMENT = clusters of 2-5 payments, same account pair and amount, within two hours (100% of labelled rows).

**Time**
- Timing follows the **sender's local clock**: weekend share 9.9-10.5% in every country in local time vs 10.0-14.2% in UTC; offsets recovered by two independent methods (35/35 agree).
- One local-hour profile for all countries (peak 18:00, floor ~1% overnight); weekends carry 0.28x a weekday per day.
- Corporate and consumer senders have the **same** schedule (hypothesis rejected).
- Weekly volume moves between 6 discrete levels (x1.0 to x2.4) with unchanged composition.
- No batch/minute/second spikes. Time does not change amounts, routing type or anomaly labels.

## Known limitations (state these honestly in the report)
- Per-country UTC offsets are inferred (about +/-1 h from the weekend fit alone, confirmed by the hour-profile fit); AU (+11) has a flat curve.
- The daily FX-rate anchor assumes the most repeated amount is a round 1,000 local units; the day-specific fit is the evidence, not the unit.
- Fat-finger baseline is the sender's median normal amount, which is noisy.
- Unresolved: why SGD and CHF medians are ~1.0x USD but GBP is 0.56x; the weekly volume multiplier schedule; DUPLICATE_PAYMENT clusters' other differing fields.
- Not yet covered by Member 1's gates: the BIC path / routing / duration / account-text columns (`BIC8_PATH`, `TOTAL_DURATION`, `TRANSACTION_TYPE_CODE` internals, `*_DETAILS`, `*_TOKENS`).

## Hand-off notes
- Member 3 (Power BI + PowerPoint): use `outputs/csv/` and `outputs/charts/`; chart titles already state the quantified takeaway and show n.
- Members 2/3: always filter on `ANOMALY_TYPE = 'NORMAL'` for distribution analysis and use `utc_*` columns plus `ordering_country` offsets (see `d3_temporal_summary.csv`, block `country_offset`) for local-time analysis. `utc_hour`/`utc_dow` are TINYINT: cast to int before arithmetic.

## Running from this repository
This folder is self-contained. The raw CSV (4.9 GB) and the generated parquet (1.3 GB) exceed GitHub's file limit and are **not** committed (`member1/data/` is git-ignored). To reproduce, place the raw CSV at `member1/data/swift_umdac_datathon_2026_fictitious_payment_data.csv`, then run `python member1/src/01_data_prep_and_audit.py` followed by `02`, `03`, `04`. Requires: duckdb, pandas, numpy, scipy, matplotlib.
