# Swift derived-feature verification

**Result: PASS_FULL**

- Enriched source: `swift_enriched.csv.gz`
- Records checked: **10,000,000**
- Scope: **all enriched rows**
- Original columns: **21**
- Derived columns independently recalculated: **17**
- Total derived-field mismatches: **0**

| Derived column | Mismatched rows |
|---|---:|
| `SOURCE_ROW_NUMBER` | 0 |
| `EPOCH_SECONDS_NUM` | 0 |
| `USD_AMOUNT_NUM` | 0 |
| `TOTAL_DURATION_NUM` | 0 |
| `CURRENCY_CONVERSION_COUNT_NUM` | 0 |
| `PARTICIPANT_COUNT_NUM` | 0 |
| `UTC_TIMESTAMP` | 0 |
| `ROUTE_OBSERVED_BIC_COUNT` | 0 |
| `ROUTE_HAS_GAP` | 0 |
| `ROUTE_TOKEN_FORMAT_REVIEW` | 0 |
| `ROUTE_COUNT_MATCH` | 0 |
| `CONTINUITY_FLAG_MATCH` | 0 |
| `ANOMALY_LABELLED` | 0 |
| `AMOUNT_NONPOSITIVE_REVIEW` | 0 |
| `DURATION_NEGATIVE_REVIEW` | 0 |
| `FX_COUNT_INVALID_REVIEW` | 0 |
| `PARTICIPANT_COUNT_INVALID_REVIEW` | 0 |

## Scope and limitations

- Verifies that the 17 appended fields agree with independently recomputed definitions.
- This is not a substitute for the separate original-vs-enriched value and row-count validation.
- Passing checks does not establish hidden economic or causal rules.
- No original payment records, party details or account IDs are included in this report.
