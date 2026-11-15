"""UMDAC Datathon 2026 — Member 2, Step 1.

Validate candidate structural rules and generate first dashboard charts.
Process an entire Swift CSV in chunks; do not upload raw records.

Run from repository root:
    python src/member2/step1_routing.py data/swift_sample.csv
    python src/member2/step1_routing.py data/your_full_dataset.csv
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

COLUMNS = [
    "BIC8_PATH", "PARTICIPANT_COUNT", "CONTINUITY_QFLAG",
    "TRANSACTION_TYPE_CODE", "CURRENCY_CONVERSION_COUNT", "TOTAL_DURATION",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Swift Member 2 routing exploration")
    parser.add_argument("csv", type=Path, help="Path to original Swift CSV or sample")
    parser.add_argument("--chunk-size", type=int, default=100_000)
    parser.add_argument("--out", type=Path, default=Path("findings/member2/step1"))
    args = parser.parse_args()

    if not args.csv.is_file():
        raise SystemExit(f"File not found: {args.csv}")
    args.out.mkdir(parents=True, exist_ok=True)

    total = 0
    rule_checks = defaultdict(lambda: [0, 0])  # [matches, evaluable records]
    route_types = Counter()
    participant_counts = Counter()
    fx_by_participants = Counter()
    duration_count = Counter()
    duration_sum = Counter()
    route_type_by_participants = Counter()

    def add_rule(name: str, good: pd.Series, valid: pd.Series) -> None:
        rule_checks[name][0] += int((good & valid).sum())
        rule_checks[name][1] += int(valid.sum())

    for chunk in pd.read_csv(
        args.csv, usecols=COLUMNS, chunksize=args.chunk_size, low_memory=False
    ):
        total += len(chunk)
        paths = chunk["BIC8_PATH"].fillna("").astype(str).str.split(";")
        actual_participants = paths.map(
            lambda parts: sum(bool(p.strip()) and p.strip() != "..." for p in parts)
        )
        has_gap = paths.map(lambda parts: any(p.strip() == "..." for p in parts))

        participants = pd.to_numeric(chunk["PARTICIPANT_COUNT"], errors="coerce")
        fx_steps = pd.to_numeric(chunk["CURRENCY_CONVERSION_COUNT"], errors="coerce")
        duration = pd.to_numeric(chunk["TOTAL_DURATION"], errors="coerce")
        continuity = chunk["CONTINUITY_QFLAG"].fillna("").astype(str).str.strip().str.upper()
        txn_type = chunk["TRANSACTION_TYPE_CODE"].fillna("MISSING").astype(str).str.strip()
        valid_paths = chunk["BIC8_PATH"].notna() & (chunk["BIC8_PATH"].astype(str).str.strip() != "")
        valid_parts = participants.notna() & valid_paths
        valid_flags = valid_paths & continuity.isin(["Y", "N"])

        add_rule("participant_count_matches_path", participants.eq(actual_participants), valid_parts)
        add_rule("continuity_N_iff_path_has_gap", continuity.eq("N").eq(has_gap), valid_flags)
        add_rule("direct_iff_two_participants", txn_type.eq("Direct").eq(participants.eq(2)), valid_parts & txn_type.ne("MISSING"))
        add_rule("fx_between_zero_and_participants_minus_one", fx_steps.ge(0) & fx_steps.le(participants - 1), valid_parts & fx_steps.notna())
        add_rule("duration_nonnegative", duration.ge(0), duration.notna())

        route_types.update(txn_type.value_counts().to_dict())
        participant_counts.update(participants.dropna().astype(int).value_counts().to_dict())

        valid = participants.notna() & fx_steps.notna()
        table = pd.DataFrame({"participants": participants[valid].astype(int), "fx": fx_steps[valid].astype(int)})
        fx_by_participants.update(table.groupby(["participants", "fx"]).size().to_dict())

        dur_table = pd.DataFrame({"participants": participants, "duration": duration}).dropna()
        grouped = dur_table.groupby("participants")["duration"].agg(["size", "sum"])
        duration_count.update(grouped["size"].to_dict())
        duration_sum.update(grouped["sum"].to_dict())

        crosstab = pd.DataFrame({"participants": participants, "type": txn_type}).dropna()
        route_type_by_participants.update(crosstab.groupby(["participants", "type"]).size().to_dict())
        print(f"Processed {total:,} records", end="\r", flush=True)

    summary = [f"INPUT: {args.csv.name}", f"TOTAL ROWS: {total:,}", "", "STRUCTURAL RULE CHECKS:"]
    for name, (matches, tested) in rule_checks.items():
        ratio = 100 * matches / tested if tested else float("nan")
        summary.append(f"{name}: {matches:,}/{tested:,} ({ratio:.3f}%)")
    summary.append("\nROUTING TYPE COUNTS:")
    for name, n in route_types.most_common():
        summary.append(f"{name}: {n:,}")
    summary.append("\nMEAN DURATION BY PARTICIPANT COUNT (seconds; may be affected by outliers):")
    for k in sorted(duration_count):
        n = duration_count[k]
        summary.append(f"participants={int(k)}: n={n:,}, mean_duration={duration_sum[k]/n:.2f}")
    summary.extend([
        "", "INTERPRETATION NOTE:",
        "Perfect matches are consistent with candidate generator rules, but do not prove causality.",
        "A direct two-participant rule may reflect the documented category definition.",
        "These charts are exploratory; validate full data, exceptions and alternative explanations.",
    ])
    report = "\n".join(summary) + "\n"
    (args.out / "member2_step1_report.txt").write_text(report, encoding="utf-8")
    print("\n" + report)

    if route_types:
        names, values = zip(*route_types.most_common())
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.bar(names, values)
        ax.set(title="Payment routing categories", ylabel="Number of payments")
        ax.tick_params(axis="x", labelrotation=15)
        fig.tight_layout()
        fig.savefig(args.out / "routing_type_counts.png", dpi=180)
        plt.close(fig)

    if duration_count:
        xs = sorted(duration_count)
        ys = [duration_sum[x] / duration_count[x] for x in xs]
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.plot(xs, ys, marker="o")
        ax.set(title="Mean payment duration by route participant count", xlabel="Participant count", ylabel="Mean duration (seconds)")
        ax.set_xticks(xs)
        fig.tight_layout()
        fig.savefig(args.out / "duration_by_participants.png", dpi=180)
        plt.close(fig)

    if fx_by_participants:
        table = pd.Series(fx_by_participants, dtype=int).unstack(fill_value=0).sort_index()
        table.index.name = "participant_count"
        table.columns.name = "fx_steps"
        proportions = table.div(table.sum(axis=1), axis=0)
        fig, ax = plt.subplots(figsize=(9, 5))
        im = ax.imshow(proportions.to_numpy(), aspect="auto", origin="upper", vmin=0, vmax=1)
        ax.set_xticks(range(len(table.columns)), labels=[str(x) for x in table.columns])
        ax.set_yticks(range(len(table.index)), labels=[str(int(x)) for x in table.index])
        ax.set(title="FX conversion distribution within each route size", xlabel="Currency conversions", ylabel="Participants")
        fig.colorbar(im, ax=ax, label="Proportion within participant count")
        fig.tight_layout()
        fig.savefig(args.out / "fx_by_participants.png", dpi=180)
        plt.close(fig)

    pd.DataFrame([
        {"participants": int(k[0]), "fx_steps": int(k[1]), "count": int(v)}
        for k, v in sorted(fx_by_participants.items())
    ]).to_csv(args.out / "fx_aggregate_counts.csv", index=False)
    print(f"Saved report, charts, and aggregated table to {args.out}")


if __name__ == "__main__":
    main()
