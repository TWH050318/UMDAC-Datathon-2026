"""Shared paths and settings for the whole team. Import this everywhere."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "swift_umdac_datathon_2026_fictitious_payment_data.csv"
# Parquet is written as a folder of part files (each < 400 MB) so it also fits on FAT32 drives.
RAW_DIR = ROOT / "data" / "interim" / "payments_raw"
FEATURES_DIR = ROOT / "data" / "processed" / "payments_features"
RAW_PARQUET = (RAW_DIR / "*.parquet").as_posix()            # glob used in SQL
FEATURES_PARQUET = (FEATURES_DIR / "*.parquet").as_posix()  # glob used in SQL
CHARTS = ROOT / "outputs" / "charts"
CSV_OUT = ROOT / "outputs" / "csv"
DOCS = ROOT / "docs"

# DuckDB settings: lower MEMORY_LIMIT if your laptop has 8 GB RAM or less.
MEMORY_LIMIT = "4GB"
THREADS = 2


def connect():
    """Return a DuckDB connection with the team-wide settings applied."""
    import duckdb

    con = duckdb.connect()
    con.execute(f"SET memory_limit='{MEMORY_LIMIT}'")
    con.execute(f"SET threads={THREADS}")
    (ROOT / "data" / "tmp").mkdir(parents=True, exist_ok=True)
    con.execute(f"SET temp_directory='{(ROOT / 'data' / 'tmp').as_posix()}'")
    return con
