"""Helpers shared by all notebooks: one DuckDB connection, two views, small I/O helpers.

    from utils import q, rule_check, savefig, export
    q("SELECT FLOW, count(*) FROM f GROUP BY 1")

Views:  f = analysis table (data/processed/payments_features/)
        p = raw table incl. *_DETAILS / *_TOKENS text (data/interim/payments_raw/)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib.pyplot as plt
import pandas as pd
from config import CHARTS, CSV_OUT, FEATURES_PARQUET, RAW_PARQUET, connect

con = connect()
con.execute(f"CREATE OR REPLACE VIEW f AS SELECT * FROM '{FEATURES_PARQUET}'")
con.execute(f"CREATE OR REPLACE VIEW p AS SELECT * FROM '{RAW_PARQUET}'")
pd.set_option("display.width", 200, "display.max_columns", 40, "display.max_rows", 200)
plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left"})


def q(sql: str) -> pd.DataFrame:
    """Run SQL on the full dataset and return a DataFrame."""
    return con.execute(sql).df()


def rule_check(name: str, rule_sql: str, where: str = "TRUE", table: str = "f") -> pd.DataFrame:
    """Validate a candidate rule on the FULL dataset.

    rule_sql is a boolean SQL expression. Returns how many rows are in scope
    (`where`), how many satisfy the rule, and the match rate. A deterministic
    rule should give 100%; anything lower means exceptions to investigate.
    """
    df = q(f"""SELECT count(*) AS rows_in_scope,
                      sum(CASE WHEN ({rule_sql}) THEN 1 ELSE 0 END) AS rows_matching
               FROM {table} WHERE {where}""")
    df.insert(0, "rule", name)
    df["match_rate_pct"] = (100 * df.rows_matching / df.rows_in_scope).round(4)
    df["exceptions"] = df.rows_in_scope - df.rows_matching
    return df


def savefig(name: str):
    """Save the current figure to outputs/charts/<name>.png for the dashboard."""
    CHARTS.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(CHARTS / f"{name}.png", dpi=160, bbox_inches="tight")


def export(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Save an aggregate table to outputs/csv/<name>.csv (Power BI input)."""
    CSV_OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(CSV_OUT / f"{name}.csv", index=False)
    return df
