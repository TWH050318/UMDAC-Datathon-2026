"""Read-only, chunked Swift payment data profiler for UMDAC Datathon 2026.

Run from repository root:
    python src/data_engineering/data_profiling.py data/swift_sample.csv --out findings/data_engineering/sample
    python src/data_engineering/data_profiling.py data/YOUR_FULL_DATASET.csv --out findings/data_engineering/full_dataset

Generates aggregate summaries ONLY, no raw payment/account/party data.
Keeps the original CSV untouched and NEVER deduplicates or removes outliers.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

NUMERIC_COLUMNS = [
    "EPOCH_SECONDS", "USD_AMOUNT", "TOTAL_DURATION",
    "CURRENCY_CONVERSION_COUNT", "PARTICIPANT_COUNT",
]
CATEGORICAL_COLUMNS = [
    "CURRENCY_CODE", "TRANSACTION_TYPE_CODE", "CONTINUITY_QFLAG",
    "ORDERING_TYPE", "BENEFICIARY_TYPE", "ANOMALY_TYPE",
]
EXPECTED_COLUMNS = [
    "EPOCH_SECONDS", "CURRENCY_CODE", "USD_AMOUNT", "ORDERING_BIC8",
    "BENEFICIARY_BIC8", "BIC8_PATH", "TOTAL_DURATION", "CONTINUITY_QFLAG",
    "CURRENCY_CONVERSION_COUNT", "PARTICIPANT_COUNT", "TRANSACTION_TYPE_CODE",
    "ORDERING_ACCOUNT", "BENEFICIARY_ACCOUNT", "ORDERING_DETAILS",
    "ORDERING_TOKENS", "BENEFICIARY_DETAILS", "BENEFICIARY_TOKENS",
    "ORDERING_TYPE", "BENEFICIARY_TYPE", "ANOMALY_TYPE",
]


def utc_label(epoch: float | None) -> str:
    if epoch is None or not np.isfinite(epoch):
        return "not available"
    try:
        return pd.to_datetime(epoch, unit="s", utc=True).isoformat()
    except (ValueError, OverflowError, TypeError):
        return "out of supported datetime range"


def add_test(checks: dict, label: str, eligible: pd.Series, condition: pd.Series) -> None:
    count = int(eligible.sum())
    checks[label]["tested"] += count
    checks[label]["matched"] += int((eligible & condition.fillna(False)).sum())


def profile(input_file: Path, output_dir: Path, chunk_size: int, quantile_sample_size: int) -> None:
    if not input_file.is_file():
        raise SystemExit(f"Cannot find input CSV: {input_file}")
    output_dir.mkdir(parents=True, exist_ok=True)

    row_count = 0
    columns: list[str] | None = None
    blank_counts: Counter = Counter()
    invalid_numeric: Counter = Counter()
    cat_counts: dict[str, Counter] = {c: Counter() for c in CATEGORICAL_COLUMNS}
    numeric_stats = {c: {"count": 0, "sum": 0., "min": None, "max": None} for c in NUMERIC_COLUMNS}
    checks = defaultdict(lambda: {"tested": 0, "matched": 0})
    observations = Counter()
    reservoir = pd.DataFrame()
    rng = np.random.default_rng(2026)

    # All fields are loaded as text to avoid silently converting account IDs,
    # currency codes, party text, or literal "NA" into missing values.
    reader = pd.read_csv(
        input_file, chunksize=chunk_size, dtype=str, keep_default_na=False,
        encoding="utf-8-sig", on_bad_lines="error",
    )
    for chunk_num, chunk in enumerate(reader, start=1):
        if columns is None:
            columns = chunk.columns.tolist()
        n = len(chunk)
        row_count += n

        for col in columns:
            blank_counts[col] += int(chunk[col].str.strip().eq("").sum())

        for col in CATEGORICAL_COLUMNS:
            if col in chunk:
                # Empty anomaly labels are NOT automatically "normal" payments.
                counts = chunk[col].str.strip().replace("", "<BLANK / UNLABELLED>").value_counts()
                cat_counts[col].update(counts.to_dict())

        number: dict[str, pd.Series] = {}
        for col in NUMERIC_COLUMNS:
            if col not in chunk:
                continue
            raw = chunk[col].str.strip()
            numeric = pd.to_numeric(raw, errors="coerce")
            finite = np.isfinite(numeric)
            valid = numeric.where(finite)
            number[col] = valid
            invalid_numeric[col] += int((raw.ne("") & ~finite).sum())
            values = valid.dropna()
            if len(values):
                stats = numeric_stats[col]
                stats["count"] += len(values)
                stats["sum"] += float(values.sum())
                this_min, this_max = float(values.min()), float(values.max())
                stats["min"] = this_min if stats["min"] is None else min(stats["min"], this_min)
                stats["max"] = this_max if stats["max"] is None else max(stats["max"], this_max)

        if "USD_AMOUNT" in number:
            observations["nonpositive_usd_amount_review"] += int(number["USD_AMOUNT"].le(0).sum())
        if "TOTAL_DURATION" in number:
            observations["negative_duration_review"] += int(number["TOTAL_DURATION"].lt(0).sum())
        if "PARTICIPANT_COUNT" in number:
            observations["nonpositive_participant_count_review"] += int(number["PARTICIPANT_COUNT"].le(0).sum())
        if "CURRENCY_CONVERSION_COUNT" in number:
            observations["negative_fx_count_review"] += int(number["CURRENCY_CONVERSION_COUNT"].lt(0).sum())

        for bic_col in ("ORDERING_BIC8", "BENEFICIARY_BIC8"):
            if bic_col in chunk:
                nonblank = chunk[bic_col].str.strip().ne("")
                pattern_ok = chunk[bic_col].str.strip().str.fullmatch(r"[A-Za-z0-9]{8}")
                add_test(checks, f"{bic_col}_8_alphanumeric", nonblank, pattern_ok)

        if "BIC8_PATH" in chunk:
            path_raw = chunk["BIC8_PATH"].str.strip()
            path_valid = path_raw.ne("")
            # The literal ... token is a route gap, not a missing row.
            parsed = path_raw.map(lambda p: [part.strip() for part in p.split(";")])
            actual_bics = parsed.map(lambda p: [item for item in p if item and item != "..."])
            actual_count = actual_bics.map(len)
            has_gap = parsed.map(lambda p: "..." in p)
            first_bic = actual_bics.map(lambda p: p[0] if p else "")
            last_bic = actual_bics.map(lambda p: p[-1] if p else "")
            observations["paths_with_gap_placeholder"] += int((path_valid & has_gap).sum())
            observations["paths_without_gap_placeholder"] += int((path_valid & ~has_gap).sum())
            observations["paths_with_non_bic_tokens_review"] += int(parsed.map(
                lambda p: any(item not in ("", "...") and not (
                    len(item) == 8 and item.isascii() and item.isalnum()
                ) for item in p)).sum())

            if "PARTICIPANT_COUNT" in number:
                p = number["PARTICIPANT_COUNT"]
                add_test(checks, "participant_count_equals_observed_bics", path_valid & p.notna(), p.eq(actual_count))
                if "TRANSACTION_TYPE_CODE" in chunk:
                    typ = chunk["TRANSACTION_TYPE_CODE"].str.strip()
                    add_test(checks, "direct_type_iff_two_participants_candidate", path_valid & p.notna() & typ.ne(""), typ.eq("Direct").eq(p.eq(2)))
                if "CURRENCY_CONVERSION_COUNT" in number:
                    fx = number["CURRENCY_CONVERSION_COUNT"]
                    add_test(checks, "fx_count_between_zero_and_participants_minus_one_candidate", path_valid & p.notna() & fx.notna(), fx.ge(0) & fx.le(p - 1))

            if "CONTINUITY_QFLAG" in chunk:
                flag = chunk["CONTINUITY_QFLAG"].str.strip().str.upper()
                add_test(checks, "continuity_N_iff_path_contains_gap_candidate", path_valid & flag.isin(["Y", "N"]), flag.eq("N").eq(has_gap))
            if "ORDERING_BIC8" in chunk:
                sending = chunk["ORDERING_BIC8"].str.strip()
                add_test(checks, "first_observed_bic_matches_ordering_bic", path_valid & sending.ne("") & first_bic.ne(""), first_bic.eq(sending))
            if "BENEFICIARY_BIC8" in chunk:
                receiving = chunk["BENEFICIARY_BIC8"].str.strip()
                add_test(checks, "last_observed_bic_matches_beneficiary_bic", path_valid & receiving.ne("") & last_bic.ne(""), last_bic.eq(receiving))

        # Small random-key reservoir approximates quantiles WITHOUT collecting
        # all transaction values or writing raw rows to disk.
        quant_cols = [c for c in ("USD_AMOUNT", "TOTAL_DURATION", "PARTICIPANT_COUNT", "CURRENCY_CONVERSION_COUNT") if c in number]
        if quant_cols and quantile_sample_size > 0:
            keys = rng.random(n)
            selected = np.argpartition(keys, min(quantile_sample_size, n) - 1)[:min(quantile_sample_size, n)]
            new_sample = pd.DataFrame({"_key": keys[selected]})
            for col in quant_cols:
                new_sample[col] = number[col].iloc[selected].to_numpy()
            reservoir = pd.concat([reservoir, new_sample], ignore_index=True).nsmallest(quantile_sample_size, "_key")

        print(f"Read {row_count:,} records in {chunk_num:,} chunks", end="\r", flush=True)

    if columns is None:
        raise SystemExit("CSV contains no rows.")
    missing_expected = [col for col in EXPECTED_COLUMNS if col not in columns]
    extra_columns = [col for col in columns if col not in EXPECTED_COLUMNS]
    if extra_columns == ["DISCLAIMER"]:
        extra_columns = ["DISCLAIMER (metadata column)"]

    quantiles = {}
    for col in reservoir:
        if col == "_key":
            continue
        values = reservoir[col].dropna()
        if not values.empty:
            q = values.quantile([.5, .9, .99]).to_dict()
            quantiles[col] = {"approx_median": float(q[.5]), "approx_p90": float(q[.9]), "approx_p99": float(q[.99])}

    report = [
        "# Swift payment dataset — read-only data profiling report", "",
        f"- Input file: `{input_file.name}`",
        f"- Total records inspected: **{row_count:,}**",
        f"- Total columns: **{len(columns)}**",
        "- Method: chunked, read-only profiling; numeric quantiles approximate (random-key sample).",
        "- NO rows were removed, deduplicated, imputed, or transformed in the source file.", "",
        "## Dataset schema", "",
        f"Expected Swift columns missing: {', '.join(missing_expected) if missing_expected else 'None'}",
        f"Additional columns: {', '.join(extra_columns) if extra_columns else 'None'}", "",
        "## Blank / whitespace-only values", "",
        "| Column | Blank count | Share |", "|---|---:|---:|",
    ]
    for col in columns:
        count = blank_counts[col]
        report.append(f"| `{col}` | {count:,} | {100*count/row_count:.2f}% |")

    report += ["", "## Numeric data checks", "", "| Column | Valid | Nonblank invalid | Min | Mean | Max | Approx. median | Approx. p99 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for col in NUMERIC_COLUMNS:
        if col not in columns:
            continue
        s = numeric_stats[col]
        avg = s["sum"] / s["count"] if s["count"] else None
        f = lambda v: f"{v:,.2f}" if v is not None else "—"
        q = quantiles.get(col, {})
        report.append(f"| `{col}` | {s['count']:,} | {invalid_numeric[col]:,} | {f(s['min'])} | {f(avg)} | {f(s['max'])} | {f(q.get('approx_median'))} | {f(q.get('approx_p99'))} |")

    if "EPOCH_SECONDS" in columns:
        t = numeric_stats["EPOCH_SECONDS"]
        report += ["", f"UTC timestamp range (numeric min/max): **{utc_label(t['min'])}** to **{utc_label(t['max'])}**."]

    report += ["", "## Categorical frequencies (aggregate only)"]
    for col in CATEGORICAL_COLUMNS:
        if col not in columns:
            continue
        report += ["", f"### {col}", "", "| Value | Records |", "|---|---:|"]
        # Complete aggregate frequencies, without exposing individual account identifiers.
        for value, cnt in cat_counts[col].most_common():
            report.append(f"| `{str(value).replace('|', '/')}` | {cnt:,} |")

    report += ["", "## Structural consistency checks (NOT proof of generating causes)", "", "| Candidate relationship | Tested | Matches | Match rate |", "|---|---:|---:|---:|"]
    for label, counts in sorted(checks.items()):
        tested = counts["tested"]
        matches = counts["matched"]
        rate = f"{100*matches/tested:.2f}%" if tested else "—"
        report.append(f"| `{label}` | {tested:,} | {matches:,} | {rate} |")

    report += ["", "## Review flags (do not automatically delete)", "", "| Flag | Records |", "|---|---:|"]
    for name, count in sorted(observations.items()):
        report.append(f"| `{name}` | {count:,} |")
    report += [
        "", "## Cleaning decisions and limitations", "",
        "1. Preserve the original CSV; clean into separate, documented derived datasets only if required.",
        "2. Duplicate payments and unusual amounts may be deliberately generated anomalies. No automatic deduplication or outlier removal.",
        "3. `...` in `BIC8_PATH` is a meaningful route-gap token, not a missing payment record.",
        "4. Blank `ANOMALY_TYPE` means **unlabelled**, not proof of legitimate/normal payment.",
        "5. An enriched anomaly sample must not be used to estimate the full-population anomaly rate.",
        "6. Structural consistency tests are candidate relationships; verify exceptions and alternative explanations on full data.",
        "7. Exact duplicate-record detection is **not** performed in this initial memory-bounded profile. Investigate separately, without dropping records.",
        "8. Approximate quantiles come from a bounded random-key sample and may differ from exact full-data quantiles.",
        "9. This report contains only aggregate statistics; do not commit raw records or sensitive party details.", "",
    ]

    summary = {
        "input_file": input_file.name, "rows": row_count, "columns": columns,
        "missing_expected_columns": missing_expected, "extra_columns": extra_columns,
        "blank_values": dict(blank_counts),
        "invalid_numeric_nonblank": dict(invalid_numeric),
        "numeric_stats": numeric_stats, "approx_quantiles": quantiles,
        "category_counts": {k: dict(v) for k, v in cat_counts.items() if k in columns},
        "structural_checks": {k: dict(v) for k, v in checks.items()},
        "review_flags": dict(observations),
    }
    (output_dir / "profile_report.md").write_text("\n".join(report), encoding="utf-8")
    (output_dir / "profile_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nFinished. Profiled {row_count:,} records. Reports saved to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Read-only Swift data profiler")
    parser.add_argument("csv", type=Path, help="Input Swift CSV (no changes are made)")
    parser.add_argument("--out", type=Path, default=Path("findings/data_engineering/sample"), help="Report output folder")
    parser.add_argument("--chunk-size", type=int, default=25_000, help="Rows per chunk (default 25000)")
    parser.add_argument("--quantile-sample-size", type=int, default=10_000, help="Bounded numeric sample size")
    args = parser.parse_args()
    if args.chunk_size < 1 or args.quantile_sample_size < 0:
        parser.error("chunk-size must be positive and quantile-sample-size nonnegative")
    profile(args.csv, args.out, args.chunk_size, args.quantile_sample_size)


if __name__ == "__main__":
    main()
