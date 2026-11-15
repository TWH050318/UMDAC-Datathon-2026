# Swift payment dataset — read-only data profiling report

- Input file: `swift_umdac_datathon_2026_fictitious_payment_data.csv`
- Total records inspected: **10,000,000**
- Total columns: **21**
- Method: chunked, read-only profiling; numeric quantiles approximate (random-key sample).
- NO rows were removed, deduplicated, imputed, or transformed in the source file.

## Dataset schema

Expected Swift columns missing: None
Additional columns: DISCLAIMER (metadata column)

## Blank / whitespace-only values

| Column | Blank count | Share |
|---|---:|---:|
| `DISCLAIMER` | 9,999,999 | 100.00% |
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
| `ANOMALY_TYPE` | 9,992,994 | 99.93% |

## Numeric data checks

| Column | Valid | Nonblank invalid | Min | Mean | Max | Approx. median | Approx. p99 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `EPOCH_SECONDS` | 10,000,000 | 0 | 1,682,853,746.00 | 1,686,927,373.78 | 1,690,797,361.00 | — | — |
| `USD_AMOUNT` | 10,000,000 | 0 | 0.01 | 97,204.10 | 15,664,132,213.09 | 3,360.40 | 1,226,665.17 |
| `TOTAL_DURATION` | 10,000,000 | 0 | 2.00 | 771.51 | 21,649.00 | 59.00 | 5,396.20 |
| `CURRENCY_CONVERSION_COUNT` | 10,000,000 | 0 | 0.00 | 1.34 | 17.00 | 1.00 | 5.00 |
| `PARTICIPANT_COUNT` | 10,000,000 | 0 | 2.00 | 2.58 | 22.00 | 2.00 | 6.00 |

UTC timestamp range (numeric min/max): **2023-04-30T11:22:26+00:00** to **2023-07-31T09:56:01+00:00**.

## Categorical frequencies (aggregate only)

### CURRENCY_CODE

| Value | Records |
|---|---:|
| `EUR` | 3,198,639 |
| `USD` | 1,702,991 |
| `GBP` | 873,781 |
| `CHF` | 803,898 |
| `SGD` | 367,648 |
| `CNY` | 324,963 |
| `HKD` | 197,458 |
| `JPY` | 184,251 |
| `AUD` | 166,877 |
| `CAD` | 111,146 |
| `KRW` | 108,765 |
| `AED` | 97,143 |
| `SAR` | 97,116 |
| `UAH` | 69,006 |
| `RUB` | 65,105 |
| `DKK` | 63,387 |
| `PAB` | 61,600 |
| `QAR` | 59,848 |
| `TRY` | 55,351 |
| `MYR` | 54,058 |
| `INR` | 51,163 |
| `ILS` | 49,045 |
| `ARS` | 46,494 |
| `ZAR` | 44,481 |
| `KYD` | 41,531 |
| `PLN` | 40,386 |
| `CZK` | 39,013 |
| `TWD` | 38,116 |
| `BHD` | 35,322 |
| `HUF` | 34,676 |
| `SEK` | 32,872 |
| `BSD` | 31,971 |
| `VND` | 29,570 |
| `RON` | 29,348 |
| `NZD` | 28,879 |
| `COP` | 28,670 |
| `CLP` | 27,854 |
| `BWP` | 27,278 |
| `XOF` | 25,887 |
| `BBD` | 24,350 |
| `ALL` | 24,281 |
| `MUR` | 22,811 |
| `KZT` | 22,494 |
| `BDT` | 21,979 |
| `NOK` | 21,256 |
| `XCD` | 20,152 |
| `BRL` | 20,131 |
| `MXN` | 18,883 |
| `KWD` | 18,195 |
| `GTQ` | 15,047 |
| `LKR` | 14,505 |
| `LBP` | 13,795 |
| `MOP` | 13,099 |
| `PYG` | 12,431 |
| `ANG` | 12,089 |
| `IQD` | 11,844 |
| `KHR` | 11,798 |
| `IDR` | 10,510 |
| `THB` | 9,729 |
| `UGX` | 9,666 |
| `BGN` | 9,649 |
| `ISK` | 9,634 |
| `EGP` | 9,282 |
| `BMD` | 8,877 |
| `PHP` | 8,637 |
| `NGN` | 8,566 |
| `DOP` | 8,537 |
| `DZD` | 8,154 |
| `PEN` | 7,934 |
| `LAK` | 7,560 |
| `JOD` | 7,130 |
| `XPF` | 6,968 |
| `AOA` | 6,916 |
| `MMK` | 6,890 |
| `OMR` | 6,799 |
| `UYU` | 6,083 |
| `TND` | 5,904 |
| `PGK` | 5,751 |
| `XAF` | 5,278 |
| `MNT` | 5,167 |
| `GHS` | 5,035 |
| `LYD` | 4,877 |
| `AWG` | 4,752 |
| `BYN` | 4,583 |
| `NAD` | 4,489 |
| `UZS` | 4,481 |
| `AZN` | 4,236 |
| `RWF` | 4,198 |
| `ZWL` | 4,189 |
| `CVE` | 4,118 |
| `YER` | 4,110 |
| `KES` | 4,031 |
| `AMD` | 3,941 |
| `MAD` | 3,866 |
| `BAM` | 3,775 |
| `HNL` | 3,754 |
| `CRC` | 3,695 |
| `GNF` | 3,607 |
| `TJS` | 3,515 |
| `MKD` | 3,506 |
| `FJD` | 3,415 |
| `RSD` | 3,210 |
| `SDG` | 3,158 |
| `BZD` | 3,072 |
| `MVR` | 3,018 |
| `CUP` | 3,014 |
| `PKR` | 2,770 |
| `ETB` | 2,739 |
| `GEL` | 2,645 |
| `VES` | 2,496 |
| `NIO` | 2,446 |
| `TOP` | 2,390 |
| `SSP` | 2,286 |
| `SLL` | 2,007 |
| `MDL` | 1,953 |
| `BND` | 1,874 |
| `TZS` | 1,870 |
| `MRU` | 1,807 |
| `SRD` | 1,803 |
| `CDF` | 1,766 |
| `SYP` | 1,707 |
| `BTN` | 1,587 |
| `IRR` | 1,584 |
| `KGS` | 1,515 |
| `TMT` | 1,392 |
| `BOB` | 1,336 |
| `GYD` | 1,301 |
| `NPR` | 1,083 |
| `DJF` | 1,043 |
| `SBD` | 1,006 |
| `MZN` | 890 |
| `ZMW` | 872 |
| `AFN` | 697 |
| `VUV` | 696 |
| `BIF` | 639 |
| `SHP` | 563 |
| `TTD` | 556 |
| `LRD` | 516 |
| `GMD` | 506 |
| `GIP` | 493 |
| `KMF` | 466 |
| `JMD` | 442 |
| `MWK` | 354 |
| `KPW` | 303 |
| `SZL` | 303 |
| `LSL` | 288 |
| `HTG` | 237 |
| `SOS` | 217 |
| `MGA` | 203 |
| `SCR` | 170 |
| `STN` | 104 |
| `WST` | 62 |
| `ERN` | 15 |
| `FKP` | 5 |
| `SVC` | 4 |

### TRANSACTION_TYPE_CODE

| Value | Records |
|---|---:|
| `Direct` | 6,323,280 |
| `Indirect` | 3,260,758 |
| `Covered` | 415,962 |

### CONTINUITY_QFLAG

| Value | Records |
|---|---:|
| `Y` | 9,232,796 |
| `N` | 767,204 |

### ORDERING_TYPE

| Value | Records |
|---|---:|
| `B` | 7,874,637 |
| `C` | 2,125,363 |

### BENEFICIARY_TYPE

| Value | Records |
|---|---:|
| `C` | 7,118,450 |
| `B` | 2,881,550 |

### ANOMALY_TYPE

| Value | Records |
|---|---:|
| `<BLANK / UNLABELLED>` | 9,992,994 |
| `ROMANCE_SCAM` | 2,476 |
| `FAT_FINGER_MISTAKE` | 1,940 |
| `CEO_SCAM` | 945 |
| `DUPLICATE_PAYMENT` | 679 |
| `ACCOUNT_REPLACEMENT_SCAM` | 649 |
| `CUSTOMER_RECALL` | 317 |

## Structural consistency checks (NOT proof of generating causes)

| Candidate relationship | Tested | Matches | Match rate |
|---|---:|---:|---:|
| `BENEFICIARY_BIC8_8_alphanumeric` | 10,000,000 | 10,000,000 | 100.00% |
| `ORDERING_BIC8_8_alphanumeric` | 10,000,000 | 10,000,000 | 100.00% |
| `continuity_N_iff_path_contains_gap_candidate` | 10,000,000 | 10,000,000 | 100.00% |
| `direct_type_iff_two_participants_candidate` | 10,000,000 | 10,000,000 | 100.00% |
| `first_observed_bic_matches_ordering_bic` | 10,000,000 | 9,501,601 | 95.02% |
| `fx_count_between_zero_and_participants_minus_one_candidate` | 10,000,000 | 10,000,000 | 100.00% |
| `last_observed_bic_matches_beneficiary_bic` | 10,000,000 | 9,500,735 | 95.01% |
| `participant_count_equals_observed_bics` | 10,000,000 | 10,000,000 | 100.00% |

## Review flags (do not automatically delete)

| Flag | Records |
|---|---:|
| `negative_duration_review` | 0 |
| `negative_fx_count_review` | 0 |
| `nonpositive_participant_count_review` | 0 |
| `nonpositive_usd_amount_review` | 0 |
| `paths_with_gap_placeholder` | 767,204 |
| `paths_with_non_bic_tokens_review` | 0 |
| `paths_without_gap_placeholder` | 9,232,796 |

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
