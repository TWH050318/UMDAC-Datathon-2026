"""Step 1: raw CSV (4.95 GB, 10M rows) -> typed Parquet.

Cleaning decisions made here (also logged in docs/data_issues_log.md):
  * DISCLAIMER column is dropped: it holds one legal notice on the first row
    and is NULL everywhere else, so it carries no payment information.
  * ROW_ID is added = position of the record in the original file (0-based),
    so that generation order can be studied and every row stays traceable.
  * No row is removed and no value is changed.
"""
import time

from config import RAW_CSV, RAW_DIR, RAW_PARQUET, connect

COLUMNS = {
    "DISCLAIMER": "VARCHAR",
    "EPOCH_SECONDS": "BIGINT",
    "CURRENCY_CODE": "VARCHAR",
    "USD_AMOUNT": "DOUBLE",
    "ORDERING_BIC8": "VARCHAR",
    "BENEFICIARY_BIC8": "VARCHAR",
    "BIC8_PATH": "VARCHAR",
    "TOTAL_DURATION": "BIGINT",
    "CONTINUITY_QFLAG": "VARCHAR",
    "CURRENCY_CONVERSION_COUNT": "INTEGER",
    "PARTICIPANT_COUNT": "INTEGER",
    "TRANSACTION_TYPE_CODE": "VARCHAR",
    "ORDERING_ACCOUNT": "VARCHAR",
    "BENEFICIARY_ACCOUNT": "VARCHAR",
    "ORDERING_DETAILS": "VARCHAR",
    "ORDERING_TOKENS": "VARCHAR",
    "BENEFICIARY_DETAILS": "VARCHAR",
    "BENEFICIARY_TOKENS": "VARCHAR",
    "ORDERING_TYPE": "VARCHAR",
    "BENEFICIARY_TYPE": "VARCHAR",
    "ANOMALY_TYPE": "VARCHAR",
}


def main():
    t0 = time.time()
    con = connect()
    # Start from an empty folder so no file from an earlier run (or any stray file) is ever read again.
    if RAW_DIR.exists():
        for old in RAW_DIR.glob("*.parquet"):
            old.unlink()
    con.execute("SET preserve_insertion_order=true")
    RAW_DIR.parent.mkdir(parents=True, exist_ok=True)
    cols = ", ".join(f"'{k}': '{v}'" for k, v in COLUMNS.items())
    keep = ", ".join(c for c in COLUMNS if c != "DISCLAIMER")
    con.execute(
        f"""
        COPY (
            SELECT row_number() OVER () - 1 AS ROW_ID, {keep}
            FROM read_csv('{RAW_CSV.as_posix()}', header=true, columns={{{cols}}},
                          quote='"', escape='"', parallel=false)
        ) TO '{RAW_DIR.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 50000,
             FILE_SIZE_BYTES '18MB', OVERWRITE)
        """
    )
    n = con.execute(f"SELECT count(*) FROM '{RAW_PARQUET}'").fetchone()[0]
    print(f"rows written: {n:,}  ({time.time() - t0:.0f}s)  -> {RAW_DIR}")


if __name__ == "__main__":
    main()
