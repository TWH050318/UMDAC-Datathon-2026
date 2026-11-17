# Swift payments — lossless cleaning and feature preparation

- Input: `swift_sample.csv` (unchanged)
- Output: `swift_sample_enriched.csv.gz` (local compressed CSV containing raw payment fields)
- Input rows: **5,000**
- Rows written: **5,000** (not yet independently read back)
- Original columns preserved: **21**
- Derived columns added: **17**

## Decisions made

1. Preserved every original CSV record and original field as text; never modified the source.
2. Added numeric and UTC timestamp fields; invalid values become blank **only in derived fields**. CSV readers should parse numeric fields explicitly.
3. Preserved duplicate records, extreme values, blank anomaly labels, and `...` route gaps.
4. Added diagnostics for routing structure, continuity and suspicious numeric values. No automatic correction.
5. No imputation, account changes, or token rewriting. Empty anomaly label means unlabelled, not proven normal.
6. Processed CSV contains synthetic account identifiers and party details: keep it out of GitHub.
7. Duplicate and anomalous payment frequency require separate analysis; this step does not infer labels.

## Data quality flags (review, not deletion)

| Check | Records |
|---|---:|
| `continuity_mismatch` | 0 |
| `invalid_numeric_CURRENCY_CONVERSION_COUNT` | 0 |
| `invalid_numeric_EPOCH_SECONDS` | 0 |
| `invalid_numeric_PARTICIPANT_COUNT` | 0 |
| `invalid_numeric_TOTAL_DURATION` | 0 |
| `invalid_numeric_USD_AMOUNT` | 0 |
| `invalid_timestamp` | 0 |
| `labelled_anomaly_records` | 2 |
| `negative_duration_review` | 0 |
| `negative_fx_count_review` | 0 |
| `nonpositive_participant_count_review` | 0 |
| `nonpositive_usd_amount_review` | 0 |
| `route_count_mismatch` | 0 |
| `route_gap_placeholder` | 355 |
| `route_token_format_review` | 0 |

## Validation

| Test | Result |
|---|---|
| Input/writer row counts match (independent validation pending) | PASS |
| Original columns retained in output schema | PASS |
| Original CSV modified by script | NO |
| Duplicate/outlier deletion performed | NO |

## Next action

Investigate review flags and compare against the read-only profiling report. Only add corrections if evidence supports them.
