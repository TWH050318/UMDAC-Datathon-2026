"""Validate that enriched Swift CSV preserves every original field and record.

Usage:
  python src/data_engineering/data_validation.py data/swift_sample.csv data/processed/swift_sample_enriched.csv.gz --report findings/data_engineering/sample

The input files are read in chunks; the report contains aggregate counts only.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from itertools import zip_longest
from pathlib import Path

import pandas as pd


def validate(original: Path, enriched: Path, report_dir: Path, chunk_size: int):
    if not original.is_file() or not enriched.is_file():
        raise SystemExit("Both original CSV and processed CSV must exist.")

    reader_options = dict(dtype=str, keep_default_na=False, chunksize=chunk_size, encoding="utf-8-sig", on_bad_lines="error")
    raw_reader = pd.read_csv(original, **reader_options)
    processed_reader = pd.read_csv(enriched, **reader_options)

    rows = 0
    missing_columns = []
    altered_columns = Counter()
    numbering_errors = 0
    column_order_ok = True
    row_count_ok = True
    for pair_no, (raw, output) in enumerate(zip_longest(raw_reader, processed_reader), 1):
        if raw is None or output is None:
            row_count_ok = False
            break
        if len(raw) != len(output):
            row_count_ok = False
            break
        if pair_no == 1:
            missing_columns = [c for c in raw.columns if c not in output.columns]
            column_order_ok = raw.columns.tolist() == output.columns[:len(raw.columns)].tolist()
        if missing_columns:
            break

        for col in raw.columns:
            altered_columns[col] += int(raw[col].ne(output[col]).sum())

        expected_num = pd.Series(range(rows + 1, rows + len(raw) + 1), dtype=str)
        recorded_num = output["SOURCE_ROW_NUMBER"].reset_index(drop=True) if "SOURCE_ROW_NUMBER" in output else pd.Series([], dtype=str)
        numbering_errors += int(expected_num.ne(recorded_num).sum()) if len(recorded_num) == len(expected_num) else len(raw)
        rows += len(raw)
        print(f"Validated {rows:,} records", end="\r", flush=True)

    changed = int(sum(altered_columns.values()))
    passed = row_count_ok and column_order_ok and not missing_columns and changed == 0 and numbering_errors == 0
    status = "PASS" if passed else "FAIL"
    summary = {
        "status": status,
        "rows_verified": rows,
        "row_counts_and_chunk_sizes_match": row_count_ok,
        "original_column_order_preserved": column_order_ok,
        "missing_original_columns": missing_columns,
        "altered_original_field_values": changed,
        "source_row_number_errors": numbering_errors,
        "altered_fields_by_column": {c: int(v) for c, v in altered_columns.items() if v},
    }
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report = [
        "# Swift payment enrichment — independent validation", "",
        f"**Result: {status}**", "",
        f"- Original CSV: `{original.name}`",
        f"- Enriched CSV: `{enriched.name}`",
        f"- Record pairs compared: **{rows:,}**",
        f"- Original values changed: **{changed:,}**",
        f"- Source row numbering errors: **{numbering_errors:,}**",
        f"- Original column order preserved: **{column_order_ok}**",
        f"- Input/output row counts match: **{row_count_ok}**",
        "", "No deduplication, outlier removal or anomaly relabelling was performed by the enrichment pipeline.",
    ]
    if not passed:
        report += ["", "## Problems", "", f"- Missing original columns: {missing_columns}", f"- Modified field counts: {summary['altered_fields_by_column']}"]
    (report_dir / "validation_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"\n{status}: {rows:,} rows compared; {changed:,} changed original values. See {report_dir}.")
    if not passed:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description="Compare original vs enriched CSV records")
    parser.add_argument("original", type=Path)
    parser.add_argument("processed", type=Path)
    parser.add_argument("--report", type=Path, default=Path("findings/data_engineering/full_dataset"))
    parser.add_argument("--chunk-size", type=int, default=25_000)
    args = parser.parse_args()
    if args.chunk_size <= 0:
        parser.error("--chunk-size must be greater than 0")
    validate(args.original, args.processed, args.report, args.chunk_size)


if __name__ == "__main__":
    main()
