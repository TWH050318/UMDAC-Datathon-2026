"""UMDAC Datathon 2026 | Swift payment processing (lossless, chunked).

Usage (from repository root):
  python src/data_engineering/data_cleaning.py data/swift_sample.csv \
      --out data/processed/swift_sample_enriched.csv.gz \
      --report findings/data_engineering/sample

  python src/data_engineering/data_cleaning.py data/swift_full.csv \
      --out data/processed/swift_enriched.csv.gz \
      --report findings/data_engineering/full_dataset

Policy: original CSV is never edited, rows are never dropped or deduplicated,
and every original column is preserved *verbatim as text* in the output.
Derived numeric columns have a _NUM suffix. The compressed CSV contains
original payment records including synthetic account/party details: keep it
inside data/ and never commit it to GitHub. Only aggregate reports may be shared after review.
"""
from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED = [
    "EPOCH_SECONDS", "CURRENCY_CODE", "USD_AMOUNT", "ORDERING_BIC8",
    "BENEFICIARY_BIC8", "BIC8_PATH", "TOTAL_DURATION", "CONTINUITY_QFLAG",
    "CURRENCY_CONVERSION_COUNT", "PARTICIPANT_COUNT", "TRANSACTION_TYPE_CODE",
    "ORDERING_ACCOUNT", "BENEFICIARY_ACCOUNT", "ORDERING_DETAILS",
    "ORDERING_TOKENS", "BENEFICIARY_DETAILS", "BENEFICIARY_TOKENS",
    "ORDERING_TYPE", "BENEFICIARY_TYPE",
]
NUMBER_FIELDS = [
    "EPOCH_SECONDS", "USD_AMOUNT", "TOTAL_DURATION",
    "CURRENCY_CONVERSION_COUNT", "PARTICIPANT_COUNT",
]
INTEGER_FIELDS = {"CURRENCY_CONVERSION_COUNT", "PARTICIPANT_COUNT"}


def convert_numeric(raw: pd.Series, integer: bool):
    """Return typed values plus an invalid-value flag; never alter raw text."""
    stripped = raw.str.strip()
    value = pd.to_numeric(stripped, errors="coerce")
    valid = np.isfinite(value)
    if integer:
        valid = valid & value.mod(1).eq(0)
        result = value.where(valid).astype("Int64")
    else:
        result = value.where(valid).astype("float64")
    invalid = stripped.ne("") & ~valid
    return result, invalid


def get_path_features(path: str):
    if not path.strip():
        return 0, False, True
    tokens = [x.strip() for x in path.split(";")]
    banks = [x for x in tokens if x and x != "..."]
    bad_tokens = any(
        not x or (x != "..." and not (len(x) == 8 and x.isascii() and x.isalnum()))
        for x in tokens
    )
    return len(banks), "..." in tokens, bad_tokens


def process(source: Path, target: Path, report_dir: Path, chunk_size: int):
    if not source.is_file():
        raise SystemExit(f"Input CSV not found: {source}")
    source = source.resolve()
    target = target.resolve()
    if source == target:
        raise SystemExit("Input and output cannot be the same file.")
    if target.exists():
        raise SystemExit(f"Refusing to overwrite existing processed CSV: {target}. Choose a new --out path or rename the old output.")
    target.parent.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    temp_target = target.with_name(target.name + ".partial")
    if temp_target.exists():
        raise SystemExit(f"Partial output exists: {temp_target}. Inspect/remove it before rerunning.")

    count = 0
    input_columns = None
    flags = Counter()
    category_counts = {x: Counter() for x in ["TRANSACTION_TYPE_CODE", "CONTINUITY_QFLAG", "ANOMALY_TYPE"]}
    output_written = 0

    try:
        with gzip.open(temp_target, "wt", encoding="utf-8", newline="") as dest:
            reader = pd.read_csv(
                source, dtype=str, chunksize=chunk_size, keep_default_na=False,
                encoding="utf-8-sig", on_bad_lines="error",
            )
            for number, chunk in enumerate(reader, 1):
                if input_columns is None:
                    input_columns = chunk.columns.tolist()
                    missing = sorted(set(REQUIRED) - set(input_columns))
                    if missing:
                        raise ValueError(f"Missing required columns: {missing}")
                    derived_names = ["SOURCE_ROW_NUMBER", "UTC_TIMESTAMP", "ROUTE_OBSERVED_BIC_COUNT", "ROUTE_HAS_GAP", "ROUTE_TOKEN_FORMAT_REVIEW", "ROUTE_COUNT_MATCH", "CONTINUITY_FLAG_MATCH", "ANOMALY_LABELLED"]
                    derived_names += [x + "_NUM" for x in NUMBER_FIELDS]
                    derived_names += ["AMOUNT_NONPOSITIVE_REVIEW", "DURATION_NEGATIVE_REVIEW", "FX_COUNT_INVALID_REVIEW", "PARTICIPANT_COUNT_INVALID_REVIEW"]
                    collisions = sorted(set(input_columns) & set(derived_names))
                    if collisions:
                        raise ValueError(f"Input has columns reserved for derived fields: {collisions}")
                n = len(chunk)
                start = count
                count += n

                # Preserve all original input columns as original strings.
                out = chunk.copy()
                out["SOURCE_ROW_NUMBER"] = pd.Series(np.arange(start + 1, count + 1, dtype=np.int64), index=chunk.index)

                numeric = {}
                for col in NUMBER_FIELDS:
                    numeric[col], invalid = convert_numeric(chunk[col], col in INTEGER_FIELDS)
                    out[col + "_NUM"] = numeric[col]
                    flags["invalid_numeric_" + col] += int(invalid.sum())

                out["UTC_TIMESTAMP"] = pd.to_datetime(numeric["EPOCH_SECONDS"], unit="s", utc=True, errors="coerce")
                flags["invalid_timestamp"] += int(out["UTC_TIMESTAMP"].isna().sum())

                route = chunk["BIC8_PATH"].map(get_path_features)
                observed = pd.Series(route.map(lambda t: t[0]), index=chunk.index, dtype="int64")
                has_gap = pd.Series(route.map(lambda t: t[1]), index=chunk.index, dtype="bool")
                token_review = pd.Series(route.map(lambda t: t[2]), index=chunk.index, dtype="bool")
                out["ROUTE_OBSERVED_BIC_COUNT"] = observed
                out["ROUTE_HAS_GAP"] = has_gap
                out["ROUTE_TOKEN_FORMAT_REVIEW"] = token_review
                flags["route_gap_placeholder"] += int(has_gap.sum())
                flags["route_token_format_review"] += int(token_review.sum())

                route_count_match = numeric["PARTICIPANT_COUNT"].eq(observed).astype("boolean")
                route_count_match = route_count_match.mask(chunk["BIC8_PATH"].str.strip().eq(""))
                out["ROUTE_COUNT_MATCH"] = route_count_match
                flags["route_count_mismatch"] += int(route_count_match.eq(False).sum())

                flag = chunk["CONTINUITY_QFLAG"].str.strip().str.upper()
                continuity_match = pd.Series(pd.NA, index=chunk.index, dtype="boolean")
                eligible = flag.isin(["Y", "N"]) & chunk["BIC8_PATH"].str.strip().ne("")
                continuity_match.loc[eligible] = flag.loc[eligible].eq("N").eq(has_gap.loc[eligible])
                out["CONTINUITY_FLAG_MATCH"] = continuity_match
                flags["continuity_mismatch"] += int(continuity_match.eq(False).sum())

                if "ANOMALY_TYPE" in chunk:
                    labelled = chunk["ANOMALY_TYPE"].str.strip().ne("")
                else:
                    labelled = pd.Series(False, index=chunk.index)
                out["ANOMALY_LABELLED"] = labelled.astype(bool)
                flags["labelled_anomaly_records"] += int(labelled.sum())

                out["AMOUNT_NONPOSITIVE_REVIEW"] = numeric["USD_AMOUNT"].le(0).fillna(False).astype(bool)
                out["DURATION_NEGATIVE_REVIEW"] = numeric["TOTAL_DURATION"].lt(0).fillna(False).astype(bool)
                out["FX_COUNT_INVALID_REVIEW"] = numeric["CURRENCY_CONVERSION_COUNT"].lt(0).fillna(False).astype(bool)
                out["PARTICIPANT_COUNT_INVALID_REVIEW"] = numeric["PARTICIPANT_COUNT"].le(0).fillna(False).astype(bool)
                for key, column in [
                    ("nonpositive_usd_amount_review", "AMOUNT_NONPOSITIVE_REVIEW"),
                    ("negative_duration_review", "DURATION_NEGATIVE_REVIEW"),
                    ("negative_fx_count_review", "FX_COUNT_INVALID_REVIEW"),
                    ("nonpositive_participant_count_review", "PARTICIPANT_COUNT_INVALID_REVIEW"),
                ]:
                    flags[key] += int(out[column].sum())

                for col, counter in category_counts.items():
                    if col in chunk:
                        counter.update(chunk[col].str.strip().replace("", "<UNLABELLED / BLANK>").value_counts().to_dict())

                out.to_csv(dest, index=False, header=(number == 1), lineterminator="\n")
                output_written += n
                print(f"Converted {count:,} rows ({number:,} chunks)", end="\r", flush=True)
        if input_columns is None:
            raise ValueError("No transaction rows found in CSV.")
        if count != output_written:
            raise RuntimeError(f"Row-count mismatch during writing: {count} vs {output_written}")
        temp_target.replace(target)
    finally:
        if temp_target.exists():
            temp_target.unlink()

    # This verifies writer counts only. Use data_validation.py to compare
    # every raw record against the processed CSV on the full dataset.
    stored_rows = output_written

    summary = {
        "input_filename": source.name,
        "output_filename": target.name,
        "input_rows": count,
        "output_rows": stored_rows,
        "original_columns_preserved": input_columns,
        "derived_columns_added": [col for col in out.columns if col not in input_columns],
        "review_flags": dict(sorted(flags.items())),
        "category_counts": {c: dict(v) for c, v in category_counts.items() if c in input_columns},
        "method": "Read-only source; zero row deletion, zero deduplication, zero outlier trimming, no imputation; append numeric-as-text and diagnostic fields to compressed CSV",
    }
    report = [
        "# Swift payments — lossless cleaning and feature preparation", "",
        f"- Input: `{source.name}` (unchanged)",
        f"- Output: `{target.name}` (local compressed CSV containing raw payment fields)",
        f"- Input rows: **{count:,}**", f"- Rows written: **{stored_rows:,}** (not yet independently read back)",
        f"- Original columns preserved: **{len(input_columns)}**",
        f"- Derived columns added: **{len(summary['derived_columns_added'])}**", "",
        "## Decisions made", "",
        "1. Preserved every original CSV record and original field as text; never modified the source.",
        "2. Added numeric and UTC timestamp fields; invalid values become blank **only in derived fields**. CSV readers should parse numeric fields explicitly.",
        "3. Preserved duplicate records, extreme values, blank anomaly labels, and `...` route gaps.",
        "4. Added diagnostics for routing structure, continuity and suspicious numeric values. No automatic correction.",
        "5. No imputation, account changes, or token rewriting. Empty anomaly label means unlabelled, not proven normal.",
        "6. Processed CSV contains synthetic account identifiers and party details: keep it out of GitHub.",
        "7. Duplicate and anomalous payment frequency require separate analysis; this step does not infer labels.", "",
        "## Data quality flags (review, not deletion)", "",
        "| Check | Records |", "|---|---:|",
    ]
    report.extend(f"| `{key}` | {value:,} |" for key, value in sorted(flags.items()))
    report.extend([
        "", "## Validation", "",
        "| Test | Result |", "|---|---|",
        f"| Input/writer row counts match (independent validation pending) | {'PASS' if count == stored_rows else 'FAIL'} |",
        "| Original columns retained in output schema | PASS |",
        "| Original CSV modified by script | NO |",
        "| Duplicate/outlier deletion performed | NO |",
        "", "## Next action", "",
        "Investigate review flags and compare against the read-only profiling report. Only add corrections if evidence supports them.",
    ])
    (report_dir / "cleaning_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    (report_dir / "cleaning_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nCompleted: {count:,} records; {target}; report: {report_dir}")


def main():
    parser = argparse.ArgumentParser(description="Lossless, chunked Swift dataset enrichment")
    parser.add_argument("csv", type=Path, help="Original Swift CSV file")
    parser.add_argument("--out", type=Path, default=Path("data/processed/swift_enriched.csv.gz"))
    parser.add_argument("--report", type=Path, default=Path("findings/data_engineering/full_dataset"))
    parser.add_argument("--chunk-size", type=int, default=25_000)
    args = parser.parse_args()
    if args.chunk_size < 1:
        parser.error("--chunk-size must be positive")
    process(args.csv, args.out, args.report, args.chunk_size)


if __name__ == "__main__":
    main()
