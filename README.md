<div align="center">

# Decoding Swift's Synthetic Payments

### UMDAC Datathon 2026 · UMEMPLOYED SQUAD

**Reverse-engineering patterns behind 10 million synthetic payment records**

![Dataset](https://img.shields.io/badge/Dataset-10M%20payments-123B5D?style=for-the-badge)
![Verified features](https://img.shields.io/badge/Features%20verified-17%2F17-0D9488?style=for-the-badge)
![Focus](https://img.shields.io/badge/Focus-8%20feature%20groups-6676C7?style=for-the-badge)

**[Project overview](#overview) · [Key findings](#key-findings) · [Explore the work](#explore-the-work) · [Methodology](#methodology)**

</div>

---

## Overview

**What rules could explain the structure of Swift's synthetic payment data?**

We analysed **10,000,000 synthetic payments** to investigate patterns in routing, currency conversion, processing duration, amounts, payment timing, customer identifiers, and labelled anomalies. Our approach combines independent data-integrity checks, explicit hypotheses, alternative explanations, and held-out validation where available.

> [!IMPORTANT]
> These are **findings about a synthetic dataset**, not the recovered source code of Swift's simulator or evidence of real-world banking performance.

## Key findings

| Feature | Result | Evidence boundary |
| :--- | :--- | :--- |
| **Routing** | **~36.8%** route-length continuation ratio | Approximate synthetic-generator model |
| **FX conversion** | **99.94%** agreement on held-out 3–6-bank paths | Inferred currency areas; not actual FX costs |
| **Processing duration** | **0.982** held-out bank-pair R² | 76.7% coverage of eligible direct pairs |
| **Payment amounts** | **~7.2×** scale for each business party | Approximate group-level relationship |
| **Currency selection** | **86.7%** cross-border sender-home use | Home currency inferred from domestic records |
| **Customer identifiers** | **~4.7×** lift for ID differences of 10–99 | Numeric proximity, not geographic distance |
| **Anomaly sequences** | **185** labelled duplicate-payment clusters | Synthetic labels; no live fraud-detection rate |

<details>
<summary><strong>Additional evidence and scope</strong></summary>

- **FX:** 99.52% agreement on held-out country pairs unseen during training.
- **Temporal activity:** sender-local timing aligns daily patterns across 35 ordering countries; this was not separately time-held-out.
- **Data integrity:** 17 of 17 derived features were independently checked, with zero reported mismatches in the full-data verification.
- **Anomaly labels:** 7,006 payments carry labels; the remaining 9,992,994 are *unlabelled*, not verified normal.

</details>

## Explore the work

The workstreams were developed across the team's repository branches.

| Workstream | What to find |
| :--- | :--- |
| **[Data Engineering](https://github.com/TWH050318/UMDAC-Datathon-2026/tree/data-engineering)** | Data validation, feature enrichment, and verification reports |
| **[Reverse Engineering](https://github.com/TWH050318/UMDAC-Datathon-2026/tree/kenny-analysis)** | Rule hypotheses, notebooks, aggregate evidence, and held-out tests |
| **[Payment Economics](https://github.com/TWH050318/UMDAC-Datathon-2026/tree/member1-data-prep-and-analysis)** | Amount, currency, and local-time analysis |
| **[Automated Dashboard](https://github.com/TWH050318/UMDAC-Datathon-2026/tree/feature/automated-dashboard)** | Reproducible visualisations for the eight feature groups |

> Branch links reflect the project snapshots used for this README. If a branch has since been merged or renamed, update its link to the corresponding location on the default branch.

## Methodology

1. **Verify the dataset** — confirm row preservation and derived-feature integrity.
2. **Describe the patterns** — profile routing, FX, duration, amounts, time, IDs, and anomaly labels.
3. **Form falsifiable hypotheses** — propose generating rules and competing explanations.
4. **Challenge the hypotheses** — compare against simpler models, negative controls, and shuffled baselines.
5. **Validate when possible** — test FX and direct bank-pair duration on later payments.
6. **Report limitations** — distinguish exact identities, supported models, and unresolved mechanisms.

## Tech stack

`Python` · `Pandas` · `NumPy` · `SciPy` · `DuckDB` · `PyArrow` · `Matplotlib` · `Jupyter`

## Data use and reproducibility

The competition dataset is synthetic and subject to its data-use rules. **Do not publish transaction-level records, account identifiers, or raw/processed Parquet files.** The repository is intended to showcase code, documentation, and aggregate evidence. Any proposed operational use requires validation using authorised real-world data.

---

<div align="center">

**UMDAC Datathon 2026 · Swift Synthetic Payments · UMEMPLOYED SQUAD**

</div>
