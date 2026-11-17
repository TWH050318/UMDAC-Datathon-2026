# Swift payment dataset — read-only data profiling report

- Input file: `swift_sample.csv`
- Total records inspected: **5,000**
- Total columns: **21**
- Method: chunked, read-only profiling; numeric quantiles approximate (random-key sample).
- NO rows were removed, deduplicated, imputed, or transformed in the source file.

## Dataset schema

Expected Swift columns missing: None
Additional columns: DISCLAIMER (metadata column)

## Blank / whitespace-only values

| Column | Blank count | Share |
|---|---:|---:|
| `DISCLAIMER` | 5,000 | 100.00% |
| `EPOCH_SECONDS` | 0 | 0.00% |
| `CURRENCY_CODE` | 0 | 0.00% |
| `USD_AMOUNT` | 0 | 0.00% |
| `ORDERING_BIC8` | 0 | 0.00% |
| `BENEFICIARY_BIC8` | 0 | 0.00% |
| `BIC8_PATH` | 0 | 0.00% |
| `TOTAL_DURATION` | 0 | 0.00% |
| `CONTINUITY_QFLAG` | 0 | 0.00% |
| `CURRENCY_CONVERSION_COUNT` | 0 | 0.00% |
| `PARTICIPANT_COUNT` | 0 | 0.00% |
| `TRANSACTION_TYPE_CODE` | 0 | 0.00% |
| `ORDERING_ACCOUNT` | 0 | 0.00% |
| `BENEFICIARY_ACCOUNT` | 0 | 0.00% |
| `ORDERING_DETAILS` | 0 | 0.00% |
| `ORDERING_TOKENS` | 0 | 0.00% |
| `BENEFICIARY_DETAILS` | 0 | 0.00% |
| `BENEFICIARY_TOKENS` | 0 | 0.00% |
| `ORDERING_TYPE` | 0 | 0.00% |
| `BENEFICIARY_TYPE` | 0 | 0.00% |
| `ANOMALY_TYPE` | 4,998 | 99.96% |

## Numeric data checks

| Column | Valid | Nonblank invalid | Min | Mean | Max | Approx. median | Approx. p99 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `EPOCH_SECONDS` | 5,000 | 0 | 1,682,880,918.00 | 1,686,885,247.85 | 1,690,762,843.00 | — | — |
| `USD_AMOUNT` | 5,000 | 0 | 0.07 | 72,857.63 | 29,133,006.47 | 3,612.07 | 1,063,146.74 |
| `TOTAL_DURATION` | 5,000 | 0 | 2.00 | 756.59 | 11,070.00 | 53.00 | 5,285.01 |
| `CURRENCY_CONVERSION_COUNT` | 5,000 | 0 | 0.00 | 1.32 | 8.00 | 1.00 | 4.00 |
| `PARTICIPANT_COUNT` | 5,000 | 0 | 2.00 | 2.55 | 10.00 | 2.00 | 6.00 |

UTC timestamp range (numeric min/max): **2023-04-30T18:55:18+00:00** to **2023-07-31T00:20:43+00:00**.

## Categorical frequencies (aggregate only)

### CURRENCY_CODE

| Value | Records |
|---|---:|
| `EUR` | 1,624 |
| `USD` | 804 |
| `GBP` | 439 |
| `CHF` | 407 |
| `CNY` | 173 |
| `SGD` | 155 |
| `JPY` | 98 |
| `AUD` | 90 |
| `HKD` | 88 |
| `SAR` | 60 |
| `KRW` | 55 |
| `CAD` | 55 |
| `AED` | 55 |
| `DKK` | 46 |
| `UAH` | 38 |
| `INR` | 32 |
| `PAB` | 32 |
| `RUB` | 30 |
| `MYR` | 30 |
| `KYD` | 29 |
| `ILS` | 27 |
| `ZAR` | 26 |
| `QAR` | 24 |
| `TRY` | 23 |
| `PLN` | 22 |
| `TWD` | 20 |
| `CLP` | 19 |
| `VND` | 19 |
| `ARS` | 18 |
| `HUF` | 18 |
| `BHD` | 18 |
| `CZK` | 17 |
| `COP` | 16 |
| `NOK` | 16 |
| `SEK` | 16 |
| `MUR` | 14 |
| `XOF` | 14 |
| `BRL` | 13 |
| `BWP` | 13 |
| `KZT` | 13 |
| `LAK` | 13 |
| `ALL` | 12 |
| `KWD` | 11 |
| `NZD` | 11 |
| `BBD` | 11 |
| `BSD` | 9 |
| `LBP` | 9 |
| `KHR` | 8 |
| `BGN` | 8 |
| `MXN` | 8 |
| `GTQ` | 8 |
| `ANG` | 8 |
| `BDT` | 7 |
| `XCD` | 7 |
| `MMK` | 7 |
| `LKR` | 6 |
| `IQD` | 6 |
| `AOA` | 6 |
| `RON` | 6 |
| `PHP` | 6 |
| `PEN` | 6 |
| `BMD` | 5 |
| `XPF` | 5 |
| `IDR` | 5 |
| `EGP` | 5 |
| `UGX` | 4 |
| `TND` | 4 |
| `DOP` | 4 |
| `SDG` | 4 |
| `THB` | 4 |
| `MDL` | 4 |
| `RWF` | 3 |
| `UYU` | 3 |
| `ISK` | 3 |
| `DZD` | 3 |
| `MOP` | 3 |
| `MNT` | 3 |
| `MAD` | 3 |
| `CRC` | 3 |
| `OMR` | 2 |
| `LYD` | 2 |
| `PYG` | 2 |
| `JOD` | 2 |
| `GYD` | 2 |
| `BYN` | 2 |
| `SRD` | 2 |
| `XAF` | 2 |
| `NGN` | 2 |
| `MKD` | 2 |
| `RSD` | 2 |
| `GEL` | 1 |
| `NAD` | 1 |
| `SHP` | 1 |
| `JMD` | 1 |
| `BTN` | 1 |
| `SLL` | 1 |
| `KES` | 1 |
| `MZN` | 1 |
| `ZMW` | 1 |
| `VES` | 1 |
| `HTG` | 1 |
| `ZWL` | 1 |
| `AZN` | 1 |
| `AWG` | 1 |
| `CUP` | 1 |
| `NIO` | 1 |
| `BAM` | 1 |
| `AMD` | 1 |
| `SSP` | 1 |
| `KGS` | 1 |
| `SCR` | 1 |
| `CDF` | 1 |
| `GIP` | 1 |
| `GHS` | 1 |
| `BND` | 1 |
| `SYP` | 1 |
| `CVE` | 1 |
| `PGK` | 1 |
| `TOP` | 1 |
| `DJF` | 1 |
| `GNF` | 1 |

### TRANSACTION_TYPE_CODE

| Value | Records |
|---|---:|
| `Direct` | 3,232 |
| `Indirect` | 1,580 |
| `Covered` | 188 |

### CONTINUITY_QFLAG

| Value | Records |
|---|---:|
| `Y` | 4,645 |
| `N` | 355 |

### ORDERING_TYPE

| Value | Records |
|---|---:|
| `B` | 3,931 |
| `C` | 1,069 |

### BENEFICIARY_TYPE

| Value | Records |
|---|---:|
| `C` | 3,558 |
| `B` | 1,442 |

### ANOMALY_TYPE

| Value | Records |
|---|---:|
| `<BLANK / UNLABELLED>` | 4,998 |
| `ACCOUNT_REPLACEMENT_SCAM` | 1 |
| `ROMANCE_SCAM` | 1 |

## Structural consistency checks (NOT proof of generating causes)

| Candidate relationship | Tested | Matches | Match rate |
|---|---:|---:|---:|
| `BENEFICIARY_BIC8_8_alphanumeric` | 5,000 | 5,000 | 100.00% |
| `ORDERING_BIC8_8_alphanumeric` | 5,000 | 5,000 | 100.00% |
| `continuity_N_iff_path_contains_gap_candidate` | 5,000 | 5,000 | 100.00% |
| `direct_type_iff_two_participants_candidate` | 5,000 | 5,000 | 100.00% |
| `first_observed_bic_matches_ordering_bic` | 5,000 | 4,735 | 94.70% |
| `fx_count_between_zero_and_participants_minus_one_candidate` | 5,000 | 5,000 | 100.00% |
| `last_observed_bic_matches_beneficiary_bic` | 5,000 | 4,776 | 95.52% |
| `participant_count_equals_observed_bics` | 5,000 | 5,000 | 100.00% |

## Review flags (do not automatically delete)

| Flag | Records |
|---|---:|
| `negative_duration_review` | 0 |
| `negative_fx_count_review` | 0 |
| `nonpositive_participant_count_review` | 0 |
| `nonpositive_usd_amount_review` | 0 |
| `paths_with_gap_placeholder` | 355 |
| `paths_with_non_bic_tokens_review` | 0 |
| `paths_without_gap_placeholder` | 4,645 |

## Cleaning decisions and limitations

1. Preserve the original CSV; clean into separate, documented derived datasets only if required.
2. Duplicate payments and unusual amounts may be deliberately generated anomalies. No automatic deduplication or outlier removal.
3. `...` in `BIC8_PATH` is a meaningful route-gap token, not a missing payment record.
4. Blank `ANOMALY_TYPE` means **unlabelled**, not proof of legitimate/normal payment.
5. An enriched anomaly sample must not be used to estimate the full-population anomaly rate.
6. Structural consistency tests are candidate relationships; verify exceptions and alternative explanations on full data.
7. Exact duplicate-record detection is **not** performed in this initial memory-bounded profile. Investigate separately, without dropping records.
8. Approximate quantiles come from a bounded random-key sample and may differ from exact full-data quantiles.
9. This report contains only aggregate statistics; do not commit raw records or sensitive party details.
