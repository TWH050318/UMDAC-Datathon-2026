"""Step 2: typed Parquet -> analysis table with shared derived fields.

Every derived field is a deterministic function of the raw columns, so no
information is invented. The four long text columns (*_DETAILS, *_TOKENS)
stay in data/interim/payments_raw/; join on ROW_ID when you need them.

Derived fields (shared definitions for the whole team):
  TS_UTC, DATE_UTC, HOUR_UTC, DOW (1=Mon..7=Sun), IS_WEEKEND   from EPOCH_SECONDS
  ORD_COUNTRY / BEN_COUNTRY   characters 5-6 of the BIC8 (ISO country code)
  ORD_LOC / BEN_LOC           characters 7-8 of the BIC8 (location code)
  IS_DOMESTIC                 ordering and beneficiary bank in the same country
  FLOW                        B2B / B2C / C2B / C2C
  N_PATH_BICS                 BICs listed in BIC8_PATH, '...' not counted
  HAS_GAP                     BIC8_PATH contains '...'
  N_INTERMEDIARIES            PARTICIPANT_COUNT - 2
  PATH_FIRST_IS_ORD / PATH_LAST_IS_BEN   path endpoints equal the two BIC8 columns
  N_PATH_COUNTRIES            distinct countries among the visible path BICs
  LOG10_USD                   log10(USD_AMOUNT)
  ANOMALY, IS_ANOMALY         ANOMALY_TYPE with NULL -> 'NONE'
  *_ACC_IS_IBAN, *_ACC_COUNTRY  account looks like an IBAN (CC + 2 digits), its country
  *_DETAILS_COUNTRY           last <country_code:XX> token of the party details
"""
import time

from config import FEATURES_DIR, FEATURES_PARQUET, RAW_PARQUET, connect

SQL = f"""
COPY (
    WITH base AS (
        SELECT *,
               to_timestamp(EPOCH_SECONDS) AT TIME ZONE 'UTC' AS TS_UTC,
               list_filter(string_split(BIC8_PATH, ';'), lambda x: x <> '...') AS path_bics
        FROM '{RAW_PARQUET}'
    )
    SELECT
        ROW_ID, EPOCH_SECONDS, CURRENCY_CODE, USD_AMOUNT, ORDERING_BIC8, BENEFICIARY_BIC8,
        BIC8_PATH, TOTAL_DURATION, CONTINUITY_QFLAG, CURRENCY_CONVERSION_COUNT,
        PARTICIPANT_COUNT, TRANSACTION_TYPE_CODE, ORDERING_ACCOUNT, BENEFICIARY_ACCOUNT,
        ORDERING_TYPE, BENEFICIARY_TYPE, ANOMALY_TYPE,
        TS_UTC,
        CAST(TS_UTC AS DATE)                      AS DATE_UTC,
        hour(TS_UTC)                              AS HOUR_UTC,
        isodow(TS_UTC)                            AS DOW,
        isodow(TS_UTC) >= 6                       AS IS_WEEKEND,
        substr(ORDERING_BIC8, 5, 2)               AS ORD_COUNTRY,
        substr(BENEFICIARY_BIC8, 5, 2)            AS BEN_COUNTRY,
        substr(ORDERING_BIC8, 7, 2)               AS ORD_LOC,
        substr(BENEFICIARY_BIC8, 7, 2)            AS BEN_LOC,
        substr(ORDERING_BIC8, 5, 2) = substr(BENEFICIARY_BIC8, 5, 2) AS IS_DOMESTIC,
        ORDERING_TYPE || '2' || BENEFICIARY_TYPE  AS FLOW,
        len(path_bics)                            AS N_PATH_BICS,
        contains(BIC8_PATH, '...')                AS HAS_GAP,
        PARTICIPANT_COUNT - 2                     AS N_INTERMEDIARIES,
        path_bics[1]  = ORDERING_BIC8             AS PATH_FIRST_IS_ORD,
        path_bics[-1] = BENEFICIARY_BIC8          AS PATH_LAST_IS_BEN,
        len(list_distinct(list_transform(path_bics, lambda x: substr(x, 5, 2)))) AS N_PATH_COUNTRIES,
        log10(USD_AMOUNT)                         AS LOG10_USD,
        coalesce(ANOMALY_TYPE, 'NONE')            AS ANOMALY,
        ANOMALY_TYPE IS NOT NULL                  AS IS_ANOMALY,
        regexp_matches(ORDERING_ACCOUNT,    '^_FAKE_[A-Z]{{2}}[0-9]{{2}}') AS ORD_ACC_IS_IBAN,
        regexp_matches(BENEFICIARY_ACCOUNT, '^_FAKE_[A-Z]{{2}}[0-9]{{2}}') AS BEN_ACC_IS_IBAN,
        CASE WHEN regexp_matches(ORDERING_ACCOUNT, '^_FAKE_[A-Z]{{2}}[0-9]{{2}}')
             THEN substr(ORDERING_ACCOUNT, 7, 2) END    AS ORD_ACC_COUNTRY,
        CASE WHEN regexp_matches(BENEFICIARY_ACCOUNT, '^_FAKE_[A-Z]{{2}}[0-9]{{2}}')
             THEN substr(BENEFICIARY_ACCOUNT, 7, 2) END AS BEN_ACC_COUNTRY,
        nullif(regexp_extract_all(ORDERING_TOKENS,    '<country_code:([A-Z]{{2}})>', 1)[-1], '') AS ORD_DETAILS_COUNTRY,
        nullif(regexp_extract_all(BENEFICIARY_TOKENS, '<country_code:([A-Z]{{2}})>', 1)[-1], '') AS BEN_DETAILS_COUNTRY
    FROM base
) TO '{FEATURES_DIR.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 500000,
     FILE_SIZE_BYTES '300MB', OVERWRITE_OR_IGNORE)
"""


def main():
    t0 = time.time()
    con = connect()
    FEATURES_DIR.parent.mkdir(parents=True, exist_ok=True)
    con.execute(SQL)
    n, c = con.execute(
        f"SELECT count(*), count(DISTINCT ROW_ID) FROM '{FEATURES_PARQUET}'"
    ).fetchone()
    assert n == c, "ROW_ID must stay unique"
    print(f"rows: {n:,}  ({time.time() - t0:.0f}s)  -> {FEATURES_DIR}")


if __name__ == "__main__":
    main()
