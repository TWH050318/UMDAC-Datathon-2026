"""Verify all 17 Swift enrichment fields against the original fields in an enriched CSV.

Run from the repository root:
    python src/data_engineering/feature_verification.py \
        data/processed/swift_enriched.csv.gz \
        --report findings/data_engineering/full_dataset

Use --max-rows 5000 for a quick pilot, then remove it to verify all rows.
Reads the enriched file in chunks and writes aggregate reports only. It neither
modifies nor exports any individual transaction. Requires pandas and numpy.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

NUMERIC_SOURCES = [
    "EPOCH_SECONDS", "USD_AMOUNT", "TOTAL_DURATION",
    "CURRENCY_CONVERSION_COUNT", "PARTICIPANT_COUNT",
]
INTEGERS = {"CURRENCY_CONVERSION_COUNT", "PARTICIPANT_COUNT"}
DERIVED_COLUMNS = [
    "SOURCE_ROW_NUMBER", "EPOCH_SECONDS_NUM", "USD_AMOUNT_NUM",
    "TOTAL_DURATION_NUM", "CURRENCY_CONVERSION_COUNT_NUM", "PARTICIPANT_COUNT_NUM",
    "UTC_TIMESTAMP", "ROUTE_OBSERVED_BIC_COUNT", "ROUTE_HAS_GAP",
    "ROUTE_TOKEN_FORMAT_REVIEW", "ROUTE_COUNT_MATCH", "CONTINUITY_FLAG_MATCH",
    "ANOMALY_LABELLED", "AMOUNT_NONPOSITIVE_REVIEW",
    "DURATION_NEGATIVE_REVIEW", "FX_COUNT_INVALID_REVIEW",
    "PARTICIPANT_COUNT_INVALID_REVIEW",
]
REQUIRED_ORIGINAL = [
    "EPOCH_SECONDS", "USD_AMOUNT", "BIC8_PATH", "PARTICIPANT_COUNT",
    "CONTINUITY_QFLAG", "CURRENCY_CONVERSION_COUNT", "TOTAL_DURATION",
    "ANOMALY_TYPE",
]


def expected_numeric(raw: pd.Series, integral: bool) -> pd.Series:
    """Independently parse finite numeric input; only integers for count fields."""
    values = pd.to_numeric(raw.str.strip(), errors="coerce")
    finite = pd.Series(np.isfinite(values.to_numpy(dtype=float)), index=raw.index)
    if integral:
        finite &= values.mod(1).eq(0).fillna(False)
    return values.where(finite)


def path_checks(path: str) -> tuple[int, bool, bool]:
    """Count observed (non-gap, nonempty) BIC tokens and flag malformed tokens."""
    if not path.strip():
        return (0, False, True)
    tokens = [t.strip() for t in path.split(";")]
    observed = sum(bool(t and t != "...") for t in tokens)
    gap = "..." in tokens
    bad = any(
        (not t) or (t != "..." and not (len(t) == 8 and t.isascii() and t.isalnum()))
        for t in tokens
    )
    return (observed, gap, bad)


def check_number(actual: pd.Series, expected: pd.Series) -> pd.Series:
    stored = actual.str.strip()
    observed = pd.to_numeric(stored, errors="coerce").to_numpy(dtype=float)
    wanted = expected.to_numpy(dtype=float)
    matches = np.isclose(observed, wanted, rtol=1e-12, atol=1e-9, equal_nan=True)
    # Require a blank string for an invalid/missing derived numeric, not junk text.
    matches &= (~np.isnan(wanted)) | stored.eq("").to_numpy()
    return pd.Series(matches, index=actual.index)


def check_boolean(actual: pd.Series, expected: pd.Series) -> pd.Series:
    """Compare stored booleans, allowing missing only where the source is ineligible."""
    representation = expected.map({True: "true", False: "false"}).fillna("")
    return actual.str.strip().str.lower().eq(representation)


def verify(file: Path, report_dir: Path, chunk_size: int, max_rows: int | None) -> None:
    if not file.is_file():
        raise SystemExit(f"Enriched CSV not found: {file}")
    if chunk_size < 1 or (max_rows is not None and max_rows < 1):
        raise SystemExit("--chunk-size and --max-rows must be positive")
    report_dir.mkdir(parents=True, exist_ok=True)
    reader = pd.read_csv(
        file, dtype=str, keep_default_na=False, chunksize=chunk_size,
        encoding="utf-8-sig", on_bad_lines="error",
    )
    problems: Counter[str] = Counter()
    checked_rows = 0
    sample_row_numbers: dict[str, list[int]] = {}
    original_count: int | None = None
    seen_derived: list[str] = []

    for chunk_no, chunk in enumerate(reader, 1):
        if original_count is None:
            absent = sorted(set(DERIVED_COLUMNS + REQUIRED_ORIGINAL) - set(chunk.columns))
            if absent:
                raise SystemExit(f"Required fields absent from enriched CSV: {absent}")
            seen_derived = [c for c in chunk.columns if c in DERIVED_COLUMNS]
            original_count = len(chunk.columns) - len(DERIVED_COLUMNS)
            if len(chunk.columns) != original_count + 17:
                raise SystemExit("Unexpected derived-column count")
            # The previous pipeline preserves all raw fields at the front.
            if chunk.columns[-17:].tolist() != DERIVED_COLUMNS:
                raise SystemExit("Derived column order differs from data_cleaning.py")

        if max_rows is not None:
            remaining = max_rows - checked_rows
            if remaining <= 0:
                break
            chunk = chunk.iloc[:remaining].copy()

        n = len(chunk)
        if n == 0:
            break
        checks: dict[str, pd.Series] = {}
        expected_row = pd.Series(np.arange(checked_rows + 1, checked_rows + n + 1), index=chunk.index)
        checks["SOURCE_ROW_NUMBER"] = check_number(chunk["SOURCE_ROW_NUMBER"], expected_row)

        typed: dict[str, pd.Series] = {}
        for source in NUMERIC_SOURCES:
            expected = expected_numeric(chunk[source], source in INTEGERS)
            typed[source] = expected
            checks[f"{source}_NUM"] = check_number(chunk[f"{source}_NUM"], expected)

        wanted_utc = pd.to_datetime(typed["EPOCH_SECONDS"], unit="s", utc=True, errors="coerce")
        stored_utc = pd.to_datetime(chunk["UTC_TIMESTAMP"], utc=True, errors="coerce")
        checks["UTC_TIMESTAMP"] = wanted_utc.eq(stored_utc) | (wanted_utc.isna() & stored_utc.isna())

        features = chunk["BIC8_PATH"].map(path_checks)
        counts = pd.Series(features.map(lambda x: x[0]), index=chunk.index)
        gaps = pd.Series(features.map(lambda x: x[1]), index=chunk.index)
        invalid_tokens = pd.Series(features.map(lambda x: x[2]), index=chunk.index)
        checks["ROUTE_OBSERVED_BIC_COUNT"] = check_number(chunk["ROUTE_OBSERVED_BIC_COUNT"], counts)
        checks["ROUTE_HAS_GAP"] = check_boolean(chunk["ROUTE_HAS_GAP"], gaps)
        checks["ROUTE_TOKEN_FORMAT_REVIEW"] = check_boolean(chunk["ROUTE_TOKEN_FORMAT_REVIEW"], invalid_tokens)

        # Nullable route-count comparison; ineligible when path blank or count invalid.
        participant = typed["PARTICIPANT_COUNT"].astype("Int64")
        count_match = participant.eq(counts).astype("boolean")
        count_match = count_match.mask(chunk["BIC8_PATH"].str.strip().eq(""))
        checks["ROUTE_COUNT_MATCH"] = check_boolean(chunk["ROUTE_COUNT_MATCH"], count_match)

        qflag = chunk["CONTINUITY_QFLAG"].str.strip().str.upper()
        eligible = qflag.isin(["Y", "N"]) & chunk["BIC8_PATH"].str.strip().ne("")
        continuity = pd.Series(pd.NA, index=chunk.index, dtype="boolean")
        continuity.loc[eligible] = qflag.loc[eligible].eq("N").eq(gaps.loc[eligible])
        checks["CONTINUITY_FLAG_MATCH"] = check_boolean(chunk["CONTINUITY_FLAG_MATCH"], continuity)

        labelled = chunk["ANOMALY_TYPE"].str.strip().ne("")
        checks["ANOMALY_LABELLED"] = check_boolean(chunk["ANOMALY_LABELLED"], labelled)
        checks["AMOUNT_NONPOSITIVE_REVIEW"] = check_boolean(
            chunk["AMOUNT_NONPOSITIVE_REVIEW"], typed["USD_AMOUNT"].le(0).fillna(False)
        )
        checks["DURATION_NEGATIVE_REVIEW"] = check_boolean(
            chunk["DURATION_NEGATIVE_REVIEW"], typed["TOTAL_DURATION"].lt(0).fillna(False)
        )
        checks["FX_COUNT_INVALID_REVIEW"] = check_boolean(
            chunk["FX_COUNT_INVALID_REVIEW"], typed["CURRENCY_CONVERSION_COUNT"].lt(0).fillna(False)
        )
        checks["PARTICIPANT_COUNT_INVALID_REVIEW"] = check_boolean(
            chunk["PARTICIPANT_COUNT_INVALID_REVIEW"], typed["PARTICIPANT_COUNT"].le(0).fillna(False)
        )

        for name, is_ok in checks.items():
            failed_positions = np.flatnonzero(~is_ok.fillna(False).to_numpy(dtype=bool))
            problems[name] += len(failed_positions)
            if len(failed_positions) and len(sample_row_numbers.get(name, [])) < 5:
                current = sample_row_numbers.setdefault(name, [])
                for pos in failed_positions[:5 - len(current)]:
                    current.append(checked_rows + int(pos) + 1)

        checked_rows += n
        print(f"Verified derived fields for {checked_rows:,} rows", end="\r", flush=True)

    if checked_rows == 0:
        raise SystemExit("No rows found")
    failures = sum(problems.values())
    limited = max_rows is not None
    passed = failures == 0
    status = ("PASS_PARTIAL" if limited else "PASS_FULL") if passed else "FAIL"
    summary = {
        "status": status,
        "source_file": file.name,
        "records_checked": checked_rows,
        "verification_scope": "first N rows only" if limited else "all rows in enriched CSV",
        "original_column_count": original_count,
        "derived_columns_checked": DERIVED_COLUMNS,
        "mismatches_by_derived_column": {c: int(problems.get(c, 0)) for c in DERIVED_COLUMNS},
        "mismatches_total": int(failures),
        "example_source_row_numbers_only": sample_row_numbers,
        "note": "Checks computed features only; prior raw-to-enriched data_validation.py checks original values and row counts.",
    }
    (report_dir / "feature_verification_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    lines = [
        "# Swift derived-feature verification", "",
        f"**Result: {status}**", "",
        f"- Enriched source: `{file.name}`",
        f"- Records checked: **{checked_rows:,}**",
        f"- Scope: **{'first N rows only' if limited else 'all enriched rows'}**",
        f"- Original columns: **{original_count}**",
        "- Derived columns independently recalculated: **17**",
        f"- Total derived-field mismatches: **{failures:,}**", "",
        "| Derived column | Mismatched rows |", "|---|---:|",
    ]
    lines.extend(f"| `{column}` | {int(problems.get(column, 0)):,} |" for column in DERIVED_COLUMNS)
    lines += [
        "", "## Scope and limitations", "",
        "- Verifies that the 17 appended fields agree with independently recomputed definitions.",
        "- This is not a substitute for the separate original-vs-enriched value and row-count validation.",
        "- Passing checks does not establish hidden economic or causal rules.",
        "- No original payment records, party details or account IDs are included in this report.",
    ]
    if failures:
        lines += ["", "## Example failing source row numbers (without payment details)", ""]
        lines.extend(f"- `{k}`: {v}" for k, v in sample_row_numbers.items())
    (report_dir / "feature_verification_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n{status}: {checked_rows:,} records, {failures:,} derived-field mismatches. See {report_dir}")
    if not passed:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Independently verify all 17 Swift derived fields")
    parser.add_argument("enriched_csv", type=Path)
    parser.add_argument("--report", type=Path, default=Path("findings/data_engineering/full_dataset"))
    parser.add_argument("--chunk-size", type=int, default=25_000)
    parser.add_argument("--max-rows", type=int, default=None, help="Pilot only; does not verify the full dataset")
    args = parser.parse_args()
    verify(args.enriched_csv, args.report, args.chunk_size, args.max_rows)


if __name__ == "__main__":
    main()
